# Active probing

To run measurements between any two ASes, we must use a dedicated container called `MEASUREMENT`.
After activating [port forwarding](port_forwarding), you can access the measurement container over port 2099:

```
ssh -p 2099 root@<your_server_domain>
```

You can find the password in the file `groups/ssh_measurement.txt`.
It should be distributed to all students such that they can access the `MEASUREMENT` container.
In the `MEASUREMENT` container, we provide a script called `launch_traceroute.sh` that relies on `nping` and that can be used to launch traceroutes between any pair of ASes. For example if you want to run a `traceroute` from AS1 to AS2, simply run the following command:

```
root@ba1ccfaf2f55:~# ./launch_traceroute.sh 1 2.108.0.1
Hop 1:  1.0.199.1 TTL=0 during transit
Hop 2:  179.0.0.2 TTL=0 during transit
Hop 3:  2.0.1.2 TTL=0 during transit
Hop 4:  2.0.6.2 TTL=0 during transit
Hop 5:  2.108.0.1 Echo reply (type=0/code=0)
```

where 2.108.0.1 is an IP address of a host in AS2. You can see the path used by the packets to reach the destination IP.

By default, the `MEASUREMENT` container is connected to the router `MILA` in every transit AS (see the [`l3_routers.txt`](layer3_configuration#l3_routerstxt) configuration file). If for one AS none of the routers is connected to the `MEASUREMENT` container, you cannot run a traceroute from that AS via the `MEASUREMENT` container. Using the default configuration files this is the case for the the Tier1 and Stub ASes. In other words, by default the `MEASUREMENT` container can only launch traceroutes from student ASes.
