Name: csm-test
Version: %{version}
Release: %{dist}
Summary: Installs CSM sanity test scripts
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: csm-test-%{version}.tar.gz
Requires: csm

%description
Installs CSM sanity test scripts

%prep
%setup -n csm/test
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm/test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm/test

%post
CSM_DIR=/opt/seagate/csm/

%postun
/bin/rm -rf /opt/seagate/csm/test 2> /dev/null

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/test/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
