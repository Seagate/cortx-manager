#!/usr/bin/env bash

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

read -p "Enter Ip to be Replaced in Config: "  ip_name
ping $ip_name -c 2

if [ $? != 0 ]; then
    echo "Invalid IP"
    exit 1
fi
sed -i 's/localhost/'$ip_name'/g' /etc/cortx/csm/csm.conf
sed -i 's/127.0.0.1/'$ip_name'/g' /etc/cortx/csm/csm.conf
sed -i 's/localhost/'$ip_name'/g' /etc/cortx/csm/database.yaml
sed -i 's/127.0.0.1/'$ip_name'/g' /etc/cortx/csm/database.yaml

read -p "Enter PORT for Consul to be Replaced in Config: "  consul_port
if [ $consul_port == '' ] ; then
    consul_port=18500
fi
sed -i 's/8500/'$consul_port'/g' /etc/cortx/csm/database.yaml