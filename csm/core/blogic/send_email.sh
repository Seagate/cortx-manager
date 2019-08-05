#!/bin/bash
hostname=`hostname`
msg=$(tail -n 1 /var/log/messages)
echo "$msg" | mutt -s "Error/IEM Occured in syslog on $hostname" $(cat /etc/csm/email/email_list)
echo "OK"
