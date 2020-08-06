#!/bin/bash -x

#  ****************************************************************************
#  Filename:          shutdown_cron.sh
#  Description:       Cron Shell Script for Shutting Down Node.

#  Creation Date:     22/07/2020
#  Author:            Prathamesh Rodi
                 

#  Do NOT modify or remove this copyright and confidentiality notice!
#  Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
#  The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
#  Portions are also trade secret. Any use, duplication, derivation, distribution
#  or disclosure of this code, for any reason, not expressly authorized is
#  prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
# ****************************************************************************

PATH=/usr/bin:/sbin:/usr/sbin;export PATH
source /opt/seagate/cortx/csm/home/.bashrc

while getopts ":g:u:p:n:s" o; do
    case "${o}" in
        u)
            USER=${OPTARG}
            ;;
        p)
            PASSWORD=${OPTARG}
            ;;
        n)
            NODE_NAME=${OPTARG}
            ;;
        s)
            EXIT=${OPTARG}
    esac
done

hctl node --username "${USER}" --password "${PASSWORD}" shutdown "${NODE_NAME}"
