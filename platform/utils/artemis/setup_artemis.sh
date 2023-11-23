# if [ "${property1}" = "ARTEMIS"  ];then

#     # start ARTEMIS container
#     docker run -itd --net='none' --name="${group_k}_ARTEMIS"  \
#         -v ${GROUPSDIR}/configs/${group_k}_exabgp.conf:/exabgp.conf \
#         -v ${GROUPSDIR}/logs/${group_k}_parser.log:/parser/parser.log \
#         -v ${GROUPSDIR}/output/${group_k}_output.csv:/parser/output.csv \
#         -v ${GROUPSDIR}/output/as_prefixes.csv:/parser/as_prefixes.csv \
#         -v ${UTILSDIR}/pipe/docker_pipe:/pipe \
#         -e "ASN=${group_number}" \
#         -e "ARTEMIS_INTERVAL=30" \
#         --hostname="${group_k}_ARTEMIS" --cpus=2 --pids-limit 100 \
#         papastam/mi-artemis

#     # cache the docker pid for ovs-docker.sh
#     source ${DIRECTORY}/groups/docker_pid.map
#     DOCKER_TO_PID["${group_k}_ARTEMIS"]=$(docker inspect -f '{{.State.Pid}}' ${group_k}_ARTEMIS)
#     declare -p DOCKER_TO_PID > ${DIRECTORY}/groups/docker_pid.map

#     passwd="$(openssl rand -hex 8)"
#     echo "${passwd}" >> "${DIRECTORY}"/groups/ssh_artemis.txt
#     echo -e ""${passwd}"\n"${passwd}"" | docker exec -i ${group_k}_ARTEMIS passwd root

#     echo "Created ARTEMIS container for group ${group_number}"
# fi