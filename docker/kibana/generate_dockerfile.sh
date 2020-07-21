#!/bin/sh
separator="\",\""
args=( "$@" )
regex="$( printf "${separator}%s" "${args[@]}" )"

echo "FROM docker.elastic.co/kibana/kibana-oss:6.8.10" > ./Dockerfile
echo "ENV ELASTICSEARCH_HOSTS='[\"${regex:${#separator}}\"]'" >> ./Dockerfile
echo "EXPOSE 5601" >> ./Dockerfile


