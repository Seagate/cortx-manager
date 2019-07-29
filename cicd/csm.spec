Name: csm
Version: %{version}
Release: %{dist}
Summary: CSM Tools
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: csm-%{version}.tar.gz

%description
CSM Tools

%prep
%setup -n csm/src
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm

%post
CSM_DIR=/opt/seagate/csm
ln -sf $CSM_DIR/cli/csmcli.py /usr/bin/csmcli
mkdir -p /etc/csm/email
CFG_DIR=$CSM_DIR/conf
[ -f /etc/csm/csm.conf ] || \
    cp -R $CFG_DIR/etc/csm/csm.conf.sample /etc/csm/csm.conf
cp $CFG_DIR/etc/csm/cluster.yaml.* /etc/csm/
[ -f /etc/csm/components.yaml ] || \
    cp $CFG_DIR/etc/csm/components.yaml /etc/csm/
mkdir -p /var/csm/bundle
mkdir -p /var/log/csm
touch /var/log/csm/csm.log

%postun
/bin/rm -f /usr/bin/csmcli 2> /dev/null

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
