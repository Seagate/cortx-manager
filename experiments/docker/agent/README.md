# CSM Agent Docker Container

You need CSM Agent RPM to install it inside the container.

2. Go to the root of the source code tree.
3. Either build the RPM with `./jenkins/build.sh` script or download prebuilt RPM from the [CI server](http://ci-storage.mero.colo.seagate.com/releases/eos/components/dev/multibranch/csm/).
3. Create a symlink to the CSM Agent RPM named `csm_agent.rpm`.
4. Build the Docker image from the Dockerfile.
5. Now you can run the container with the CSM Agent inside of it.

```
$ git clone git@github.com:Seagate/cortx-csm.git /work/cortx-csm
$ cd /work/cortx-csm
$ wget http://ci-storage.mero.colo.seagate.com/releases/eos/components/dev/multibranch/csm/MR-899-merge/eos-csm_agent-1.0.0-5_98408566.x86_64.rpm
$ ln -s eos-csm_agent-1.0.0-5_98408566.x86_64.rpm csm_agent.rpm
$ docker build -t csm-agent:v0 -f experiments/docker/agent/Dockerfile .
$ docker run -d -p 28101:28101 --name csm-agent csm-agent:v0
```

To delete the container you shoud stop it and then remove it.
```
docker stop csm-agent
docker rm csm-agent
```
