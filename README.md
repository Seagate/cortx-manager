# EOS Management Stack

Directory Structure
~~~~~~~~~~~~~~~~~~

cli     - Command Line Implementation
ras     - RAS Functionality
rest    - REST API Impementation
gui     - Graphical User Interface
auth    - Authentication platform

Supported Package
~~~~~~~~~~~~~~~~
pip3.6 install paramiko
pip3.6 install toml
pip3.6 install PyYAML
pip3.6 install configparser
pip3.6 install argparse
pip3.6 install paramiko

Build
~~~~~
Run the command below to generate the rpm.
$ ./jenkins/build.sh -b <build-no>

RPM would be created in dist/rpmbuild/RPMS folder.

Install csm RPMs
~~~~~~~~~~~~~~
yum localinstall -y csm-<version>.rpm
yum localinstall -y csm-test-<version>.rpm
yum localinstall -y eos-csm-<version>.rpm
yum localinstall -y eos-csm-test-<version>.rpm

Setup CSM
~~~~~~~~~~~~~~
csmcli setup init

Unit Testing
~~~~~~~~~~~~
Follow the commands given below to run unit tests for CLI.
$ cd csm
$ python -m unittest discover cli/test/

Sanity Testing
~~~~~~~~~~~~~~
1. copy samples/csm/config to /etc/csm/config. Review/Edit/Update the same.

2. copy samples/cluster.yaml to /etc/csm/cluster.yaml
   Edit /etc/csm/cluster.yaml and modify entries as per your test environment.

3. cp samples/components.yaml to /etc/csm/components.yaml

4. Make sure current user has read permission to /var/log folder.
    If not, then run the following command:
   $ chmod -R 755 /var/log

5. Edit test/args.yaml in case there are any specific test parameters to be added.

6. Run the test using the following command:
   $ test/run_test.py -t /test/plans/<test-file>.pln
