# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

Name: <RPM_NAME>
Version: %{version}
Release: %{dist}
Summary: Cortx CLI
License: Seagate Proprietary
URL: http://gitlab.mero.colo.seagate.com/eos/csm
Source0: <PRODUCT>-cli-%{version}.tar.gz
%define debug_package %{nil}

%description
Cortx CLI

%prep
%setup -n cli
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
    ln -sf $CSM_DIR/lib/cortxcli_setup /usr/bin/csm_setup
    ln -sf $CSM_DIR/lib/cortxcli_setup $CSM_DIR/bin/csm_setup

    ln -sf $CSM_DIR/lib/cortxcli /usr/bin/cortxcli
    ln -sf $CSM_DIR/lib/cortxcli $CSM_DIR/bin/cortxcli

    cp -f $CFG_DIR/service/csm_agent.service /etc/systemd/system/csm_agent.service
}

[ -d "${CSM_DIR}/test" ] && {
    ln -sf $CSM_DIR/lib/csm_test /usr/bin/csm_test
    ln -sf $CSM_DIR/lib/csm_test $CSM_DIR/bin/csm_test
}

[ -f /etc/uds/uds_s3.toml ] || \
    cp -R $CFG_DIR/etc/uds/uds_s3.toml.sample /etc/uds/uds_s3.toml
exit 0

%preun
[ $1 -eq 1 ] && exit 0

%postun
[ $1 -eq 1 ] && exit 0
rm -f /usr/bin/cortxcli_setup 2> /dev/null;
rm -f /usr/bin/cortxcli 2> /dev/null;
rm -rf <CSM_PATH>/bin/ 2> /dev/null;
exit 0

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
<CSM_PATH>/*

%changelog
* Mon Jul 29 2019 Ajay Paratmandali <ajay.paratmandali@seagate.com> - 1.0.0
- Initial spec file
