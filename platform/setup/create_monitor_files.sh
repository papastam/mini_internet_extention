#!/bin/bash
#
# Create files needed for exabgp_monitor and artemis

# Source directories.
DIRECTORY="$1"
DATADIR="${DIRECTORY}/groups"
CONFIGDIR="${DIRECTORY}/config"
IMAGESDIR="${DIRECTORY}/docker_images"
EXA_DIR="${IMAGESDIR}/exabgp_monitor"
UTILSDIR="${DIRECTORY}/utils"
GROUPSDIR="${DIRECTORY}/groups/exabgp_monitor"

set -o errexit
set -o pipefail
set -o nounset

DIRECTORY="$1"
DOCKERHUB_USER="${2:-papastam}"
source "${DIRECTORY}"/config/subnet_config.sh

# read configs
readarray groups < "${DIRECTORY}"/config/AS_config.txt
group_numbers=${#groups[@]}

monitor_exists=false
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"

    if [ "${group_as}" != "IXP" ] && [ "${group_config}" == "Monitored" ];then
        monitor_exists=true
    fi
done

# if no monitor exists, dont create files
if [ "$monitor_exists" = false ]; then
    echo "No monitored ASes found, no monitor files created."
    exit 0
fi

mkdir -p ${GROUPSDIR} | true
mkdir -p ${GROUPSDIR}/configs | true 
mkdir -p ${GROUPSDIR}/output | true
mkdir -p ${GROUPSDIR}/logs | true

for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"

    if [ "${group_as}" != "IXP" ];then
        # Create as_prefixes.csv, format is: IP|AS|AS_NAME
        echo "${group_number}.0.0.0/8|${group_number}" >> ${GROUPSDIR}/as_prefixes.csv
        echo "Updated ${GROUPSDIR}/as_prefixes.csv"
    fi


    if [ "${group_as}" != "IXP" ] && [ "${group_config}" == "Monitored" ];then
        monitor_as=$((group_number+1000))

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        # Create the files if they don't exist
        umask 000; touch ${GROUPSDIR}/configs/${group_k}_exabgp.conf
        umask 000; touch ${GROUPSDIR}/logs/${group_k}_parser.log
        umask 000; touch ${GROUPSDIR}/output/${group_k}_output.csv

        #Clear config file
        umask 666 

        echo "process message-logger {
            run python3 /parser/parser.py;
            encoder json;
        }" > ${GROUPSDIR}/configs/${group_k}_exabgp.conf

        router_cnt=0
        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            # Generate the config
            echo "neighbor $(subnet_router_EXABGP_MONITOR "${group_k}" "neighbor" "${router_cnt}") {
local-address $(subnet_router_EXABGP_MONITOR "${group_k}" "local-address" "${router_cnt}");
local-as "${group_k}";
peer-as "${group_k}";
family {
    ipv4 unicast;
}
api {
    processes [ message-logger ];
    receive {
        parsed;
        update;
    }
}

}
" >> ${GROUPSDIR}/configs/${group_k}_exabgp.conf

            router_cnt=$((router_cnt+1))
            echo "Created ${GROUPSDIR}/configs/${group_k}_exabgp.conf"
        done
    fi
done