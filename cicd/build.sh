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
BASE_DIR=$(realpath "$(dirname $0)/..")
PROG_NAME=$(basename $0)
DIST=$(realpath $BASE_DIR/dist)
CORTX_PATH="/opt/seagate/cortx/"
CSM_PATH="${CORTX_PATH}csm"
CORTXCLI_PATH="${CORTX_PATH}cli"
DEBUG="DEBUG"
INFO="INFO"
PROVISIONER_CONFIG_PATH="${CORTX_PATH}provisioner/generated_configs"

print_time() {
    printf "%02d:%02d:%02d\n" $(( $1 / 3600 )) $(( ( $1 / 60 ) % 60 )) $(( $1 % 60 ))
}

show_stat() {
if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "$1" ]; then
    DIFF=$(( $3 - $2 ))
    printf "$4 BUILD TIME:  \t\t"
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
cd $BASE_DIR
cd ${DIST}
pwd
echo "Creating tar for $1 build from $2 folder"
    tar -czf "${DIST}/rpmbuild/SOURCES/${PRODUCT}-$1-${VER}.tar.gz" "$2"
TAR_END_TIME=$(($(date +%s) - TAR_START_TIME))
TAR_TOTAL_TIME=$((TAR_TOTAL_TIME + TAR_END_TIME))
}

rm_list() {
    sed -i -e "s|<PATH>|${DIST}/$2|g" "$1"
    for x in $(cat $1);do rm -r $x;done;
}

install_py_req() {
    # Check python package
    req_file=$BASE_DIR/cicd/pyinstaller/$1
    echo "Installing python packages..."
    pip install -r "$req_file" || {
        echo "Unable to install package from $req_file"; exit 1;
    };
}

usage() {
    echo """
usage: $PROG_NAME [-v <csm version>]
                            [-b <build no>] [-k <key>]
                            [-p <product_name>]
                            [-c <all|backend>] [-t]
                            [-d][-i]
                            [-q <true|false>]

Options:
    -v : Build rpm with version
    -b : Build rpm with build number
    -k : Provide key for encryption of code
    -p : Provide product name default cortx
    -c : Build rpm for [all|backend|cli]
    -t : Build rpm with test plan
    -d : Build dev env
    -i : Build csm with integration test
    -q : Build csm with log level debug or info.
        """ 1>&2;
    exit 1;
}

while getopts ":g:v:b:p:k:c:tdiq" o; do
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
        k)
            KEY=${OPTARG}
            ;;
        c)
            COMPONENT=${OPTARG}
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

cd $BASE_DIR
[ -z $"$BUILD" ] && BUILD="$(git rev-parse --short HEAD)" \
        || BUILD="${BUILD}_$(git rev-parse --short HEAD)"
[ -z "$VER" ] && VER=$(cat $BASE_DIR/VERSION)
[ -z "$PRODUCT" ] && PRODUCT="cortx"
[ -z "$KEY" ] && KEY="cortx@ees@csm@pr0duct"
[ -z "$COMPONENT" ] && COMPONENT="all"
[ -z "$TEST" ] && TEST=false
[ -z "$INTEGRATION" ] && INTEGRATION=false
[ -z "$DEV" ] && DEV=false
[ -z "$QA" ] && QA=false

echo "Using VERSION=${VER} BUILD=${BUILD} PRODUCT=${PRODUCT} TEST=${TEST}..."

################### COPY FRESH DIR ##############################

# Create fresh one to accomodate all packages.
COPY_START_TIME=$(date +%s)
DIST="$BASE_DIR/dist"
TMPDIR="$DIST/tmp"
[ -d "$TMPDIR" ] && {
    rm -rf ${TMPDIR}
}
mkdir -p $TMPDIR

CONF=$BASE_DIR/csm/conf/
CLI_CONF=$BASE_DIR/csm/cli/conf/

cd $BASE_DIR
rm -rf ${DIST}/rpmbuild
mkdir -p ${DIST}/rpmbuild/SOURCES
COPY_END_TIME=$(date +%s)

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
    pip install pyinstaller==3.5

    install_py_req requirment.txt
    install_py_req req_dev.txt

    # Solving numpy libgfortran-ed201abd.so.3.0.0 dependency problem
    pip uninstall -y numpy
    pip install numpy --no-binary :all:
