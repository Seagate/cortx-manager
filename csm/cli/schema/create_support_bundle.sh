#!/bin/bash
while getopts ":g:i:m:n:c:s" o; do
    case "${o}" in
        i)
            ID=${OPTARG}
            ;;
        m)
            COMMENT=${OPTARG}
            ;;
        n)
            NODE_NAME=${OPTARG}
            ;;
        c)
            COMPONENTS=${OPTARG}
            ;;
        s)
            OS=true
    esac
done

CSMCLI_COMMAND="csmcli bundle_generate '${ID}' '${COMMENT}' '${NODE_NAME}'"

if [ -n "$OS" ]
then
  CSMCLI_COMMAND="${CSMCLI_COMMAND} -o"
fi


if [ -n "$COMPONENTS" ]
then
  CSMCLI_COMMAND="${CSMCLI_COMMAND} -c ${COMPONENTS}"
fi

eval $CSMCLI_COMMAND
