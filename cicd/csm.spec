Name: csm
Version: %{version}
Release: %{dist}
Summary: Seagate Object Storage CSM Tools
License: Seagate Proprietary
URL: http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/csm
Source0: csm-%{version}.tar.gz
Requires: initscripts fontconfig
Requires: graphite-web python-carbon python-requests
Requires: PyYAML python-paramiko

%description
Seagate Object Storage CSM Tools

%prep
%setup -n csm
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm
ln -s /opt/seagate/csm/config/csm_init $RPM_BUILD_ROOT/opt/seagate/csm/csm_init

%post
ln -sf /opt/seagate/csm/cli/csmcli.py /usr/bin/csmcli
mkdir -p /etc/csm/email
CFG_DIR=/opt/seagate/csm/config
cp $CFG_DIR/etc/csm/cluster.yaml.* /etc/csm/
[ -f /etc/csm/components.yaml ] || cp $CFG_DIR/etc/csm/components.yaml /etc/csm/
mkdir -p /var/csm/bundle
touch /var/log/csm.log
[ -f /etc/csm.conf ] || cp -R $CFG_DIR/etc/csm.conf.sample /etc/csm.conf

%postun
/bin/rm -f /usr/bin/csmcli 2> /dev/null
/bin/rm -f /opt/seagate/csm/csm_init 2> /dev/null

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/*

%changelog
* Mon Jul 16 2018 Malhar Vora <malhar.vora@seagate.com> - 1.0.0
- Initial spec file
