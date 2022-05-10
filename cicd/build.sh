#!/bin/bash
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

set -e
BUILD_START_TIME=$(date +%s)
SCRIPT_DIR_NAME=$(dirname "$0")
BASE_DIR=$(realpath "$SCRIPT_DIR_NAME/..")
PROG_NAME=$(basename "$0")
DIST=$(realpath "$BASE_DIR/dist")
CORTX_PATH="/opt/seagate/cortx/"
CSM_PATH="${CORTX_PATH}csm"
CORTXCLI_PATH="${CORTX_PATH}cli"
DEBUG="DEBUG"
INFO="INFO"
CORTX_UNSUPPORTED_FEATURES_PATH="${BASE_DIR}/schema/unsupported_features.json"
BRAND_UNSUPPORTED_FEATURES_PATH="config/csm/unsupported_features.json"
CORTX_L18N_PATH="${BASE_DIR}/schema/l18n.json"
BRAND_L18N_PATH="config/csm/l18n.json"

print_time() {
    printf "%02d:%02d:%02d\n" $(( $1 / 3600 )) $(( ( $1 / 60 ) % 60 )) $(( $1 % 60 ))
}

show_stat() {
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "$1" ]; then
    DIFF=$(( $3 - $2 ))
    printf "%s BUILD TIME:  \t\t" "$4"
    print_time $DIFF
fi
}

rpm_build() {
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "$1" ]; then
    echo "rpm build CSM $1 RPM"
    echo rpmbuild --define "version $VER" --define "dist $BUILD" --define "_topdir $TOPDIR" \
            -bb "$BASE_DIR/cicd/$2.spec"
    rpmbuild --define "version $VER" --define "dist $BUILD" --define "_topdir $TOPDIR" -bb "$TMPDIR/$2.spec"
fi
}

gen_tar_file() {
TAR_START_TIME=$(date +%s)
cd "$BASE_DIR"
cd "${DIST}"
pwd
echo "Creating tar for $1 build from $2 folder"
    tar -czf "${DIST}/rpmbuild/SOURCES/${PRODUCT}-$1-${VER}.tar.gz" "$2"
TAR_END_TIME=$(($(date +%s) - TAR_START_TIME))
TAR_TOTAL_TIME=$((TAR_TOTAL_TIME + TAR_END_TIME))
}

usage() {
    echo """
usage: $PROG_NAME [-v <csm version>]
                            [-b <build no>]
                            [-p <product_name>]
                            [-c <all|backend>] [-t]
                            [-d][-i]
                            [-q <true|false>]

Options:
    -v : Build rpm with version
    -b : Build rpm with build number
    -p : Provide product name default cortx
    -c : Build rpm for [all|backend|cli]
    -n : brand name
    -l : brand file path
    -t : Build rpm with test plan
    -d : Build dev env
    -i : Build csm with integration test
    -q : Build csm with log level debug or info.
        """ 1>&2;
    exit 1;
}

while getopts ":g:v:b:p:c:n:l:tdiq" o; do
    case "${o}" in
        v)
            VER=${OPTARG}
            ;;
        b)
            BUILD=${OPTARG}
            ;;
        p)
            PRODUCT=${OPTARG}
            ;;
        c)
            COMPONENT=${OPTARG}
            ;;
        n)
            BRAND_NAME=${OPTARG}
            ;;
        l)
            BRAND_CONFIG_PATH=${OPTARG}
            ;;
        t)
            TEST=true
            ;;
        d)
            DEV=true
            ;;
        i)
            INTEGRATION=true
            ;;
        q)
            QA=true
            ;;
        *)
            usage
            ;;
    esac
done

cd "$BASE_DIR"
[ -z $"$BUILD" ] && BUILD="$(git rev-parse --short HEAD)" \
        || BUILD="${BUILD}_$(git rev-parse --short HEAD)"
[ -z "$VER" ] && VER=$(cat "$BASE_DIR/VERSION")
[ -z "$PRODUCT" ] && PRODUCT="cortx"
[ -z "$KEY" ] && KEY="cortx@ees@csm@pr0duct"
[ -z "$COMPONENT" ] && COMPONENT="all"
[ -z "$TEST" ] && TEST=false
[ -z "$INTEGRATION" ] && INTEGRATION=false
[ -z "$DEV" ] && DEV=false
[ -z "$QA" ] && QA=false

