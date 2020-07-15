# CSM Agent continer on kubernetes

You need CSM Agent image to deploy pod and service

# Prequisites
1. Create csm-agent image using Dockerfile
2. Create local docker repository

# Push images to local repository

1. make sure you have local csm agent image 
2. Add tag local csm-agent image 
```
$ docker tag csm-agent ssc-vm-0508.colo.seagate.com:5000/csm-agent
```
NOTE: ssc-vm-0508.colo.seagate.com:5000 is local docker registry

3. push image to local docker registry
```
$ docker push ssc-vm-0508.colo.seagate.com:5000/csm-agent
```
4. Pull reloader image and push it to local registry  which is used in furthur steps
```
$ docker pull stakater/reloader:v0.0.60
$ docker tag docker.io/stakater/reloader:v0.0.60 ssc-vm-0508.colo.seagate.com:5000/reloader:v0.0.60
$ docker push ssc-vm-0508.colo.seagate.com:5000/reloader:v0.0.60
```
5. Verify if csm-agent and reloader images uploaded in local registry
```
$ curl -X GET ssc-vm-0508.colo.seagate.com:5000/v2/_catalog
```
Output :
```
[root@ssc-vm-c-927 csm_agent]# curl -X GET ssc-vm-0508.colo.seagate.com:5000/v2/_catalog
{"repositories":["csm-agent","csm-web","csm-web-v1","my-ubuntu","reloader"]}
```

# Create configmap for csm-agent configs

1. Create local config folder and copy cluster.conf,csm.conf and database.yaml into config folder 
2. Create configmap using below command
```
$ kubectl create configmap csm-agent-config --from-file=config/
```
3. You can get all config from configmap 
```
$ kubectl describe configmaps csm-agent-config
```

# Create csm-agent POD using csm-agent image

1. Using experiments/kubernetes/csm_agent/csm_agent_pod.yaml you can create deployment which will create 
  pod for csm-agent
```
$ kubectl apply -f csm_agent_pod.yaml
```
2. verify pods is running or not
```
$ kubectl get pods 
```
Output:
```
[root@ssc-vm-c-927 csm_agent]# kubectl get pods
NAME                                      READY   STATUS        RESTARTS   AGE
csm-agent-565cdc799b-4zhcj                1/1     Running       0          3d13h
csm-web-5455fdd7dc-w745w                  1/1     Running       0          3d13h

```

# Create csm-agent kubernetes service
This service will be used to communicate between csm-agent and csm-web.
csm-web can access csm-agent service directly in any pod from kuberenetes cluster

1. Using experiments/kubernetes/csm_agent/csm_agent_service.yaml you can create service
```
$ kubectl apply -f csm_agent_service.yaml
```
2. Verify if service is  running or not.
```
$ kubectl get services
```
Output:
```
[root@ssc-vm-c-927 csm_agent]# kubectl get services
NAME              TYPE        CLUSTER-IP       EXTERNAL-IP   PORT(S)           AGE
csm-agent-svc     NodePort    10.98.13.61      <none>        28101:32101/TCP   4d
csm-web-svc       NodePort    10.108.114.151   <none>        28100:32100/TCP   4d
docker-registry   NodePort    10.100.207.220   <none>        5000:30002/TCP    6d21h

```
We can access csm-agent service externally using <master-ip>:32101 <nodeport> given in csm_agent_service.yaml file.
Also csm-agent can be accessed to all pods in cluster using <servive-name>:28101 port example : csm-agent-svc:28101

# Reloader to update pods
If someone changes any configmap value then reloader can watch changes in ConfigMap rolling upgrades on Pods with their associated DeploymentConfigs, Deployments, Daemonsets and Statefulsets. 

1. Using experiments/kubernetes/csm_agent/reloader.yaml you can deploy Reloader

```
$ kubectl apply -f reloader.yaml
```
2. We have already added below lines in our csm_agent_pods.yaml

```
annotations:
    configmap.reloader.stakater.com/reload: "csm-agent-config"
```
# Edit ConfigMap
We have attached ConfigMap as volume in pods so any changes in configMaps will be directly reflects in 
that volume (files)

command to edit configMap , Update configMap and save it

```
kubectl edit configmap csm-agent-config
```
One can Update ConsulDB and ElasticsearchDB host with running instances of it , any vm ip
or any kubernetes service name.

# Delete kubernetes objects - deployment, pod nad services

1. you can delete deployment, pod and services using command

```
$ kubectl delete <pods>/<services>/<deployment> <name_pod>/<name_service>/<name_deployment>
```
