DIRECTORY=$1
exa_exists=$(docker ps -a | grep EXABGP | wc -l)

if [[ "$exa_exists" -eq 0 ]]; then
    echo "No EXABGP_MONITOR container found, skipping exabgp_setup.sh"
    exit 0
fi
nohup docker exec -i EXABGP_MONITOR exabgp exabgp.conf > "${DIRECTORY}"/docker_images/exabgp_monitor/exabgp_monitor.log 2>&1 &
echo "exabgp ran successfully"
echo "${DIRECTORY}"/docker_images/exabgp_monitor/exabgp_monitor.log