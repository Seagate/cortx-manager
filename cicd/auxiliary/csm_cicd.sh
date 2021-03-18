#!/bin/bash

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

set -x

RPM_PATH=$1
CSM_REPO_PATH=$2
CSM_PATH=$3


yum install -y $RPM_PATH/*.rpm

# Copy certificates
mkdir -p /etc/ssl/stx/ /etc/cortx/ha/
cp -f $CSM_REPO_PATH/cicd/auxiliary/stx.pem /etc/ssl/stx/
#cp -f $CSM_REPO_PATH/cicd/auxiliary/etc/database.json /etc/cortx/ha/

groupadd haclient

python3 -c "import provisioner; print(provisioner.__file__)"
python3 -c "import sys; print(sys.path)"
pip3 freeze

chmod 777 -R /var/log/seagate
csm_setup post_install --config json:///opt/seagate/cortx/csm/templates/csm.post-install.conf.tmpl
csm_setup prepare --config json:///opt/seagate/cortx/csm/templates/csm.prepare.conf.tmpl
csm_setup config --config json:///opt/seagate/cortx/csm/templates/csm.config.conf.tmpl
csm_setup init --config json:///opt/seagate/cortx/csm/templates/csm_setup_conf_template.json

#su -c "/usr/bin/csm_agent --debug &" csm
/usr/bin/csm_agent --debug &


# TODO: Uncomment when container able to start systemd service
#systemctl restart csm_agent


#systemctl status csm_agent

[ -f /var/log/seagate/csm/csm_agent.log ] && {
    cat /var/log/seagate/csm/csm_agent.log
} || {
    echo "Log init failed"
}

sleep 5s
mkdir -p /tmp


/usr/bin/csm_test -t $CSM_PATH/test/plans/cicd.pln -f $CSM_PATH/test/test_data/args.yaml -o /tmp/result.txt
