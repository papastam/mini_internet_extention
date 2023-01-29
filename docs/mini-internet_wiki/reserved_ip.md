# Reserved IPs

The mini-Internet allocates a `/8` prefix for every AS using the following scheme: AS X receives prefix `X.0.0.0/8`.
However, aside from the ASes' prefixes, the mini-Internet also uses other prefixes for various purposes.
Below we list all the subnets that are used within the mini-Internet (except the ones allocated to every AS). This helps to avoid conflicts such as 
allocating a prefix to a group while it is already used elsewhere in the mini-Internet.

* **179.0.0.0/8:** reserved for the eBGP sessions between normal ASes.
* **180.0.0.0/8:** reserved for the eBGP sessions with IXPs.
* **198.0.0.0/8:** reserved for the links to the DNS server.
* **157.0.0.0/8:** reserved for the links between the server and the SSH containers.
* **158.0.0.0/8:** reserved for the links between the SSH containers and the other containers.

With the default parameters, you should thus not have AS179, AS180, AS198, AS157 or AS158 in the topology.
Aside from that, do not use AS99 as port 99 is used for [active probing](active_probing).


## Modifying the reserved prefixes

The scheme used to allocate the prefixes within the mini-Internet comes from the [subnet_config.sh](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/config/subnet_config.sh) script.
You can edit this script to change how the prefixes are allocated within the mini-Internet.

:warning: Note that this has not yet been fully tested and some features might no longer work if you change the prefix allocation scheme. 
