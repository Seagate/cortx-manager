# Update LOCAL_DOCKER_REGISTRY tag with docker registry

1. You can use update_local_registry.sh to update docker registry
```
[root@ssc-vm-0511 tmp]# sh update_local_registry.sh -h
This script will update LOCAL_DOCKER_REGISTRY label from
all yaml file from given dir to given docker registry host:port

Usage:
sh update_local_registry.sh -d <target dir> -host <docker registry host> -port <registry port>
```

Options: -d location of yaml file (directory)
         -host hostname of new docker registry
         -port port for docker registry

Example: 
[root@ssc-vm-c-057 cortx-csm]# sh experiments/kubernetes/update_local_registry.sh -host ssc-vm-0508.colo.seagate.com -port 5000 -d ./experiments/kubernetes/

Output:

Docker registry: ssc-vm-0508.colo.seagate.com:5000
running command : find './experiments/kubernetes/' -type f -name '*.yaml' | xargs sed -i 's/LOCAL_DOCKER_REGISTRY/ssc-vm-0508.colo.seagate.com:5000/';
Successfully : find './experiments/kubernetes/' -type f -name '*.yaml' | xargs sed -i 's/LOCAL_DOCKER_REGISTRY/ssc-vm-0508.colo.seagate.com:5000/';

