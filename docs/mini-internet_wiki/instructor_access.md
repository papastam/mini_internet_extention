# Instructor access

## Docker-based

If you are the instructor and have access to the server hosting the mini-Internet, you can directly access the containers using the various docker commands. First, type  `docker ps` to get a list of all the containers running. The names of the hosts, switches and routers always follow the same convention. For instance, to access a shell on the `ZURI` router in AS1, just use the following command:

```
docker exec -it 1_ZURIrouter bash
```

If you are in the router container, run `vtysh` to access the CLI of that router.

The following example shows you how to access the switch S1 in the L2 network DCN of AS3:

```
sudo docker exec -it 3_L2_DCN_S1 bash
```

Hosts and switches do not have a CLI, so once you are in the container you can directly start to configure them.

## SSH-based

A public key is automatically added into all the SSH containers, and the paired private key is available in `groups/id_rsa`. 
The instructor can thus use this pair of keys to access all the SSH containers with ssh (using the `-i` parameter).