# DNS

The `DNS` container, connected to every AS and only accessibly by the instructors, runs a bind9 DNS server. In the [`l3_routers.txt`](layer3_configuration#l3_routerstxt) configuration file, we can see that the DNS container is connected to every `ZURI` router. The DNS server has the IP address `198.0.0.100/24` and as soon as the students have configured intra-domain routing and have advertised this subnet into OSPF, they should be able to reach the DNS server and use it.

For instance, a `traceroute` from LYON-host to VIEN-host returns the following output:

```
root@LYON_host /> traceroute 50.107.0.1
traceroute to 50.107.0.1 (50.107.0.1), 30 hops max, 46 byte packets
 1  LYON-host.group50 (50.106.0.2)  0.941 ms  0.008 ms  0.004 ms
 2  BASE-LYON.group50 (50.0.8.1)  0.324 ms  GENE-LYON.group50 (50.0.10.1)  0.301 ms  0.599 ms
 3  LUGA-GENE.group50 (50.0.9.2)  0.376 ms  ZURI-BASE.group50 (50.0.1.1)  0.699 ms  LUGA-GENE.group50 (50.0.9.2)  0.324 ms
 4  VIEN-ZURI.group50 (50.0.5.2)  0.611 ms  VIEN-LUGA.group50 (50.0.12.2)  0.602 ms  0.595 ms
 5  host-VIEN.group50 (50.107.0.1)  0.873 ms  0.721 ms  0.596 ms
```

The naming convention is quite straightforward: XXXX-YYYY.groupZ: where XXXX is the router or host which (should) have the shown IP configured on one of its interfaces; YYYY is the name of the router on the other end of the link connected to this interface (or "host" if it is a host); finally Z is the AS number. The IP addresses used on the links connecting two ASes (e.g., `179.x.x.x`) are not translated.
