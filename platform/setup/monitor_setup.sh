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
DOCKERHUB_USER="${2:-papastam}"
source "${DIRECTORY}"/config/subnet_config.sh

# read configs
readarray groups < "${DIRECTORY}"/config/AS_config.txt
group_numbers=${#groups[@]}

for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"

    # Check if the AS is a Monitored AS
    if [ "${group_as}" != "IXP" ] && [ "${group_config}" == "Monitored" ] ;then
        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        # start EXABGP_MONITOR container
        docker run -itd --net='none' --name="${group_k}_EXABGP_MONITOR"  \
            -v ${GROUPSDIR}/configs/${group_k}_exabgp.conf:/exabgp.conf \
            -v ${GROUPSDIR}/logs/${group_k}_parser.log:/parser/parser.log \
            -v ${GROUPSDIR}/output/${group_k}_output.csv:/parser/output.csv \
            --hostname="${group_k}_EXABGP_MONITOR" --cpus=2 --pids-limit 100 \
            papastam/mi-exabgp_monitor exabgp.conf

        # cache the docker pid for ovs-docker.sh
        source ${DIRECTORY}/groups/docker_pid.map
        DOCKER_TO_PID["${group_k}_EXABGP_MONITOR"]=$(docker inspect -f '{{.State.Pid}}' ${group_k}_EXABGP_MONITOR)
        declare -p DOCKER_TO_PID > ${DIRECTORY}/groups/docker_pid.map

        passwd="$(openssl rand -hex 8)"
        echo "${passwd}" >> "${DIRECTORY}"/groups/ssh_exabgp_monitor.txt
        echo -e ""${passwd}"\n"${passwd}"" | docker exec -i ${group_k}_EXABGP_MONITOR passwd root
        
        # Link the EXABGP_MONITOR container with each router
        router_cnt=0
        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            # Create bridge
            echo -n "-- add-br ${group_k}_${rname}_exabgp " >> "${DIRECTORY}"/groups/add_bridges.sh
            echo "ip link set dev ${group_k}_${rname}_exabgp up" >> "${DIRECTORY}"/groups/ip_setup.sh

            subnet_bridge="$(subnet_router_EXABGP_MONITOR "${group_number}" "bridge" "${router_cnt}")"
            subnet_exabgp_monitor="$(subnet_router_EXABGP_MONITOR "${group_number}" "monitor" "${router_cnt}")"
            subnet_group="$(subnet_router_EXABGP_MONITOR "${group_number}" "group" "${router_cnt}")"

            # Add port to EXABGP_MONITOR container
            d_part=$((router_cnt*4+2))
            gateway="${subnet_bridge%.*}.${d_part}"
            ./setup/ovs-docker.sh add-port ${group_k}_${rname}_exabgp r_"${group_number}_${rname}" ${group_k}_EXABGP_MONITOR --ipaddress="${subnet_exabgp_monitor}" --gateway="${gateway}" --route="${group_number}.0.0.0/8"

            mod=$((${group_number} % 100))
            div=$((${group_number} / 100))

            if [ $mod -lt 10 ];then
                mod="0"$mod
            fi
            if [ $div -lt 10 ];then
                div="0"$div
            fi

            # Add port to router container
            ./setup/ovs-docker.sh add-port ${group_k}_${rname}_exabgp monitor \
            "${group_number}"_"${rname}"router --ipaddress="${subnet_group}" \
            --macaddress="aa:22:22:22:"$div":"$mod

            # Connect ports
            ./setup/ovs-docker.sh connect-ports ${group_k}_${rname}_exabgp \
            r_"${group_number}_${rname}" ${group_k}_EXABGP_MONITOR \
            monitor "${group_number}"_"${rname}"router

            echo "Connected EXABGP_MONITOR container with router ${rname}"

            router_cnt=$((router_cnt+1))
        done

        echo "Created EXABGP_MONITOR container for group ${group_number}"
    fi
done
