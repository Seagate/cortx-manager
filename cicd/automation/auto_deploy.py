# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
This python file will run prerequisites and then run auto-deploy.
"""
import paramiko
import os
import sys
import time

subscription_mgr_disabled = ""
subscription_mgr_enabled  = ""
auto_deploy_script = ""

class Utility:
    
    @staticmethod
    def connect(host, username, password, shell=True):
        """
        Connect to remote host.
        :param host: host ip address
        :type host: str
        :param username: host username
        :type username: str
        :param password: host password
        :type password: str
        :param shell: In case required shell invocation
        :return: Boolean, Whether ssh connection establish or not
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print("Connecting to host: ",host)
            client.connect(hostname=host, username=username, password=password)
            if shell:
                shell = client.invoke_shell()
        except paramiko.AuthenticationException:
            print("Server authentication failed")
            result = False
        except paramiko.SSHException as ssh_exception:
            print(
                "Could not establish ssh connection: %s",
                ssh_exception)
            result = False
        except socket.timeout as timeout_exception:
            print(
                "Could not establish connection because of timeout: %s",
                timeout_exception)
            result = False
        except Exception as error:
            print("Exception while connecting to server")
            print("Error message: ", error)
            result = False
            if shell:
                client.close()
            if not isinstance(shell, bool):
                shell.close()
        else:
            result = client
        return result
    
    def execute_command(
        self,
        command,
        host,
        username,
        password,
        timeout_sec=400,
        inputs=None,
        nbytes=None,
        read_sls=False):
        """
        Execute the command on the given host
        :param command: Command to be executed
        :param host: hostname/ IP address
        :param username: username on the given host
        :param password: password of the given user
        :param timeout_sec: timeout
        :param inputs: Inputs to the command
        :param nbytes: Number of bytes to read
        :param read_sls: Read as single text
        """
        output = None
        result_flag = True
        client = self.connect(host, username, password)
        if client:
            print("Server_IP: {}".format(host))
            print("Executing command: {}".format(command))
            stdin, stdout, stderr = client.exec_command(
                command, timeout=timeout_sec)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status:
                result_flag = False
            if inputs:
                stdin.write('\n'.join(inputs))
                stdin.write('\n')
            stdin.flush()
            stdin.channel.shutdown_write()
            client.close()
            if nbytes:
                ssh_output = stdout.read(nbytes)
            # this branch is only applicable to configure-cortx lib
            elif read_sls:
                ssh_output = stdout.read()
                if ssh_output == b'':
                    ssh_error = stderr.read()
                    return result_flag, ssh_error
                return result_flag, ssh_output
            else:
                ssh_output = stdout.readlines()
            ssh_error = stderr.read()
            if ssh_error == b'':
                output = ssh_output
            else:
                output = ssh_error
        else:
            output = constants.SSH_CONNECT_ERR
            result_flag = False
            # client.close()
        return result_flag, output

