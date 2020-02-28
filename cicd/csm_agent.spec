Name: <RPM_NAME>
Version: %{version}
Release: %{dist}
Summary: CSM Tools
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: <PRODUCT>-csm_agent-%{version}.tar.gz
%define debug_package %{nil}

%description
CSM Tools

%prep
%setup -n csm
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}<CSM_PATH>
cp -rp . ${RPM_BUILD_ROOT}<CSM_PATH>
exit 0

%post
# Use csm_setup cli for csm directory, permission services
mkdir -p /etc/uds
CSM_DIR=<CSM_PATH>
CFG_DIR=$CSM_DIR/conf
PRODUCT=<PRODUCT>

# Move binary file
[ -d "${CSM_DIR}/lib" ] && {
    ln -sf $CSM_DIR/lib/csm_setup /usr/bin/csm_setup
    ln -sf $CSM_DIR/lib/csm_setup $CSM_DIR/bin/csm_setup

    ln -sf $CSM_DIR/lib/csmcli /usr/bin/csmcli
    ln -sf $CSM_DIR/lib/csmcli $CSM_DIR/bin/csmcli

    ln -sf $CSM_DIR/lib/csm_agent /usr/bin/csm_agent
    ln -sf $CSM_DIR/lib/csm_agent $CSM_DIR/bin/csm_agent

    ln -sf $CSM_DIR/lib/csm_cleanup /usr/bin/csm_cleanup
    ln -sf $CSM_DIR/lib/csm_cleanup $CSM_DIR/bin/csm_cleanup

    cp -f $CFG_DIR/service/csm_agent.service /etc/systemd/system/csm_agent.service
}

[ -d "${CSM_DIR}/test" ] && {
    ln -sf $CSM_DIR/lib/csm_test /usr/bin/csm_test
    ln -sf $CSM_DIR/lib/csm_test $CSM_DIR/bin/csm_test
}

[ -f /etc/uds/uds_s3.toml ] || \
    cp -R $CFG_DIR/etc/uds/uds_s3.toml.sample /etc/uds/uds_s3.toml

#TODO: Move rsyslog and logrotate in csm_setup
[ -d "/etc/rsyslog.d" ] && {
    cp -f $CFG_DIR/etc/rsyslog.d/csm_logs.conf /etc/rsyslog.d/csm_logs.conf
    cp -f $CFG_DIR/etc/rsyslog.d/support_bundle.conf /etc/rsyslog.d/support_bundle.conf
    systemctl restart rsyslog
} || \
    echo "Csm logs could not be configured. Check & fix it manually." >>/dev/stderr
[ -d "/etc/logrotate.d" ] && {
    cp -f $CFG_DIR/etc/logrotate.d/csm_agent_log.conf /etc/logrotate.d/csm_agent_log.conf
} || \
    echo "Csm logs rotation could not be configured. Check & fix it manually." >>/dev/stderr
exit 0

%preun
[ $1 -eq 1 ] && exit 0
systemctl disable csm_agent
systemctl stop csm_agent

%postun
[ $1 -eq 1 ] && exit 0
rm -f /etc/systemd/system/csm_agent.service 2> /dev/null;
rm -f /usr/bin/csm_setup 2> /dev/null;
rm -f /usr/bin/csmcli 2> /dev/null;
rm -f /usr/bin/csm_agent 2> /dev/null;
rm -f /usr/bin/csm_test 2> /dev/null;
rm -f /usr/bin/csm_cleanup 2> /dev/null;
rm -rf <CSM_PATH>/bin/ 2> /dev/null;
systemctl daemon-reload
exit 0

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
<CSM_PATH>/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
