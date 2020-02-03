Name: <RPM_NAME>
Version: %{version}
Release: %{dist}
Summary: CSM Tools
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: <PRODUCT>-csm-%{version}.tar.gz
%define debug_package %{nil}

%description
CSM Tools

%prep
%setup -n csm
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm
exit 0

%post
mkdir -p /var/csm/bundle /var/log/seagate/csm /etc/csm /etc/uds
CSM_DIR=/opt/seagate/csm
CFG_DIR=$CSM_DIR/conf
PRODUCT=<PRODUCT>

[ -d "${CSM_DIR}/lib" ] && {
    ln -sf $CSM_DIR/lib/csm_setup /usr/bin/csm_setup
    ln -sf $CSM_DIR/lib/csm_setup $CSM_DIR/bin/csm_setup

    ln -sf $CSM_DIR/lib/csmcli /usr/bin/csmcli
    ln -sf $CSM_DIR/lib/csmcli $CSM_DIR/bin/csmcli

    ln -sf $CSM_DIR/lib/csm_agent /usr/bin/csm_agent
    ln -sf $CSM_DIR/lib/csm_agent $CSM_DIR/bin/csm_agent

    cp -f $CFG_DIR/service/csm_agent.service /etc/systemd/system/csm_agent.service
}

[ -d "${CSM_DIR}/test" ] && {
    ln -sf $CSM_DIR/lib/csm_test /usr/bin/csm_test
    ln -sf $CSM_DIR/lib/csm_test $CSM_DIR/bin/csm_test
}

[ -f /etc/csm/csm.conf ] || \
    cp -R $CFG_DIR/etc/csm/csm.conf.sample /etc/csm/csm.conf
[ -f /etc/csm/cluster.conf ] || \
	cp $CFG_DIR/etc/csm/cluster.conf.sample /etc/csm/cluster.conf
[ -f /etc/csm/components.yaml ] || \
    cp $CFG_DIR/etc/csm/components.yaml /etc/csm/
[ -f /etc/csm/database.yaml ] || \
    cp -R $CFG_DIR/etc/csm/database.yaml.sample /etc/csm/database.yaml
[ -f /etc/uds/uds_s3.toml ] || \
    cp -R $CFG_DIR/etc/uds/uds_s3.toml.sample /etc/uds/uds_s3.toml

[ -d "${CSM_DIR}/${PRODUCT}/gui" ] && {
    cp -f $CFG_DIR/service/csm_web.service /etc/systemd/system/csm_web.service

    ENV=$CSM_DIR/web/web-dist/.env
    sed -i "s|CSM_UI_PATH=\"/\"|CSM_UI_PATH=\"${CSM_DIR}/${PRODUCT}/gui/ui-dist\"|g" $ENV
    sed -i "s/NODE_ENV=\"development\"/NODE_ENV=\"production\"/g" $ENV
}
exit 0

%postun
[ $1 -eq 1 ] && exit 0
rm -f /usr/bin/csm_setup 2> /dev/null;
rm -f /usr/bin/csmcli 2> /dev/null;
rm -f /usr/bin/csm_web 2> /dev/null;
rm -f /usr/bin/csm_agent 2> /dev/null;
rm -f /usr/bin/csm_test 2> /dev/null;
rm -rf /opt/seagate/csm/bin/ 2> /dev/null;
exit 0

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