class Prerequisites:
    """
    This class executes prerequisites command on
    both nodes.
    """
    def __init__(self, primary_node,
                 primary_node_username,
                 primary_node_password,
                 secondary_node,
                 secondary_node_username,
                 secondary_node_password,
                 prereq_link
                 ):
        params = [(primary_node, primary_node_username, primary_node_password),
                  (secondary_node, secondary_node_username, secondary_node_password)]
        self.execute_prerequisites(params)

    def run_prerequisites_command(self, node, username, password, command, subs_mngr):
        try:
            status,resp = utils_obj.execute_command(command=command,
                                       host=node,
                                       username=username,
                                      password=password)

            print("Run subscription manager {} command on both nodes {} {}".format(subs_mngr, status, resp))
        except:
            print("checking if node is up")

        finally:
                    time.sleep(60) # waiting for reboot process to start before checking ping
                    retry_count = 15
                    while retry_count > 0:
                        print("checking if node is up")
                        if self.check_ping(node):
                            time.sleep(120) #waiting for ssh service
                            break
                        time.sleep(60)

                    cmd = "tail -n5 /var/log/seagate/provisioner/cortx-prereqs.log"
                    _, resp = utils_obj.execute_command(command=cmd,
                                              host=node,
                                              username=username,
                                              password=password)
                    if ('SUCCESS' in str(resp)) or ('Nothing to do' in str(resp)):
                        print(f"{subs_mngr} command run successful")

    def execute_prerequisites(self, params):
        """
        This method executes prerequisites on both node
        :param params: list of tuples(primary & secondary node)
        """
        for param in params:
            node, username, password = param
            print("Check os verion")
            linux_vesion_cmd = "cat /etc/redhat-release"
            status, resp = utils_obj.execute_command(command = linux_vesion_cmd,
                                                     host=node,
                                                     username=username,
                                                     password=password)
            print("check os version {} {}".format(status, resp
                                                  ))
            assert status
            found = False
            for ele in resp:
                if "7.7" in ele:
                    found = True
            assert found

            print("Check kernel version")
            linux_kernel_version_cmd = "uname -a"
            status, resp = utils_obj.execute_command(command=linux_kernel_version_cmd,
                                                     host=node,
                                                     username=username,
                                                     password=password)
            print("check kernel version {} {}".format(status, resp
                                                  ))
            assert status
            found = False
            for ele in resp:
                if "3.10.0-1062.el7.x86_64" in ele:
                    found = True
            assert found

            print("Check licenses, subscription manager enabled on both nodes")
            check_licenses_cmd =  "subscription-manager list | grep Status: | awk '{ print $2 }' " \
                                      "&& subscription-manager status | grep 'Overall Status:' | awk '{ print $3 }'"
            status, resp = utils_obj.execute_command(command = check_licenses_cmd,
                                                     host=node,
                                                     username=username,
                                                     password=password)
            print("Check licenses, subscription manager enabled on both nodes {} {}".format(status, resp
                                                  ))
            assert status
            enable_subscription_manager = True
            found = [False, False]
            for ele in resp:
                if  "Subscribed" in ele.strip():
                    found[0] = True
                if  "Current" in ele.strip():
                    found[1] = True
            if False in found:
                enable_subscription_manager = False
            else:
                print("Check high availability license enabled on both nodes")
                check_ha_licenses_cmd = "subscription-manager repos --list | grep rhel-ha-for-rhel-7-server-rpms"
                status, resp = utils_obj.execute_command(command=check_ha_licenses_cmd,
                                                         host=node,
                                                         username=username,
                                                         password=password)
                print("Check high availability license enabled on both node {} {}".format(status, resp))
                assert status
                found = False
                for ele in resp:
                    if  "Repo ID:   rhel-ha-for-rhel-7-server-rpms" in ele.strip():
                        found = True
                if not found:
                    enable_subscription_manager = False

            if not enable_subscription_manager:
                print(subscription_mgr_disabled)
                print("Run subscription manager disabled command on both nodes")
                subscription_manager_disabled_cmd = "curl {} -o cortx-prereqs.sh; chmod a+x cortx-prereqs.sh; ./cortx-prereqs.sh --disable-sub-mgr".format(subscription_mgr_disabled)
                #subscription_manager_disabled_cmd = " ".join([subscription_manager_disabled_cmd, '> /tmp/out1.log'])
                self.run_prerequisites_command(node, username, password, subscription_manager_disabled_cmd,
                                               "disable" )
            else:
                print("Run subscription manager enabled command on both nodes")
                subscription_manager_enabled_cmd = "curl {} | bash -s".format(subscription_mgr_enabled)
                #subscription_manager_enabled_cmd = " ".join([subscription_manager_enabled_cmd, '> /tmp/out1.log'])
                self.run_prerequisites_command(node, username, password, subscription_manager_enabled_cmd,
                                               "enable" )

            print("Verify volumes/LUNs mapped from storage enclosure to the servers")
            lsblk_cmd = "lsblk -S|grep SEAGATE"
            status, resp = utils_obj.execute_command(command=lsblk_cmd,
                                                     host=node,
                                                     username=username,
                                                     password=password
                                                     )
            print("lsblk cmd output {} {}".format(status, resp))
            assert len(resp) > 0

    def check_ping(self, host):
        response = os.system("ping -c 1 " + host)
        if response == 0:
            pingstatus = True
        else:
            pingstatus = False

        return pingstatus

