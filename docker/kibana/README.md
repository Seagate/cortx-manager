1) Docker image build command:
$ sudo docker build .

- You can specify a repository and tag at which to save the new image:
$ sudo docker build -t repo/tag .

2) List docker images and get kibana image id:
$ sudo docker image ls
REPOSITORY                            TAG                 IMAGE ID            CREATED             SIZE
<none>                                <none>              e5870e50b337        16 minutes ago      508 MB

3) Currently, there are two different execution configuration:
3.1) Kibana is executed along with ES on the same machine. Container will share the host’s networking namespace in order to access "localhost" from within container:
$ sudo docker run --network="host" <IMAGE_ID>

3.2) ES and kibana are executed on separate machines:
- Specify ES host in the ELASTICSEARCH_HOSTS environement variable in Dockerfile
- Build image and get the ID as in 1), 2)
- $ sudo docker run <IMAGE_ID>