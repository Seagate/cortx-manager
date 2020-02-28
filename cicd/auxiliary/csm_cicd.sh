#!/bin/bash

RPM_PATH=$1
CSM_REPO_PATH=$2
CSM_PATH=$3

yum install -y $RPM_PATH/*.rpm

# Copy certificates
mkdir -p /etc/ssl/stx-s3/s3/
cp -f $CSM_REPO_PATH/jenkins/cicd/ca.crt /etc/ssl/stx-s3/s3/
cp -f $CSM_REPO_PATH/jenkins/cicd/ca.key /etc/ssl/stx-s3/s3/

csm_setup post_install
csm_setup config
csm_setup init

su -c "/usr/bin/csm_agent &" csm
# TODO: Run web as csm user after not path issue is resolved
node $CSM_PATH/web/web-dist/server.js &

# TODO: Uncomment when container able to start systemd service
#systemctl restart csm_agent
#systemctl restart csm_web

#systemctl status csm_agent
#systemctl status csm_web

sleep 5s
mkdir -p /tmp

/usr/bin/csm_test -t $CSM_PATH/test/plans/cicd.pln -f $CSM_PATH/test/test_data/args.yaml -o /tmp/result.txt