class AutoDeploy:
    """
    This class executes auto deploy command on
    both nodes.
    """
    def __init__(self, args ):
        self.args = args 

    def download_auto_deploy_script(self):
        """
        This method will download the auto deploy script
        """
        print("Download auto_deploy script on primary node")
        download_auto_deploy_cmd = "curl {} -o auto-deploy; chmod a+x auto-deploy".format(auto_deploy_script)
        status, resp = utils_obj.execute_command(command=download_auto_deploy_cmd,
                                                 host=self.args.pnode,
                                                 username=self.args.pnode_user,
                                                 password=self.args.pnode_passwd)
        utils_obj.execute_command(command="chmod 777 *",
                                                 host=self.args.pnode,
                                                 username=self.args.pnode_user,
                                                 password=self.args.pnode_passwd)
        return status, resp
 
    def create_auto_deploy_command(self):
        """
        This will create auto deploy command using given argumnets
        """
        pre_command = "./auto-deploy -s {0} -p {1}".format(self.args.snode,
                                                           self.args.snode_passwd)
        command = [pre_command]
        params = ["C", "V", "n", "N", "i", "I", "A", "B", "U", "P", "m1", "m2", "b1", "b2", "t"]
        for param in params:
            if getattr(self.args, param):
                if param=="m1" or param=="m2" or param=="b1" or param=="b2":
                    command.append( "--"+param )
                else:
                    command.append( "-"+param )
                command.append(getattr(self.args, param))     
        return ' '.join(command)          

    def run_auto_deploy_script(self):
        """
        This method will run the auto deploy script
        :return: boolean
        
        utils_obj.execute_command(command="rpm -e $(rpm -qa |grep eos-prvsnr)",
                                                 host=self.args.pnode,
                                                 username=self.args.pnode_user,
                                                 password=self.args.pnode_passwd)        

        utils_obj.execute_command(command="rpm -e $(rpm -qa |grep eos-prvsnr)",
                                                 host=self.secondary_node,
                                                 username=self.secondary_node_username,
                                                 password=self.secondary_node_password)

        """
        print("Run auto_deploy script on primary node")
        run_auto_deploy_cmd = self.create_auto_deploy_command()
        #run_auto_deploy_cmd = " ".join([run_auto_deploy_cmd, '> /tmp/deploy.log'])
        print("Command:", run_auto_deploy_cmd)
        try:
            utils_obj.execute_command(command=run_auto_deploy_cmd,
                                                 timeout_sec = 3600,
                                             host=self.args.pnode,
                                             username=self.args.pnode_user,
                                             password=self.args.pnode_passwd
                                              )
        except Exception as e:
            print("exception {}".format(e))
            print("Checking output for validation")
        finally:
            cmd = "tail -n5 /var/log/seagate/provisioner/auto-deploy.log"
            _, resp = utils_obj.execute_command(command=cmd,
                                             host=self.args.pnode,
                                             username=self.args.pnode_user,
                                             password=self.args.pnode_passwd)
            if ('SUCCESS' in str(resp)) or ('Nothing to do' in str(resp)):
                print("autodeploy command run successful")
            else:
                assert False, resp


    def verify_corosync_pacemake_status(self):
        """
        This method verify status of corosync-pacemake
        :return: boolean,tuple
        """
        print("Verify corosync-pacemake cluster status")
        corosync_pacemake_cluster_status_cmd = "pcs cluster status"
        status, resp = utils_obj.execute_command(command=corosync_pacemake_cluster_status_cmd,
                                             host=self.args.pnode,
                                             username=self.args.pnode_user,
                                             password=self.args.pnode_passwd
                                              )
        found = 0
        for i in resp:
            if "2: Online" in i.strip() or "1: Online" in i.strip():
                found+=1
        if found < 2:
            assert False, resp
 
        return status, resp

    def verify_cluster_status(self):
        """
        This method verifies the status of cortx-cluster
        :return: boolean,tuple
        """
        print("Verify in detail CORTX cluster status")
        cortx_cluster_status_cmd = "pcs status"
        status, resp = utils_obj.execute_command(command=cortx_cluster_status_cmd,
                                             host=self.args.pnode,
                                             username=self.args.pnode_user,
                                             password=self.args.pnode_passwd
                                              )
        found = 0
        for i in resp:
            if "nodes configured" in i.strip() or "Online:" in i.strip():
                found+=1
        if found < 2:
            assert False, resp

        return status, resp            

