#!/bin/bash
#
# start EXA_BGP container

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
DOCKERHUB_USER="${2:-thomahol}"
source "${DIRECTORY}"/config/subnet_config.sh

mkdir -p ${GROUPSDIR}
mkdir -p ${GROUPSDIR}/configs
mkdir -p ${GROUPSDIR}/output
mkdir -p ${GROUPSDIR}/logs

# read configs
readarray groups < "${DIRECTORY}"/config/AS_config.txt
group_numbers=${#groups[@]}

# Check if there is a BGP_MONITOR container 
has_monitor=0
as_array=()
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_as="${group_k[1]}"
    group_router_config="${group_k[3]}"

    if [ "${group_as}" != "IXP" ];then
        if grep -Fq "BGP_MONITOR" "${DIRECTORY}"/config/$group_router_config; then
            has_monitor=1
            as_array+=("${group_k}")
        fi
    fi
done

# Stop the script if there is no BGP_MONITOR container
if [[ "$has_monitor" -eq 0 ]]; then
    echo "No BGP monitor specified, skipping exabgp_setup.sh"
    exit 0
fi

for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"

    if [ "${group_as}" != "IXP" ];then

        # Create as_prefixes.csv, format is: IP|AS|AS_NAME
        echo "${group_number}.0.0.0/8|${group_number}|${group_number}" >> ${GROUPSDIR}/output/as_prefixes.csv

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            if [ "${property1}" = "BGP_MONITOR"  ];then

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

                # Generate the config
                echo "neighbor $(subnet_router_EXABGP_MONITOR "${group_k}" "neighbor" ) {
local-address $(subnet_router_EXABGP_MONITOR "${group_k}" "local-address" );
local-as 10000;
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

                # start EXABGP_MONITOR container
                docker run -itd --net='none' --name="${group_k}_EXABGP_MONITOR"  \
                    -v ${GROUPSDIR}/configs/${group_k}_exabgp.conf:/exabgp.conf \
                    -v ${GROUPSDIR}/logs/${group_k}_parser.log:/parser/parser.log \
                    -v ${GROUPSDIR}/output/${group_k}_output.csv:/parser/output.csv \
                    --hostname="${group_k}_EXABGP_MONITOR" --cpus=2 --pids-limit 100 \
                    exabgp_monitor exabgp.conf

                # cache the docker pid for ovs-docker.sh
                source ${DIRECTORY}/groups/docker_pid.map
                DOCKER_TO_PID["${group_k}_EXABGP_MONITOR"]=$(docker inspect -f '{{.State.Pid}}' ${group_k}_EXABGP_MONITOR)
                declare -p DOCKER_TO_PID > ${DIRECTORY}/groups/docker_pid.map

                passwd="$(openssl rand -hex 8)"
                echo "${passwd}" >> "${DIRECTORY}"/groups/ssh_exabgp_monitor.txt
                echo -e ""${passwd}"\n"${passwd}"" | docker exec -i ${group_k}_EXABGP_MONITOR passwd root

                # FIXTHIS (or not)
                # subnet_ssh_exabgp_monitor="$(subnet_ext_sshContainer -1 "${group_k}_EXABGP_MONITOR")"
                # ./setup/ovs-docker.sh add-port ssh_to_group ssh_in ${group_k}_EXABGP_MONITOR --ipaddress="${subnet_ssh_exabgp_monitor}"

                echo -n "-- add-br ${group_k}_exabgp " >> "${DIRECTORY}"/groups/add_bridges.sh
                echo "ip link set dev ${group_k}_exabgp up" >> "${DIRECTORY}"/groups/ip_setup.sh

                subnet_bridge="$(subnet_router_EXABGP_MONITOR "${group_number}" "bridge")"
                subnet_exabgp_monitor="$(subnet_router_EXABGP_MONITOR "${group_number}" "monitor")"
                subnet_group="$(subnet_router_EXABGP_MONITOR "${group_number}" "group")"

                ./setup/ovs-docker.sh add-port ${group_k}_exabgp group_"${group_number}" ${group_k}_EXABGP_MONITOR --ipaddress="${subnet_exabgp_monitor}" --gateway="${subnet_bridge%.*}.1" --route="${group_number}.0.0.0/8"

                mod=$((${group_number} % 100))
                div=$((${group_number} / 100))

                if [ $mod -lt 10 ];then
                    mod="0"$mod
                fi
                if [ $div -lt 10 ];then
                    div="0"$div
                fi

                ./setup/ovs-docker.sh add-port ${group_k}_exabgp exabgp \
                "${group_number}"_"${rname}"router --ipaddress="${subnet_group}" \
                --macaddress="aa:22:22:22:"$div":"$mod

                ./setup/ovs-docker.sh connect-ports ${group_k}_exabgp \
                group_"${group_number}" ${group_k}_EXABGP_MONITOR \
                exabgp "${group_number}"_"${rname}"router

                echo "Created EXABGP_MONITOR container for group ${group_number}"
            
            fi
        done
    fi
done
