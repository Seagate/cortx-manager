# CSM Agent Docker Container

The Dockerfile for the CSM Agent container installs the Agent during the build stage from provided RPM.
You can either download the RPM from the CI server or you can build it manually.

To enable the agent inside the container to access all neccessary services on the host
you need to provide configuration files. These configuration files should contain desired host name
for each service. The files will be visible to the CSM Agent via volume mount points insede the container.

1. Go to the root of the source code tree.
2. Either build the RPM with `./jenkins/build.sh` script or download prebuilt RPM
   from the [CI server](http://ci-storage.mero.colo.seagate.com/releases/eos/components/dev/multibranch/csm/).
3. Build the Docker image from the Dockerfile specifying the path to the CSM Agent RPM.
5. Prepare configuration files and put it to the directories which later be used as a mount points inside the container.
5. Now you can run the container with the CSM Agent inside of it specifying volume directories and port to export.

Example:
```
$ git clone git@github.com:Seagate/cortx-csm.git /work/cortx-csm
$ cd /work/cortx-csm
$ wget http://ci-storage.mero.colo.seagate.com/releases/eos/components/dev/multibranch/csm/MR-899-merge/eos-csm_agent-1.0.0-5_98408566.x86_64.rpm
$ docker build -t csm-agent --rm --build-arg CSM_AGENT_RPM=eos-csm_agent-1.0.0-5_98408566.x86_64.rpm -f experiments/docker/agent/Dockerfile .
$ rpm2cpio eos-csm_agent-1.0.0-5_98408566.x86_64.rpm | cpio -idmv './opt/seagate/eos/csm/conf/etc/csm/*'
$ mkdir -p csm-etc/{csm,cortx/ha}
$ mv ./opt/seagate/eos/csm/conf/etc/csm/* csm-etc/csm/
$ cp ./experiments/docker/agent/extra/ha/database.json csm-etc/cortx/ha/database.json
$ echo -en '\nDEPLOYMENT:\n    mode: dev\n' >> csm-etc/csm/csm.conf
$ vim csm-etc/csm/csm.conf      # edit all necessary hostnames to point to the appropriate service
$ vim csm-etc/csm/database.yaml # edit all necessary hostnames to point to the appropriate service
$ vim csm-etc/ha/database.json  # edit all necessary hostnames to point to the appropriate service
$ docker run -d -p 28101:28101 -v $PWD/csm-etc/csm:/etc/csm -v $PWD/csm-etc/cortx:/etc/cortx --name csm-agent csm-agent
```

To delete the container you shoud stop it and then remove it.
```
docker stop csm-agent
docker rm csm-agent
```