'''        
def parse_args():
    from optparse import OptionParser
    parser= OptionParser()

    parser.add_option('--primarynodeip', dest='primary_node', action="append", default='', help='primary node ip')

    options, args = parser.parse_args()
    return options
'''
class Deploy():
    """ this class parse all args and deploy complete CORTX stack"""
    @staticmethod
    def deploy(args):
        print(args)
        global  subscription_mgr_disabled
        global subscription_mgr_enabled
        global auto_deploy_script

        subscription_mgr_disabled = args.pre
        subscription_mgr_enabled = args.pre
        auto_deploy_script = args.a
        prerequisites_obj = Prerequisites(args.pnode,
                args.pnode_user,
                args.pnode_passwd,
                args.snode,
                args.snode_user,
                args.snode_passwd,
                args.pre)
        auto_deploy_obj = AutoDeploy(args)
        auto_deploy_obj.download_auto_deploy_script()
        auto_deploy_obj.run_auto_deploy_script()
        print("Autodeployment Successful")
        auto_deploy_obj.verify_corosync_pacemake_status()
        auto_deploy_obj.verify_cluster_status()
        print("Cluster started Successfully")
        

if __name__ == "__main__":
    #options = parse_args()
    import argparse
   
    
    utils_obj = Utility()
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-pnode", type=str,
            help="Hostname for primary node")
    argParser.add_argument("-snode", type=str,
            help="Hostname for secondary node")
    argParser.add_argument("-pnode_user", type=str, default="root",
            help="User for primary node")
    argParser.add_argument("-pnode_passwd", type=str,
            help="Password for primary node")
    argParser.add_argument("-snode_passwd", type=str,
            help="Password for secondary node")
    argParser.add_argument("-snode_user", type=str, default="root",
            help="User for secondary node")
    argParser.add_argument("-C", type=str,
            help="Cluster ip for HW")
    argParser.add_argument("-V", type=str,
            help="Management vip for HW")
    argParser.add_argument("-n", type=str, default="enp175s0f0",
            help="Public n/w interface name (default enp175s0f0)")
    argParser.add_argument("-N", type=str, default="enp175s0f1",
            help="Private n/w interface name (default enp175s0f1)")
    argParser.add_argument("-i", type=str,
            help=(f"IP address for public n/w interface name on node-1."  
                        f"This IP will be assigned to the n/w interface"  
                        f"provided for -n option."  
                        f"Omit this option if ip is already set by DHCP"))
    argParser.add_argument("-I", type=str,
            help=(f"IP address for public n/w interface name on node-2,"  
                        f"This IP will be assigned to the n/w interface name"  
                        f"provided for -N option."))
    argParser.add_argument("-A", type=str,
            help="IP address of controller A (default 10.0.0.2)")
    argParser.add_argument("-B", type=str,
            help="IP address of controller B (default 10.0.0.2)")
    argParser.add_argument("-U", type=str, default="manage",
            help="User for controller (default 'manage')")
    argParser.add_argument("-P", type=str,
            help="Password for controller (default 'passwd')")
    argParser.add_argument("-b1", type=str, default="ADMIN",
            help="BMC User for Node-1. Default ADMIN")
    argParser.add_argument("-b2", type=str, default="ADMIN",
            help="BMC User for Node-2. Default ADMIN")
    argParser.add_argument("-m1", type=str, default="adminBMC!",
            help="BMC Password for Node-1. Default adminBMC!")
    argParser.add_argument("-m2", type=str, default="adminBMC!",
            help="BMC Password for Node-2. Default adminBMC!")
    argParser.add_argument("-t", type=str, default="http://cortx-storage.colo.seagate.com/releases/cortx/github/release/rhel-7.7.1908/last_successful/",
            help="target build url for CORTX ( default 'http://cortx-storage.colo.seagate.com/releases/cortx/github/release/rhel-7.7.1908/last_successful/')")
    argParser.add_argument("-pre", type=str, default="https://raw.githubusercontent.com/Seagate/cortx-prvsnr/release/cli/src/cortx-prereqs.sh?token=APVYY2LLIQYAKTNYFYM4QS27CFXIA",
            help="link for prereq script  ( default 'https://raw.githubusercontent.com/Seagate/cortx-prvsnr/release/cli/src/cortx-prereqs.sh?token=APVYY2LLIQYAKTNYFYM4QS27CFXIA'")
    argParser.add_argument("-a", type=str, default="https://raw.githubusercontent.com/Seagate/cortx-prvsnr/release/cli/src/auto-deploy?token=APVYY2PVVBU2LY53KMGFVLK7BVTHE",
            help="link to autodeploy script for CORTX (default 'https://raw.githubusercontent.com/Seagate/cortx-prvsnr/release/cli/src/auto-deploy?token=APVYY2PVVBU2LY53KMGFVLK7BVTHE')")
 
    argParser.set_defaults(func=Deploy.deploy)
    args = argParser.parse_args()
    args.func(args)
 
    sys.exit(0)
