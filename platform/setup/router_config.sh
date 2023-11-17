#!/bin/bash
#
# creates an initial configuration for every router
# load configuration into router

set -o errexit
set -o pipefail
set -o nounset

DIRECTORY="$1"
source "${DIRECTORY}"/config/subnet_config.sh
source "${DIRECTORY}"/setup/_parallel_helper.sh

# read configs
readarray groups < "${DIRECTORY}"/config/AS_config.txt
readarray extern_links < "${DIRECTORY}"/config/aslevel_links.txt
readarray l2_switches < "${DIRECTORY}"/config/l2_switches.txt
readarray l2_links < "${DIRECTORY}"/config/l2_links.txt
readarray l2_hosts < "${DIRECTORY}"/config/l2_hosts.txt

group_numbers=${#groups[@]}
n_extern_links=${#extern_links[@]}
n_l2_switches=${#l2_switches[@]}
n_l2_links=${#l2_links[@]}
n_l2_hosts=${#l2_hosts[@]}

# create initial configuration for each router
for ((k=0;k<group_numbers;k++));do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        readarray intern_links < "${DIRECTORY}"/config/$group_internal_links
        n_routers=${#routers[@]}
        n_intern_links=${#intern_links[@]}

        # Initlization the associative array to configure the layer2 subnet advertisements
        declare -A l2_id
        idtmp=1
        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            property1="${router_i[1]}"
            property2="${router_i[2]}"
            if [[ "${property2}" == *L2* ]];then
                l2_id[$property2]=0
            fi
        done
        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            property2="${router_i[2]}"
            if [[ "${property2}" == *L2* ]];then
                if [[ "${l2_id[$property2]}" -eq "0" ]]; then
                    l2_id[$property2]=$idtmp
                    idtmp=$(($idtmp+1))
                fi
            fi
        done

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"
            property2="${router_i[2]}"
            dname=$(echo $property2 | cut -s -d ':' -f 2)

            if [ ${#rname} -gt 10 ]; then
                echo 'ERROR: Router names must have a length lower or equal than 10'
                exit 1
            fi

            touch "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh
            chmod +x "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh

            touch "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh
            chmod +x "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh

            touch "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh
            chmod +x "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh

            location="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh
            location_nr="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh

            {
                echo "#!/bin/bash"
                echo "vtysh  -c 'conf t' \\"
                echo " -c 'interface lo' \\"
                echo " -c 'ip address "$(subnet_router "${group_number}" "${i}")"' \\"
                echo " -c 'exit' \\"
                if [[ ! -z "${dname}" ]];then
                    echo " -c 'interface host' \\"
                    echo " -c 'ip address "$(subnet_host_router "${group_number}" "${i}" "router")"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router ospf' \\"
                    echo " -c 'network "$(subnet_host_router "${group_number}" "${i}" "router")" area 0' \\"
                    echo " -c 'exit' \\"
                fi

                if [[ "${property2}" == *L2* ]];then
                        echo " -c 'router ospf' \\"
                        echo " -c 'network "$(subnet_l2_router "${group_number}" $((${l2_id[$property2]}-1)))" area 0' \\"
                        echo " -c 'exit'\\"
                fi

                router_id=$(subnet_router "${group_number}" "${i}")

                echo " -c 'router ospf' \\"
                echo " -c 'ospf router-id "${router_id%/*}"' \\"
                echo " -c 'network "$(subnet_router "${group_number}" "${i}")" area 0' \\"
                echo " -c 'exit'\\"
                echo " -c 'ip route "$(subnet_group "${group_number}")" null0' \\"
                echo " -c 'ip prefix-list OWN_PREFIX seq 5 permit "$(subnet_group "${group_number}")"' \\"
                echo " -c 'route-map OWN_PREFIX permit 10' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"

                for ((j=0;j<n_routers;j++)); do
                    router_j=(${routers[$j]})
                    rname2="${router_j[0]}"
                    if [ "${rname}" != "${rname2}" ]; then
                        subnet="$(subnet_router "${group_number}" "${j}")"
                        echo " -c 'router bgp "${group_number}"' \\"
                        echo " -c 'network "$(subnet_group "${group_number}")"' \\"
                        echo " -c 'neighbor "${subnet%???}" remote-as "${group_number}"' \\"
                        echo " -c 'neighbor "${subnet%???}" update-source lo' \\"
                        echo " -c 'neighbor "${subnet%???}" next-hop-self' \\"
                        # echo " -c 'address-family ipv6 unicast' \\"
                        # echo " -c 'neighbor "${subnet%???}" activate' \\"
                        # echo " -c 'exit' \\"
                        echo " -c 'exit' \\"
                    fi
                done
            } >> "${location}"
        done

        for ((i=0;i<n_intern_links;i++)); do
            row_i=(${intern_links[$i]})
            router1="${row_i[0]}"
            router2="${row_i[1]}"
            location1="${DIRECTORY}"/groups/g"${group_number}"/"${router1}"/init_full_conf.sh
            location2="${DIRECTORY}"/groups/g"${group_number}"/"${router2}"/init_full_conf.sh
            {
                echo " -c 'interface port_"${router2}"' \\"
                echo " -c 'ip address "$(subnet_router_router_intern "${group_number}" "${i}" 1)"' \\"
                echo " -c 'ip ospf cost 1' \\"
                echo " -c 'exit' \\"
                echo " -c 'router ospf' \\"
                echo " -c 'network "$(subnet_router_router_intern "${group_number}" "${i}" 1)" area 0' \\"
                echo " -c 'exit' \\"
            } >> "${location1}"
            {
                echo " -c 'interface port_"${router1}"' \\"
                echo " -c 'ip address "$(subnet_router_router_intern "${group_number}" "${i}" 2)"' \\"
                echo " -c 'ip ospf cost 1' \\"
                echo " -c 'exit' \\"
                echo " -c 'router ospf' \\"
                echo " -c 'network "$(subnet_router_router_intern "${group_number}" "${i}" 2)" area 0' \\"
                echo " -c 'exit' \\"
            } >> "${location2}"
        done

        # Copy full config to no rules config since no rules are applied in this point
        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            cp "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh
        
            # Create a empty route-map
            {
                echo " -c 'route-map empty_in permit 10' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map empty_out permit 10' \\"
                echo " -c 'exit' \\"
            } >> "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh
        done

    else # If IXP
        touch "${DIRECTORY}"/groups/g"${group_number}"/init_full_conf.sh
        chmod +x "${DIRECTORY}"/groups/g"${group_number}"/init_full_conf.sh

        location="${DIRECTORY}"/groups/g"${group_number}"/init_full_conf.sh

        {
            echo "#!/bin/bash"
            echo "vtysh  -c 'conf t' \\"
            echo "-c 'bgp multiple-instance' \\"

            for ((i=0;i<n_extern_links;i++)); do
                row_i=(${extern_links[$i]})
                grp_1="${row_i[0]}"
                router_grp_1="${row_i[1]}"
                grp_2="${row_i[3]}"
                router_grp_2="${row_i[4]}"

                if [ "${group_number}" = "${grp_1}" ] || [ "${group_number}" = "${grp_2}" ];then
                    if [ "${group_number}" = "${grp_1}" ];then
                        grp_1="${row_i[2]}"
                        router_grp_1="${row_i[3]}"
                        grp_2="${row_i[0]}"
                        router_grp_2="${row_i[1]}"
                    fi

                    subnet1="$(subnet_router_IXP "${grp_1}" "${grp_2}" "group")"
                    subnet2="$(subnet_router_IXP "${grp_1}" "${grp_2}" "IXP")"

                    echo " -c 'ip community-list "${grp_1}" permit "${grp_2}"":""${grp_1}"' \\"
                    echo " -c 'route-map "${grp_1}"_EXPORT permit 10' \\"
                    echo " -c 'set ip next-hop "${subnet1%/*}"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'route-map "${grp_1}"_IMPORT permit 10' \\"
                    echo " -c 'match community "${grp_1}"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router bgp "${grp_2}"' \\"
                    echo " -c 'bgp router-id 180.80.${grp_2}.0' \\"
                    echo " -c 'neighbor "${subnet1%/*}" remote-as "${grp_1}"' \\"
                    echo " -c 'neighbor "${subnet1%/*}" activate' \\"
                    echo " -c 'neighbor "${subnet1%/*}" route-server-client' \\"
                    echo " -c 'neighbor "${subnet1%/*}" route-map "${grp_1}"_IMPORT import' \\"
                    echo " -c 'neighbor "${subnet1%/*}" route-map "${grp_1}"_EXPORT export' \\"
                    echo " -c 'exit' \\"

                    docker exec -d "${group_number}"_IXP bash -c "ovs-vsctl add-port IXP grp_${grp_1}"
                fi
            done
        } >> "${location}"

    fi
done

# for every connection in ./config/aslevel_links.txt
# configure the subnet as defined in ./config/subnet_config.sh
for ((i=0;i<n_extern_links;i++)); do
    row_i=(${extern_links[$i]})
    grp_1="${row_i[0]}"
    router_grp_1="${row_i[1]}"
    relation_grp_1="${row_i[2]}"
    grp_2="${row_i[3]}"
    router_grp_2="${row_i[4]}"
    relation_grp_2="${row_i[5]}"
    throughput="${row_i[6]}"
    delay="${row_i[7]}"

    for ((k=0;k<group_numbers;k++)); do
        group_k=(${groups[$k]})
        group_number="${group_k[0]}"
        group_as="${group_k[1]}"

        if [ "${grp_1}" = "${group_number}" ];then
            group_as_1="${group_as}"
        elif [ "${grp_2}" = "${group_number}" ];then
            group_as_2="${group_as}"
        fi
    done

    if [ "${group_as_1}" = "IXP" ] || [ "${group_as_2}" = "IXP" ];then
        if [ "${group_as_1}" = "IXP" ];then
            grp_1="${row_i[3]}"
            router_grp_1="${row_i[4]}"
            grp_2="${row_i[0]}"
            router_grp_2="${row_i[1]}"
        fi

        ixp_peers="${row_i[8]}"

        subnet1="$(subnet_router_IXP "${grp_1}" "${grp_2}" "group")"
        subnet2="$(subnet_router_IXP "${grp_1}" "${grp_2}" "IXP")"
        location="${DIRECTORY}"/groups/g"${grp_1}"/"${router_grp_1}"/init_full_conf.sh

        {
            echo " -c 'interface ixp_"${grp_2}"' \\"
            echo " -c 'ip address "${subnet1}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_1}"' \\"
            echo " -c 'network "$(subnet_group "${grp_1}")"' \\"
            echo " -c 'neighbor "${subnet2%???}" remote-as "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet2%???}" activate' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map IXP_OUT_${grp_2} out' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map IXP_IN_${grp_2} in' \\"
            echo " -c 'exit' \\"

            str_tmp=''
            for peer in $(echo $ixp_peers | sed "s/,/ /g"); do
                str_tmp=${str_tmp}${grp_2}:${peer}" "
            done

            echo " -c 'bgp community-list 1 permit $grp_1:10' \\"
            echo " -c 'route-map IXP_OUT_${grp_2} permit 10' \\"
            echo " -c 'set community $str_tmp' \\"
            echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
            echo " -c 'exit' \\"
            echo " -c 'route-map IXP_OUT_${grp_2} permit 20' \\"
            echo " -c 'set community $str_tmp' \\"
            echo " -c 'match community 1' \\"
            echo " -c 'exit' \\"
            echo " -c 'route-map IXP_IN_${grp_2} permit 10' \\"
            echo " -c 'set community $grp_1:20' \\"
            echo " -c 'set local-preference 50' \\"

            echo " -c 'exit' \\"
        } >> "${location}"

        # No rules config
        nr_location="${DIRECTORY}"/groups/g"${grp_1}"/"${router_grp_1}"/init_no_rules_conf.sh
        {
            echo " -c 'interface ixp_"${grp_2}"' \\"
            echo " -c 'ip address "${subnet1}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_1}"' \\"
            echo " -c 'network "$(subnet_group "${grp_1}")"' \\"
            echo " -c 'neighbor "${subnet2%???}" remote-as "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet2%???}" activate' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map IXP_OUT_${grp_2} out' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map IXP_IN_${grp_2} in' \\"
            echo " -c 'exit' \\"

            str_tmp=''
            for peer in $(echo $ixp_peers | sed "s/,/ /g"); do
                str_tmp=${str_tmp}${grp_2}:${peer}" "
            done

            echo " -c 'bgp community-list 1 permit $grp_1:10' \\"
            echo " -c 'route-map IXP_OUT_${grp_2} permit 10' \\"
            echo " -c 'set community $str_tmp' \\"
            echo " -c 'exit' \\"
            echo " -c 'route-map IXP_OUT_${grp_2} permit 20' \\"
            echo " -c 'set community $str_tmp' \\"
            echo " -c 'exit' \\"
            echo " -c 'route-map IXP_IN_${grp_2} permit 10' \\"
            echo " -c 'set community $grp_1:20' \\"
            echo " -c 'set local-preference 50' \\"

            echo " -c 'exit' \\"
        } >> "${nr_location}"
    else
        subnet="${row_i[8]}"

        if [ "$subnet" != "N/A" ]; then
            subnet1=${subnet%????}1/24
            subnet2=${subnet%????}2/24
        else
            subnet1="$(subnet_router_router_extern "${i}" 1)"
            subnet2="$(subnet_router_router_extern "${i}" 2)"
        fi

        # Full config for 1st side of the link
        location1="${DIRECTORY}"/groups/g"${grp_1}"/"${router_grp_1}"/init_full_conf.sh
        {
            echo " -c 'interface ext_"${grp_2}"_"${router_grp_2}"' \\"
            echo " -c 'ip address "${subnet1}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_1}"' \\"
            echo " -c 'neighbor "${subnet2%???}" remote-as "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map LOCAL_PREF_IN_${grp_2} in' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map LOCAL_PREF_OUT_${grp_2} out' \\"
            echo " -c 'network "$(subnet_group "${grp_1}")"' \\"
            echo " -c 'exit' \\"

            if [ $relation_grp_1 == 'Provider' ]; then
                echo " -c 'bgp community-list 2 permit $grp_1:10' \\"
                echo " -c 'bgp community-list 2 permit $grp_1:20' \\"
                echo " -c 'bgp community-list 2 permit $grp_1:30' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_2} permit 10' \\"
                echo " -c 'set community $grp_1:10' \\"
                echo " -c 'set local-preference 100' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 10' \\"
                echo " -c 'match community 2' \\"
                echo " -c 'exit' \\"
            elif [ $relation_grp_1 == 'Customer' ]; then
                echo " -c 'bgp community-list 1 permit $grp_1:10' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_2} permit 10' \\"
                echo " -c 'set community $grp_1:30' \\"
                echo " -c 'set local-preference 20' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 10' \\"
                echo " -c 'match community 1' \\"
                echo " -c 'exit' \\"
            elif [ $relation_grp_1 == 'Peer' ]; then
                echo " -c 'bgp community-list 1 permit $grp_1:10' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_2} permit 10' \\"
                echo " -c 'set community $grp_1:20' \\"
                echo " -c 'set local-preference 50' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_2} permit 10' \\"
                echo " -c 'match community 1' \\"
                echo " -c 'exit' \\"
            fi
        } >> "${location1}"

        # No rules config for 1st side of the link
        nr_location1="${DIRECTORY}"/groups/g"${grp_1}"/"${router_grp_1}"/init_no_rules_conf.sh
        {   
            echo " -c 'interface ext_"${grp_2}"_"${router_grp_2}"' \\"
            echo " -c 'ip address "${subnet1}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_1}"' \\"
            echo " -c 'neighbor "${subnet2%???}" remote-as "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map empty_in in' \\"
            echo " -c 'neighbor "${subnet2%???}" route-map empty_out out' \\"
            echo " -c 'network "$(subnet_group "${grp_1}")"' \\"
            echo " -c 'exit' \\"
        } >> "${nr_location1}"

        # Full config for 2nd side of the link
        location2="${DIRECTORY}"/groups/g"${grp_2}"/"${router_grp_2}"/init_full_conf.sh
        {
            echo " -c 'interface ext_"${grp_1}"_"${router_grp_1}"' \\"
            echo " -c 'ip address "${subnet2}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet1%???}" remote-as "${grp_1}"' \\"
            echo " -c 'neighbor "${subnet1%???}" route-map LOCAL_PREF_IN_${grp_1} in' \\"
            echo " -c 'neighbor "${subnet1%???}" route-map LOCAL_PREF_OUT_${grp_1} out' \\"
            echo " -c 'network "$(subnet_group "${grp_2}")"' \\"
            echo " -c 'exit' \\"

            if [ $relation_grp_2 == 'Provider' ]; then
                echo " -c 'bgp community-list 2 permit $grp_2:10' \\"
                echo " -c 'bgp community-list 2 permit $grp_2:20' \\"
                echo " -c 'bgp community-list 2 permit $grp_2:30' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_1} permit 10' \\"
                echo " -c 'set community $grp_2:10' \\"
                echo " -c 'set local-preference 100' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 10' \\"
                echo " -c 'match community 2' \\"
                echo " -c 'exit' \\"
            elif [ $relation_grp_2 == 'Customer' ]; then
                echo " -c 'bgp community-list 1 permit $grp_2:10' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_1} permit 10' \\"
                echo " -c 'set community $grp_2:30' \\"
                echo " -c 'set local-preference 20' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 10' \\"
                echo " -c 'match community 1' \\"
                echo " -c 'exit' \\"
            elif [ $relation_grp_2 == 'Peer' ]; then
                echo " -c 'bgp community-list 1 permit $grp_2:10' \\"
                echo " -c 'route-map LOCAL_PREF_IN_${grp_1} permit 10' \\"
                echo " -c 'set community $grp_2:20' \\"
                echo " -c 'set local-preference 50' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 5' \\"
                echo " -c 'match ip address prefix-list OWN_PREFIX' \\"
                echo " -c 'exit' \\"
                echo " -c 'route-map LOCAL_PREF_OUT_${grp_1} permit 10' \\"
                echo " -c 'match community 1' \\"
                echo " -c 'exit' \\"
            fi
        } >> "${location2}"

        # No rules config for 2nd side of the link
        nr_location2="${DIRECTORY}"/groups/g"${grp_2}"/"${router_grp_2}"/init_no_rules_conf.sh
        {
            echo " -c 'interface ext_"${grp_1}"_"${router_grp_1}"' \\"
            echo " -c 'ip address "${subnet2}"' \\"
            echo " -c 'exit' \\"
            echo " -c 'router bgp "${grp_2}"' \\"
            echo " -c 'neighbor "${subnet1%???}" remote-as "${grp_1}"' \\"
            echo " -c 'neighbor "${subnet1%???}" route-map empty_in in' \\"
            echo " -c 'neighbor "${subnet1%???}" route-map empty_out out' \\"
            echo " -c 'network "$(subnet_group "${grp_2}")"' \\"
            echo " -c 'exit' \\"
        } >> "${nr_location2}"
    fi

done

# measurement
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            if [ "${property1}" = "MEASUREMENT"  ];then
                location="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh
                {
                    echo "#!/bin/bash"
                    echo "vtysh  -c 'conf t' \\"
                    echo " -c 'interface measurement_"${group_number}"' \\"
                    echo " -c 'ip address "$(subnet_router_MEASUREMENT "${group_number}" "group")"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router ospf' \\"
                    echo " -c '"network "$(subnet_router_MEASUREMENT "${group_number}" "group")" area 0"' \\"
                    echo " -c 'exit' \\"
                } >> "${location}"
            fi
        done
    fi
done

# exabgp
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            if [ "${property1}" = "BGP_MONITOR" ] || [ "${property1}" = "ARTEMIS" ];then
                location="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh
                {
                    echo "#!/bin/bash"
                    echo "vtysh  -c 'conf t' \\"
                    echo " -c 'interface monitor' \\"
                    echo " -c 'ip address "$(subnet_router_EXABGP_MONITOR "${group_number}" "group")"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router ospf' \\"
                    echo " -c '"network "$(subnet_router_EXABGP_MONITOR "${group_number}" "group")" area 0"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'bgp community-list 1 permit $group_k:10' \\"
                    echo " -c 'route-map LOCAL_PREF_IN_EXA deny 10' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'route-map LOCAL_PREF_OUT_EXA permit 5' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'route-map LOCAL_PREF_OUT_EXA permit 10' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router bgp "${group_number}"' \\"
                    echo " -c 'neighbor "$(subnet_router_EXABGP_MONITOR "${group_number}" "local-address")" remote-as 10000' \\"
                    echo " -c 'neighbor "$(subnet_router_EXABGP_MONITOR "${group_number}" "local-address")" route-map LOCAL_PREF_IN_EXA in' \\"
                    echo " -c 'neighbor "$(subnet_router_EXABGP_MONITOR "${group_number}" "local-address")" route-map LOCAL_PREF_OUT_EXA out' \\"
                    echo " -c 'exit' \\"
                } >> "${location}"
            

            fi

        done
    fi
done


# matrix
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            if [ "${property1}" = "MATRIX"  ];then
                location="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh
                {
                    echo "#!/bin/bash"
                    echo "vtysh  -c 'conf t' \\"
                    echo " -c 'interface matrix_"${group_number}"' \\"
                    echo " -c 'ip address "$(subnet_router_MATRIX "${group_number}" "group")"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router ospf' \\"
                    echo " -c 'network "$(subnet_router_MATRIX "${group_number}" "group")" area 0' \\"
                    echo " -c 'exit' \\"
                } >> "${location}"
            fi
        done
    fi
done


# dns
for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            if [ "${property1}" = "DNS"  ];then
                location="${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh
                {
                    echo "#!/bin/bash"
                    echo "vtysh  -c 'conf t' \\"
                    echo " -c 'interface dns_"${group_number}"' \\"
                    echo " -c 'ip address "$(subnet_router_DNS "${group_number}" "group")"' \\"
                    echo " -c 'exit' \\"
                    echo " -c 'router ospf' \\"
                    echo " -c 'network "$(subnet_router_DNS "${group_number}" "group")" area 0' \\"
                    echo " -c 'exit' \\"
                }  >> "${location}"
            fi
        done
    fi
done

echo 'Sleeping 2 seconds...'
sleep 2

for ((k=0;k<group_numbers;k++)); do
    group_k=(${groups[$k]})
    group_number="${group_k[0]}"
    group_as="${group_k[1]}"
    group_config="${group_k[2]}"
    group_config="${group_k[2]}"
    group_router_config="${group_k[3]}"
    group_internal_links="${group_k[4]}"

    if [ "${group_as}" != "IXP" ];then

        readarray routers < "${DIRECTORY}"/config/$group_router_config
        n_routers=${#routers[@]}

        for ((i=0;i<n_routers;i++)); do
            router_i=(${routers[$i]})
            rname="${router_i[0]}"
            property1="${router_i[1]}"

            #run initial config
            echo " -c 'exit' -c 'write' " >> "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh
            echo " -c 'exit' -c 'write' " >> "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh

            docker cp "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_conf.sh "${group_number}"_"${rname}"router:/home/init_conf.sh
            docker exec -d "${group_number}"_"${rname}"router bash ./home/init_conf.sh &

            if [ "$group_config" == "Config" ]; then
                docker cp "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_full_conf.sh "${group_number}"_"${rname}"router:/home/init_full_conf.sh
                docker exec -d "${group_number}"_"${rname}"router bash ./home/init_full_conf.sh &
            elif [ "$group_config" == "NoRules" ]; then
                docker cp "${DIRECTORY}"/groups/g"${group_number}"/"${rname}"/init_no_rules_conf.sh "${group_number}"_"${rname}"router:/home/init_no_rules_conf.sh
                docker exec -d "${group_number}"_"${rname}"router bash ./home/init_no_rules_conf.sh &
            fi

        done
    else
        echo " -c 'exit' -c 'write' " >> "${DIRECTORY}"/groups/g"${group_number}"/init_full_conf.sh
        docker cp "${DIRECTORY}"/groups/g"${group_number}"/init_full_conf.sh "${group_number}"_IXP:/init_full_conf.sh
        docker exec -d "${group_number}"_IXP bash ./init_full_conf.sh &

        docker exec -d "${group_number}"_IXP bash -c "ifconfig IXP 180.${group_number}.0.${group_number}/24"
    fi
done

wait