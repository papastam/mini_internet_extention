#!/bin/bash
#
# delete links between groups and bgp monitor container

set -o errexit
set -o pipefail
set -o nounset

DIRECTORY="$1"
source "${DIRECTORY}"/config/subnet_config.sh

# read configs
readarray groups < "${DIRECTORY}"/config/AS_config.txt
group_numbers=${#groups[@]}

for ((k=0;k<group_numbers;k++)); do
    as_k=(${groups[$k]})
    as_number="${as_k[0]}"
    property="${as_k[1]}"
    router_config="${as_k[3]}"

    if [ "${as_number}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/${router_config}
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            # echo "-- --if-exists del-br ${as_number}_${rname}_exabgp"
            echo -n "-- --if-exists del-br ${as_number}_${rname}_exabgp " >> "${DIRECTORY}"/ovs_command.txt
            # echo -n "-- --if-exists del-port ${as_number}_artemis " >> "${DIRECTORY}"/ovs_command.txt
        done
    fi
done
