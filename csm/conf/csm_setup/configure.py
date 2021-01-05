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

import os
from cortx.utils.log import Log
from csm.common.conf import Conf
from csm.common.payload import Yaml
from csm.conf.salt import SaltWrappers
from csm.conf.setup import Setup, CsmSetupError, InvalidPillarDataError
from csm.core.blogic import const


class Configure(Setup):
    """
    Action for csm config
    create: Copy configuraion file
    load: Load configuraion file
    reset: Reset configuraion file
    delete: Delete configuration file
    """

    def __init__(self):
        super(Configure, self).__init__()

    def execute(self, command):
        """

        :return:
        """
        Configure.create(command.args)


    @staticmethod
    def store_encrypted_password(conf_data):
        # read username's and password's for S3 and RMQ
        open_ldap_credentials = SaltWrappers.get_salt_call(
            const.PILLAR_GET, const.OPENLDAP)
        # Edit Current Config File.
        if open_ldap_credentials and type(open_ldap_credentials) is dict:
            conf_data[const.S3][const.LDAP_LOGIN] = open_ldap_credentials.get(
                const.IAM_ADMIN, {}).get(const.USER)
            conf_data[const.S3][
                const.LDAP_PASSWORD] = open_ldap_credentials.get(
                const.IAM_ADMIN, {}).get(const.SECRET)
        else:
            Log.error(f"failed to get pillar data for {const.OPENLDAP}")
            raise InvalidPillarDataError(
                f"failed to get pillar data for {const.OPENLDAP}")
        sspl_config = SaltWrappers.get_salt_call(const.PILLAR_GET, const.SSPL)
        if sspl_config and type(sspl_config) is dict:
            conf_data[const.CHANNEL][const.USERNAME] = sspl_config.get(
                const.USERNAME)
            conf_data[const.CHANNEL][const.PASSWORD] = sspl_config.get(
                const.PASSWORD)
        else:
            Log.error(f"failed to get pillar data for {const.SSPL}")
            raise InvalidPillarDataError(
                f"failed to get pillar data for {const.SSPL}")
        cluster_id = SaltWrappers.get_salt_call(const.GRAINS_GET,
                                                const.CLUSTER_ID)
        provisioner_data = conf_data[const.PROVISIONER]
        provisioner_data[const.CLUSTER_ID] = cluster_id
        conf_data[const.PROVISIONER] = provisioner_data

    @staticmethod
    def create(args):
        """
        This Function Creates the CSM Conf File on Required Location.
        :return:
        """
        Log.error(f"Create the CSM Conf File on Required Location. args:{args}")
        csm_conf_target_path = os.path.join(const.CSM_CONF_PATH,
                                            const.CSM_CONF_FILE_NAME)
        csm_conf_path = os.path.join(const.CSM_SOURCE_CONF_PATH,
                                     const.CSM_CONF_FILE_NAME)
        # Read Current CSM Config FIle.
        conf_file_data = Yaml(csm_conf_path).load()
        if conf_file_data:
            if args[const.DEBUG]:
                conf_file_data[const.DEPLOYMENT] = {const.MODE: const.DEV}
            else:
                Configure.store_encrypted_password(conf_file_data)
                # Update the Current Config File.
                Yaml(csm_conf_path).dump(conf_file_data)
            Setup._run_cmd(
                f"cp -rn {const.CSM_SOURCE_CONF_PATH} {const.ETC_PATH}")
            if args[const.DEBUG]:
                Yaml(csm_conf_target_path).dump(conf_file_data)
        else:
            Log.error(f"Unable to load CSM config. Path:{csm_conf_path}")
            raise CsmSetupError(
                f"Unable to load CSM config. Path:{csm_conf_path}")

    @staticmethod
    def cli_create(args):
        """
        This Function Creates the CortxCli Conf File on Required Location.
        :return:
        """
        os.makedirs(const.CORTXCLI_PATH, exist_ok=True)
        os.makedirs(const.CORTXCLI_CONF_PATH, exist_ok=True)
        Setup._run_cmd(
            f"setfacl -R -m u:{const.NON_ROOT_USER}:rwx {const.CORTXCLI_PATH}")
        Setup._run_cmd(
            f"setfacl -R -m u:{const.NON_ROOT_USER}:rwx {const.CORTXCLI_CONF_PATH}")
        cli_conf_target_path = os.path.join(const.CORTXCLI_CONF_PATH,
                                            const.CORTXCLI_CONF_FILE_NAME)
        cli_conf_path = os.path.join(const.CORTXCLI_SOURCE_CONF_PATH,
                                     const.CORTXCLI_CONF_FILE_NAME)
        # Read Current CortxCli Config FIle.
        conf_file_data = Yaml(cli_conf_path).load()
        if conf_file_data:
            if const.ADDRESS_PARAM in args.keys():
                conf_file_data[const.CORTXCLI_SECTION][
                    const.CSM_AGENT_HOST_PARAM_NAME] = \
                    args[const.ADDRESS_PARAM]
            if args[const.DEBUG]:
                conf_file_data[const.DEPLOYMENT] = {const.MODE: const.DEV}
            else:
                Configure.store_encrypted_password(conf_file_data)
                # Update the Current Config File.
                Yaml(cli_conf_path).dump(conf_file_data)
            Setup._run_cmd(
                f"cp -rn {const.CORTXCLI_SOURCE_CONF_PATH} {const.ETC_PATH}")
            if args["f"] or args[const.DEBUG]:
                Yaml(cli_conf_target_path).dump(conf_file_data)
        else:
            raise CsmSetupError(
                f"Unable to load Cortx Cli config. Path:{cli_conf_path}")

    @staticmethod
    def load():
        Log.info("Loading config")
        csm_conf_target_path = os.path.join(const.CSM_CONF_PATH,
                                            const.CSM_CONF_FILE_NAME)
        if not os.path.exists(csm_conf_target_path):
            Log.error(
                "%s file is missing for csm setup" % const.CSM_CONF_FILE_NAME)
            raise CsmSetupError(
                "%s file is missing for csm setup" % const.CSM_CONF_FILE_NAME)
        Conf.load(const.CSM_GLOBAL_INDEX, Yaml(csm_conf_target_path))
        """
        Loading databse config
        """
        Configure.load_db()

    @staticmethod
    def load_db():
        Log.info("Loading databse config")
        db_conf_target_path = os.path.join(const.CSM_CONF_PATH,
                                           const.DB_CONF_FILE_NAME)
        if not os.path.exists(db_conf_target_path):
            Log.error(
                "%s file is missing for csm setup" % const.DB_CONF_FILE_NAME)
            raise CsmSetupError(
                "%s file is missing for csm setup" % const.DB_CONF_FILE_NAME)
        Conf.load(const.DATABASE_INDEX, Yaml(db_conf_target_path))

    @staticmethod
    def delete():
        Log.info("Delete config")
        Setup._run_cmd("rm -rf " + const.CSM_CONF_PATH)

    @staticmethod
    def reset():
        Log.info("Reset config")
        os.makedirs(const.CSM_CONF_PATH, exist_ok=True)
        Setup._run_cmd(
            "cp -rf " + const.CSM_SOURCE_CONF_PATH + " " + const.ETC_PATH)
