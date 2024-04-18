#!/bin/bash
#
# remove all container, bridges and temporary files
# will only remove the containers, bridges defined in ../config/

set -o errexit
set -o pipefail
set -o nounset

if [ "$#" != 1 ]; then
  echo "Invalid Syntax" 2>&1
  echo "Use: ${0##*/} <directory>" 2>&1
  exit 1
fi

DIRECTORY="$1"
echo -n "ovs-vsctl " > ovs_command.txt

# kill all container
./cleanup/container_cleanup.sh "${DIRECTORY}"

# remove all container & restart docker
docker system prune -f

./cleanup/host_links_cleanup.sh "${DIRECTORY}"
./cleanup/layer2_cleanup.sh "${DIRECTORY}"
./cleanup/internal_links_cleanup.sh "${DIRECTORY}"
./cleanup/external_links_cleanup.sh "${DIRECTORY}"
./cleanup/measurement_cleanup.sh "${DIRECTORY}"
./cleanup/monitor_cleanup.sh "${DIRECTORY}"
./cleanup/matrix_cleanup.sh "${DIRECTORY}"
./cleanup/dns_cleanup.sh "${DIRECTORY}"
./cleanup/ssh_cleanup.sh "${DIRECTORY}"
./cleanup/vpn_cleanup.sh "${DIRECTORY}"

# Stop the pipe listener
ps -ef | grep "pipe_listener.sh" | grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null || true 
ps -ef | grep "docker_pipe" | grep -v grep | awk '{print $2}' | xargs kill -9 &> /dev/null || true

# remove the pipe log
sudo rm -f "${DIRECTORY}"/nohup.out

bash  < ovs_command.txt || true
rm -f ovs_command.txt

# delete old running config files
if [ -e groups ]; then
  rm -rf groups
fi