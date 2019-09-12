Name: csm
Version: %{version}
Release: %{dist}
Summary: CSM Tools
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: csm-%{version}.tar.gz
BuildRequires: python36-devel
%define debug_package %{nil}

%description
CSM Tools

%prep
%setup -n csm/src
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm
exit 0

%post
CSM_DIR=/opt/seagate/csm
mkdir -p /var/csm/bundle /var/log/csm /etc/csm
chmod +x $CSM_DIR/conf/csm_setup.py
chmod +x $CSM_DIR/cli/csmcli.py
chmod +x $CSM_DIR/core/agent/csm_agent.py
ln -sf $CSM_DIR/conf/csm_setup.py /usr/bin/csm_setup
ln -sf $CSM_DIR/cli/csmcli.py /usr/bin/csmcli
ln -sf $CSM_DIR/core/agent/csm_agent.py /usr/bin/csm_agent
CFG_DIR=$CSM_DIR/conf
[ -f /etc/csm/csm.conf ] || \
    cp -R $CFG_DIR/etc/csm/csm.conf.sample /etc/csm/csm.conf
[ -f /etc/csm/cluster.conf ] || \
	cp $CFG_DIR/etc/csm/cluster.conf.sample /etc/csm/cluster.conf.sample
cp -f $CSM_DIR/web/csm_web.service /etc/systemd/system/csm_web.service
cp -f $CSM_DIR/core/agent/csm_agent.service /etc/systemd/system/csm_agent.service
[ -f /etc/csm/components.yaml ] || \
    cp $CFG_DIR/etc/csm/components.yaml /etc/csm/
exit 0

%postun
[ $1 -eq 1 ] && exit 0
rm -f /usr/bin/csm_setup 2> /dev/null;
rm -f /usr/bin/csmcli 2> /dev/null;
rm -f /usr/bin/csm_web 2> /dev/null;
rm -f /usr/bin/csm_agent 2> /dev/null;
exit 0

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
