1) Generate Kibana Dockefile using generate_Dockerfile.sh, pass Elasticsearch hostnames as a parameters.
Usage:
$ ./generate_Dockerfile.sh http://FQDN1:9200 http://FQDN2:9200 http://FQDN3:9200

- You can also specify 'localhost' if ES is installed locally:

$ ./generate_Dockerfile.sh http://localhost:9200

2) Build Docker image using the Dockerfile:
$ sudo docker build .

- You can specify a repository and tag at which to save the new image:
$ sudo docker build -t repo/tag .

3) List docker images and get kibana image id:
$ sudo docker image ls
REPOSITORY                            TAG                 IMAGE ID            CREATED             SIZE
<none>                                <none>              e5870e50b337        16 minutes ago      508 MB

4) Currently, there are two different execution configuration:
4.1) Kibana is executed along with ES on the same machine. Container will share the host’s networking namespace in order to access "localhost" from within container:
$ sudo docker run --network="host" <IMAGE_ID>

4.2) ES and kibana are executed on separate machines:
- Specify ES host in the ELASTICSEARCH_HOSTS environement variable in Dockerfile
- Build image and get the ID as in 2), 3)
- $ sudo docker run <IMAGE_ID>