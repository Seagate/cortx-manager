#!/usr/bin/bash

run_command()
{
echo "running command : $1"
eval $1
if [ "$?" -eq 0 ]; then
    echo "Successfully ran command: $1"
else
    echo "failed : $1"
    exit 1
fi

}


usage()
{
    echo "\
This script will update LOCAL_DOCKER_REGISTRY label from 
all yaml file from given dir to given docker registry host:port 

Usage:
sh update_local_registry.sh -d <target dir> -host <docker registry host> -port <registry port>

"
}
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage; exit 0
        ;;
        -d)
            [ -z "$2" ] &&
                echo "Error: Target dir not provided" && exit 1;
            dest_dir="$2"
            shift 2 ;;     
        -host)
            [ -z "$2" ] &&
                echo "Error: Docker registry not provided" && exit 1;
            host="$2"
            shift 2 ;;
        -port)
            [ -z "$2" ] &&
                echo "Error: Registry port not provided" && exit 1;
            port="$2"
            shift 2 ;;
        *) echo "Invalid option $1"; usage; exit 1;;
    esac
done


local_restory="$host:$port"
echo "Docker registry: $local_restory"

run_command "find '$dest_dir' -type f -name '*.yaml' | xargs sed -i 's/LOCAL_DOCKER_REGISTRY/$local_restory/';"