echo "Using COMPONENT=${COMPONENT} VERSION=${VER} BUILD=${BUILD} PRODUCT=${PRODUCT} TEST=${TEST}..."

################### COPY FRESH DIR ##############################

# Create fresh one to accomodate all packages.
COPY_START_TIME=$(date +%s)
DIST="$BASE_DIR/dist"
TMPDIR="$DIST/tmp"
[ -d "$TMPDIR" ] && {
    rm -rf "${TMPDIR}"
}
mkdir -p "$TMPDIR"

cd "$BASE_DIR"
rm -rf "${DIST}/rpmbuild"
mkdir -p "${DIST}/rpmbuild/SOURCES"
COPY_END_TIME=$(date +%s)

################### BRAND SPECIFIC CHANGES ######################
if [ "$BRAND_CONFIG_PATH" ]; then
	cp "$BRAND_CONFIG_PATH/$BRAND_UNSUPPORTED_FEATURES_PATH" "$CORTX_UNSUPPORTED_FEATURES_PATH"
	echo "updated unsupported_features.json from $BRAND_CONFIG_PATH/$BRAND_UNSUPPORTED_FEATURES_PATH"

	cp "$BRAND_CONFIG_PATH/$BRAND_L18N_PATH" "$CORTX_L18N_PATH"
	echo "updated l18n.json from $BRAND_CONFIG_PATH/$BRAND_L18N_PATH"
fi

################### Dependency ##########################
ENV_START_TIME=$(date +%s)
# install dependency
if [ "$DEV" == true ]; then

    # Setup Python virtual environment
    VENV="${TMPDIR}/venv"
    if [ -d "${VENV}/bin" ]; then
        echo "Using existing Python virtual environment..."
    else
        echo "Setting up Python 3.6 virtual environment..."
        python3.6 -m venv "${VENV}"
    fi
    source "${VENV}/bin/activate"
    python --version
    pip install --upgrade pip
    yum install -y cortx-py-utils
else
    pip3 install --upgrade pip
    # add cortx-py-utils below
    yum install -y cortx-py-utils
fi

# Solving numpy libgfortran-ed201abd.so.3.0.0 dependency problem
pip uninstall -y numpy
pip install numpy --no-binary :all:

ENV_END_TIME=$(date +%s)

################### Backend ##############################

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "backend" ]; then

    cp "$BASE_DIR/cicd/csm_agent.spec" "$TMPDIR"
    # Build CSM Backend
    CORE_BUILD_START_TIME=$(date +%s)
    mkdir -p "$DIST/csm/bin" "$DIST/csm/lib"

    # Copy Backend files
    cp -rf "$BASE_DIR/csm/"* "$DIST/csm"
    cp -rf "$BASE_DIR/schema" "$DIST/csm/"
    cp -rf "$BASE_DIR/templates" "$DIST/csm/"
    cp -rf "$BASE_DIR/test/" "$DIST/csm"
    cp -rf "$BASE_DIR/csm/cli/schema/csm_setup.json" "$DIST/csm/schema/"

    # Copy executables files
    cp -f "$BASE_DIR/csm/core/agent/csm_agent.py" "$DIST/csm/lib/csm_agent"
    cp -f "$BASE_DIR/csm/conf/csm_setup.py" "$DIST/csm/lib/csm_setup"
    cp -f "$BASE_DIR/csm/conf/csm_cleanup.py" "$DIST/csm/lib/csm_cleanup"
    cp -f "$BASE_DIR/csm/cli/support_bundle/csm_bundle_generate.py" "$DIST/csm/lib/csm_bundle_generate"
    cp -f "$DIST/csm/test/test_framework/csm_test.py" "$DIST/csm/lib/csm_test"
    chmod +x "$DIST/csm/lib/"*
    cd "$TMPDIR"

    # Create spec for pyinstaller
    [ "$TEST" == true ] && {
        mkdir -p "$DIST/csm/test"
        cp -R "$BASE_DIR/test/plans" "$BASE_DIR/test/test_data" "$DIST/csm/test"
    }
