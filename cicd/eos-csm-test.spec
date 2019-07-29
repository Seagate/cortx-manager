Name: eos-csm-test
Version: %{version}
Release: %{dist}
Summary: Installs EOS CSM sanity test scripts
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: eos-csm-test-%{version}.tar.gz
Requires: csm eos-csm csm-test

%description
Installs CSM sanity test scripts

%prep
%setup -n csm/test/eos
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm/test/eos
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm/test/eos

%post
CSM_DIR=/opt/seagate/csm/

%postun
/bin/rm -rf /opt/seagate/csm/test/eos 2> /dev/null

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/test/eos/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
