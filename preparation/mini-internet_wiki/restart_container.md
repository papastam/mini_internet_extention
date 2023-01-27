# Restart a container

It can happen that a container crashes while the mini-Internet is running. It is quite a hassle to restart a container and manually connect it to the other containers according to the topology. Therefore, the mini-Internet automatically generates the script `restart_container.sh` during startup. This script enables to reconnect a container to the other containers automatically.

For instance if the container `CONTAINER_NAME` has crashed or has a problem, just run the following commands:

```
docker kill CONTAINER_NAME
docker start CONTAINER_NAME
./groups/restart_container.sh CONTAINER_NAME     # needs sudo!
```

:information_source: This script can take few minutes.

:information_source: Sometimes the MAC addresses on some interfaces must follow a particular scheme (for instance the ones connected to the `MATRIX` container). Configuring these MAC addresses must be done manually.

## Restarting the SSH proxy container

It can happen that an SSH container fails if a student starts more than 100 parallel processes in it. We configured this number to limit the overall load on the server. When this problem occurs, you can no longer access the docker container, and you need to restart it following the procedure depicted above.
Besides restarting the docker container, you also need to re-enable the SSH port forwarding for that particular SSH proxy container. You can do that from the host server with the following command:

```
ssh -i groups/id_rsa -o UserKnownHostsFile=/dev/null -o "StrictHostKeyChecking no" -f -N -L 0.0.0.0:[2000+X]:157.0.0.[X+10]:22 root@157.0.0.[X+10]
```

where `X` is the group number.