################## Add CSM_PATH #################################

    # Genrate spec file for CSM
    sed -i -e "s/<RPM_NAME>/${PRODUCT}-csm_agent/g" \
        -e "s|<CSM_PATH>|${CSM_PATH}|g" \
        -e "s/<PRODUCT>/${PRODUCT}/g" "$TMPDIR/csm_agent.spec"

    sed -i -e "s|<CSM_PATH>|${CSM_PATH}|g" "$DIST/csm/conf/etc/csm/csm.conf"
    sed -i -e "s|<CSM_PATH>|${CSM_PATH}|g" "$DIST/csm/conf/setup.yaml"

    gen_tar_file csm_agent csm
    rm -rf "${TMPDIR}/csm/"*
    rm -rf "${TMPDIR}/cli/"*
    CORE_BUILD_END_TIME=$(date +%s)
fi

################### Cli ##############################

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "cli" ]; then

    cp "$BASE_DIR/cicd/cortxcli.spec" "$TMPDIR"

    # Build CortxCli
    CLI_BUILD_START_TIME=$(date +%s)
    mkdir -p "$DIST/cli/lib" "$DIST/cli/bin" "$DIST/cli/conf" "$DIST/cli/cli/"

    #Copy CLI files
    cp -R "$BASE_DIR/schema" "$DIST/cli/"
    cp -R "$BASE_DIR/templates" "$DIST/cli/"
    cp -R "$BASE_DIR/csm/scripts" "$DIST/cli/"
    cp -R "$BASE_DIR/csm/cli/schema" "$DIST/cli/cli/"

    # Copy executables files
    cp -f "$BASE_DIR/csm/cli/cortxcli.py" "$DIST/cli/lib/cortxcli"
    chmod +x "$DIST/cli/lib/"*
    cd "$TMPDIR"

################## Add CORTXCLI_PATH #################################
# Genrate spec file for CSM
    sed -i -e "s/<RPM_NAME>/${PRODUCT}-cli/g" \
        -e "s|<CSM_AGENT_RPM_NAME>|${PRODUCT}-csm_agent|g" \
        -e "s|<CORTXCLI_PATH>|${CORTXCLI_PATH}|g" \
        -e "s/<PRODUCT>/${PRODUCT}/g" "$TMPDIR/cortxcli.spec"

    gen_tar_file cli cli
    rm -rf "${TMPDIR}/csm/"*
    rm -rf "${TMPDIR}/cli/"*
    CLI_BUILD_END_TIME=$(date +%s)
fi

################### RPM BUILD ##############################

# Generate RPMs
RPM_BUILD_START_TIME=$(date +%s)
TOPDIR=$(realpath "${DIST}/rpmbuild")

# CSM Backend RPM
rpm_build backend csm_agent
# Cortx Cli RPM
rpm_build cli cortxcli

RPM_BUILD_END_TIME=$(date +%s)

# Remove temporary directory
\rm -rf "${DIST}/csm"
\rm -rf "${DIST}/cli"
\rm -rf "${TMPDIR}"
BUILD_END_TIME=$(date +%s)

echo "CSM RPMs ..."
find "$BASE_DIR" -name "*.rpm"

[ "$INTEGRATION" == true ] && {
    bash "$BASE_DIR/cicd/auxiliary/csm_cicd.sh" "$DIST/rpmbuild/RPMS/x86_64" "$BASE_DIR" "$CSM_PATH"
    RESULT=$(cat /tmp/result.txt)
    cat /tmp/result.txt
    echo "$RESULT"
    [ "Failed" == "$RESULT" ] && {
        echo "CICD Failed"
        exit 1
    }
}

printf "COPY TIME:      \t\t"
print_time $(( COPY_END_TIME - COPY_START_TIME ))
printf "ENV BUILD TIME:\t\t\t"
print_time $(( ENV_END_TIME - ENV_START_TIME ))

show_stat backend "$CORE_BUILD_START_TIME" "$CORE_BUILD_END_TIME" CORE
show_stat cli "$CLI_BUILD_START_TIME" "$CLI_BUILD_END_TIME" CLI

printf "Time taken in creating TAR: \t"
print_time $TAR_TOTAL_TIME
printf "Time taken in creating RPM: \t"
print_time $(( RPM_BUILD_END_TIME - RPM_BUILD_START_TIME ))

printf "Total build time: \t\t"
print_time $(( BUILD_END_TIME - BUILD_START_TIME ))
