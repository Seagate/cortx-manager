Name: eos-csm
Version: %{version}
Release: %{dist}
Summary: EOS CSM
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: eos-csm-%{version}.tar.gz
Requires: csm
%define debug_package %{nil}

%description
EOS CSM Plugin

%prep
%setup -n csm/src/eos
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/csm/eos
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/csm/eos

%post
CSM_INSTALL_PATH=/opt/seagate/csm
ENV=${CSM_INSTALL_PATH}/web/.env
sed -i "s/CSM_UI_PATH=\"\"/CSM_UI_PATH=\"\/opt\/seagate\/csm\/eos\/gui\"/g" $ENV

%postun
/bin/rm -rf ${CSM_INSTALL_PATH}/eos 2> /dev/null

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
/opt/seagate/csm/eos/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