else
    pip3 install --upgrade pip
    pip3 install pyinstaller==3.5
    yum install -y eos-py-utils cortx-prvsnr

    # Check python package
    install_py_req requirment.txt
fi
ENV_END_TIME=$(date +%s)
################### Backend ##############################

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "backend" ]; then

cp "$BASE_DIR/cicd/csm_agent.spec" "$TMPDIR"

    # Build CSM Backend
    CORE_BUILD_START_TIME=$(date +%s)
    mkdir -p $DIST/csm/conf/service
    cp $CONF/setup.yaml $DIST/csm/conf
    cp -R $CONF/etc $DIST/csm/conf
    cp -R $CONF/service/csm_agent.service $DIST/csm/conf/service
    cd $TMPDIR

    # Copy Backend files
    mkdir -p $DIST/csm/lib $DIST/csm/bin $DIST/csm/conf $TMPDIR/csm
    cp -rs $BASE_DIR/csm/* $TMPDIR/csm
    cp -rs $BASE_DIR/test/ $TMPDIR/csm

    cp -R $BASE_DIR/schema $DIST/csm/
    cp -R $BASE_DIR/templates $DIST/csm/
    cp -R "$BASE_DIR/csm/scripts" "$DIST/csm/"
    cp -R "$BASE_DIR/csm/cli/schema/csm_setup.json" "$DIST/csm/schema/"

    cp $BASE_DIR/cicd/csm_agent.rm $TMPDIR/
    rm_list $TMPDIR/csm_agent.rm csm

    # Create spec for pyinstaller
    [ "$TEST" == true ] && {
        PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_csm_test.spec
        cp "$BASE_DIR/cicd/pyinstaller/product_csm_test.spec" "${PYINSTALLER_FILE}"
        mkdir -p $DIST/csm/test
        cp -R $BASE_DIR/test/plans $BASE_DIR/test/test_data $DIST/csm/test
    } || {
        PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_csm.spec
        cp "$BASE_DIR/cicd/pyinstaller/product_csm.spec" "${PYINSTALLER_FILE}"
    }

    sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
        -e "s|<CSM_PATH>|${TMPDIR}/csm|g" ${PYINSTALLER_FILE}
    python3 -m PyInstaller --clean -y --distpath "${DIST}/csm" --key "${KEY}" "${PYINSTALLER_FILE}"
################## Add CSM_PATH #################################

    # Genrate spec file for CSM
    sed -i -e "s/<RPM_NAME>/${PRODUCT}-csm_agent/g" \
        -e "s|<CSM_PATH>|${CSM_PATH}|g" \
        -e "s/<PRODUCT>/${PRODUCT}/g" $TMPDIR/csm_agent.spec

    sed -i -e "s|<CORTX_PATH>|${CORTX_PATH}|g" $DIST/csm/schema/commands.yaml
    sed -i -e "s|<CSM_PATH>|${CSM_PATH}|g" $DIST/csm/conf/etc/csm/csm.conf
    sed -i -e "s|<CSM_PATH>|${CSM_PATH}|g" $DIST/csm/conf/etc/rsyslog.d/2-emailsyslog.conf.tmpl
    sed -i -e "s|<CSM_PATH>|${CSM_PATH}|g" $DIST/csm/conf/setup.yaml
    sed -i -e "s|<PROVISIONER_CONFIG_PATH>|${PROVISIONER_CONFIG_PATH}|g" $DIST/csm/conf/etc/csm/csm.conf

    if [ "$QA" == true ]; then
        sed -i -e "s|<LOG_LEVEL>|${DEBUG}|g" $DIST/csm/conf/etc/csm/csm.conf
    else
        sed -i -e "s|<LOG_LEVEL>|${INFO}|g" $DIST/csm/conf/etc/csm/csm.conf
    fi

    gen_tar_file csm_agent csm
    rm -rf ${TMPDIR}/csm/*
    rm -rf ${TMPDIR}/cli/*
    CORE_BUILD_END_TIME=$(date +%s)
fi

################### Cli ##############################

if [ "$COMPONENT" == "all" ] || [ "$COMPONENT" == "cli" ]; then

cp "$BASE_DIR/cicd/cortxcli.spec" "$TMPDIR"

    # Build CortxCli
    CLI_BUILD_START_TIME=$(date +%s)
    mkdir -p $DIST/cli/conf/service
    cp $CLI_CONF/setup.yaml $DIST/cli/conf/setup.yaml
    cp -R $CONF/etc $DIST/cli/conf
    cd $TMPDIR

    # Copy Backend files
    mkdir -p $DIST/cli/lib $DIST/cli/bin $DIST/cli/conf $TMPDIR/csm
    cp -rs $BASE_DIR/csm/* $TMPDIR/csm
    #TODO: Allow test to work with cli

    cp -R $BASE_DIR/schema $DIST/cli/
    cp -R $BASE_DIR/templates $DIST/cli/
    cp -R "$BASE_DIR/csm/scripts" "$DIST/cli/"
    mkdir -p  $DIST/cli/cli/
    cp -R "$BASE_DIR/csm/cli/schema" "$DIST/cli/cli/"

    cp $BASE_DIR/cicd/cortxcli.rm $TMPDIR/
    rm_list $TMPDIR/cortxcli.rm cli

    PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_cli.spec
    cp "$BASE_DIR/cicd/pyinstaller/product_cli.spec" "${PYINSTALLER_FILE}"

    sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
        -e "s|<CORTXCLI_PATH>|${TMPDIR}/csm|g" ${PYINSTALLER_FILE}
    python3 -m PyInstaller --clean -y --distpath "${DIST}/cli" --key "${KEY}" "${PYINSTALLER_FILE}"
################## Add CORTXCLI_PATH #################################

# Genrate spec file for CSM
    sed -i -e "s/<RPM_NAME>/${PRODUCT}-cli/g" \
        -e "s|<CORTXCLI_PATH>|${CORTXCLI_PATH}|g" \
        -e "s/<PRODUCT>/${PRODUCT}/g" $TMPDIR/cortxcli.spec

    sed -i -e "s|<CORTX_PATH>|${CORTX_PATH}|g" $DIST/cli/schema/commands.yaml

    if [ "$QA" == true ]; then
        sed -i -e "s|<LOG_LEVEL>|${DEBUG}|g" $DIST/cli/conf/etc/csm/cortxcli.conf
    else
        sed -i -e "s|<LOG_LEVEL>|${INFO}|g" $DIST/cli/conf/etc/csm/cortxcli.conf
    fi

    gen_tar_file cli cli
    rm -rf ${TMPDIR}/csm/*
    rm -rf ${TMPDIR}/cli/*
    CLI_BUILD_END_TIME=$(date +%s)
fi


################### RPM BUILD ##############################

# Generate RPMs
RPM_BUILD_START_TIME=$(date +%s)
TOPDIR=$(realpath ${DIST}/rpmbuild)

# CSM Backend RPM
rpm_build backend csm_agent
# Cortx Cli RPM
rpm_build cli cortxcli

RPM_BUILD_END_TIME=$(date +%s)

# Remove temporary directory
\rm -rf ${DIST}/csm
\rm -rf ${DIST}/cli
\rm -rf ${TMPDIR}
BUILD_END_TIME=$(date +%s)

echo "CSM RPMs ..."
find $BASE_DIR -name *.rpm

[ "$INTEGRATION" == true ] && {
    INTEGRATION_TEST_START=$(date +%s)
    bash "$BASE_DIR/cicd/auxiliary/csm_cicd.sh" "$DIST/rpmbuild/RPMS/x86_64" "$BASE_DIR" "$CSM_PATH"
    RESULT=$(cat /tmp/result.txt)
    cat /tmp/result.txt
    echo $RESULT
    [ "Failed" == $RESULT ] && {
        echo "CICD Failed"
        exit 1
    }
    INTEGRATION_TEST_STOP=$(date +%s)
}

printf "COPY TIME:      \t\t"
print_time $(( $COPY_END_TIME - $COPY_START_TIME ))
printf "ENV BUILD TIME:\t\t\t"
print_time $(( $ENV_END_TIME - $ENV_START_TIME ))

show_stat backend $CORE_BUILD_START_TIME $CORE_BUILD_END_TIME CORE
show_stat cli $CLI_BUILD_START_TIME $CLI_BUILD_END_TIME CLI

printf "Time taken in creating TAR: \t"
print_time $TAR_TOTAL_TIME
printf "Time taken in creating RPM: \t"
print_time $(( $RPM_BUILD_END_TIME - $RPM_BUILD_START_TIME ))

printf "Total build time: \t\t"
print_time $(( $BUILD_END_TIME - $BUILD_START_TIME ))
