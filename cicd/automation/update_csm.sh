#!/usr/bin/bash

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

remove_conf()
{

ls /etc/csm/
if [ "$?" -eq 0 ]; then
   echo "remving csm config files"
   rm -rf /etc/csm
else
   echo "no csm conf available"
fi
}

update_salt_pillar()
{
# Update release.sls
    echo -e "\n\t***** INFO: Updating release.sls *****" 2>&1 | tee -a $LOG_FILE
    sed -i "s~target_build: .*~target_build: ${tgt_build}~" /opt/seagate/cortx/provisioner/pillar/components/release.sls;
    salt "*" saltutil.sync_all
    salt "*" saltutil.refresh_pillar

}

run_command()
{
echo "running command : $1"
$1
if [ "$?" -eq 0 ]; then
    echo "Successfully : $1"
else
    echo "failed : $1"
    exit 1
fi

}


singlenode=false
hardware=false
remove_data=false

usage()
{
    echo "\
This script will remove existing csm rpms and 
install csm rpms from  target build Also 
do cleanup of consul data and elasticsearch data

Usage:
sh install_csm.sh -t <target build url for CORTX>

For Single Node:
sh update_csm.sh -S -t <target build url for CORTX>

For Dual Node:
sh update_csm.sh -t <target build url for CORTX>

For Dual Node HW: 
sh update_csm.sh -H -t <target build url for CORTX>

Optional Arguments:
-rm             Remove conule data and  elasticsearch data
"
}
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage; exit 0
        ;;
        -t)
            tgt_build_opt=true
            [ -z "$2" ] &&
                echo "Error: Target build not provided" && exit 1;
            tgt_build="$2"
            shift 2 ;;
        -S)
            singlenode=true
            shift 1 ;;
        -H)
            hardware=true
            shift 1 ;;
        -rm)
            remove_data=true
            shift 1 ;;
        *) echo "Invalid option $1"; usage; exit 1;;
    esac
done

indices=(alerts csmauditlog supportbundle s3-rsys-index alerts-history)
# remove csm rpms
if [[ "$hardware" == true ]]; then
   echo "diable pcs resource csm-agent"
   run_command "pcs resource disable csm-agent"
   echo "diable pcs resource csm-web"
   run_command "pcs resource disable csm-web"
fi
echo "---destoying csm on srvnode-1---"
salt srvnode-1 state.apply components.csm.teardown
if [[ "$singlenode" == false ]]; then
 echo "---destoying csm on srvnode-2---"
 salt srvnode-2 state.apply components.csm.teardown
fi
remove_conf
#remove consul data
if [[ "$remove_data" == true ]]; then
 echo "---- deleting data from consul ----"
 run_command "/opt/seagate/cortx/hare/bin/consul kv delete -recurse eos/base/"
 echo "---- deleting elasticsearch indices ----"
 for i in "${indices[@]}"
 do
   printf "\n--- deleting $i index ---" 
   curl -X DELETE http://localhost:9200/$i
 done
fi

update_salt_pillar
if [[ "$singlenode" == true ]]; then
 echo "---deploying on srvnode-1---"
 run_command "salt srvnode-1 state.apply components.csm"
else
 echo "deploying on srvnode-2 "
 run_command "salt srvnode-2 state.apply components.csm"
 echo "deploying on srvnode-1 "
 run_command "salt srvnode-1 state.apply components.csm"
fi
if [[ "$hardware" == true ]]; then
   echo "enable pcs resource csm-agent"
   run_command "pcs resource enable csm-agent"
   echo "enable pcs resource csm-web"
   run_command "pcs resource enable csm-web"
fi



