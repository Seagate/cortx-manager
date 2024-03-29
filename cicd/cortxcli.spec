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
License: Seagate
URL: http://github.com/Seagate/cortx-manager
Source0: <PRODUCT>-cli-%{version}.tar.gz
Requires: <CSM_AGENT_RPM_NAME>

%define debug_package %{nil}

%description
Cortx CLI

%prep
%setup -n cli
# Nothing to do here

%build

%install
mkdir -p ${RPM_BUILD_ROOT}<CORTXCLI_PATH>
cp -rp . ${RPM_BUILD_ROOT}<CORTXCLI_PATH>
exit 0

%post
CLI_DIR=<CORTXCLI_PATH>
PRODUCT=<PRODUCT>

# Move binary file
[ -d "${CLI_DIR}/lib" ] && {
    ln -sf $CLI_DIR/lib/cortxcli /usr/bin/cortxcli
    ln -sf $CLI_DIR/lib/cortxcli $CLI_DIR/bin/cortxcli
    ln -sf $CLI_DIR/lib/cli_setup /usr/bin/cli_setup
    ln -sf $CLI_DIR/lib/cli_setup $CLI_DIR/bin/cli_setup
}

#TODO: add test for cli
exit 0

%preun

%postun
[ $1 -eq 1 ] && exit 0
rm -f /usr/bin/cortxcli 2> /dev/null;
rm -f /usr/bin/cli_setup 2> /dev/null;
rm -rf <CORTXCLI_PATH>/bin/ 2> /dev/null;
exit 0

%clean

%files
# TODO - Verify permissions, user and groups for directory.
%defattr(-, root, root, -)
<CORTXCLI_PATH>/*

%changelog
* Mon Sep 7 2020 Eduard Aleksandrov <eduard.aleksandrov@seagate.com> - 1.0.0
- Initial spec file for cortxcli
