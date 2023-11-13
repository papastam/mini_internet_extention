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

    if [ "${as_number}" != "IXP" ];then
        echo -n "-- --if-exists del-br ${as_number}_exabgp " >> "${DIRECTORY}"/ovs_command.txt
        echo -n "-- --if-exists del-br ${as_number}_artemis " >> "${DIRECTORY}"/ovs_command.txt
    fi
done
