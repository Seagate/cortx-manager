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

while getopts ":g:i:m:n:c:s" o; do
    case "${o}" in
        i)
            ID=${OPTARG}
            ;;
        m)
            COMMENT=${OPTARG}
            ;;
        n)
            NODE_NAME=${OPTARG}
            ;;
        c)
            COMPONENTS=${OPTARG}
            ;;
        s)
            OS=true
    esac
done

CORTXCLI_COMMAND="cortxcli bundle_generate '${ID}' '${COMMENT}' '${NODE_NAME}'"

if [ -n "$OS" ]
then
  CORTXCLI_COMMAND="${CORTXCLI_COMMAND} -o"
fi


if [ -n "$COMPONENTS" ]
then
  CORTXCLI_COMMAND="${CORTXCLI_COMMAND} -c ${COMPONENTS}"
fi

eval "$CORTXCLI_COMMAND"
