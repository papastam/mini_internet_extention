# General configuration

We use several configuration files to configure the mini-Internet and define its topology at the different layers.
The configuration files must be in the [config](https://github.com/nsg-ethz/mini_internet_project/tree/master/platform/config) directory.
They are organized in the following way:

```
config/
├── aslevel_links.txt            [inter-AS links and policies] 
├── aslevel_links_students.txt   [inter-AS links for students] 
└── AS_config.txt                [per-AS topology & config]
    ├── l3_router.txt            [L3 internal topology]
    ├── l3_links.txt             [L3 internal topology]
    ├── l2_switches.txt           ^
    ├── l2_hosts.txt              |   [L2 topology]
    └── l2_links.txt              v   
```

You must keep the filenames written above, except for the layer-3 configuration files, for which you can use different filenames because they are referred in the `AS_config.txt` file.

## [`AS_config.txt`](https://github.com/nsg-ethz/mini_internet_project/tree/master/platform/config/AS_config.txt)

The `AS_config.txt` is the main configuration file.
It lists all the ASes and IXPs in the mini-Internet as well as the configuration files to use for every AS.
The following table shows an example of this configuration file. 
```
C1     C2    C3         C4                              C5                            C6                C7             C8
-------------------------------------------------------------------------------------------------------------------------------------
1      AS    Config     l3_routers_krill.txt            l3_links_krill.txt            empty.txt         empty.txt      empty.txt
2      AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
11     AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
12     AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
5      AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
6      AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
15     AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
16     AS    Config     l3_routers_tier1_and_stub.txt   l3_links_tier1_and_stub.txt   empty.txt         empty.txt      empty.txt
3      AS    Config     l3_routers.txt                  l3_links.txt                  l2_switches.txt   l2_hosts.txt   l2_links.txt
4      AS    Config     l3_routers.txt                  l3_links.txt                  l2_switches.txt   l2_hosts.txt   l2_links.txt
13     AS    NoConfig   l3_routers.txt                  l3_links.txt                  l2_switches.txt   l2_hosts.txt   l2_links.txt
14     AS    NoConfig   l3_routers.txt                  l3_links.txt                  l2_switches.txt   l2_hosts.txt   l2_links.txt
81     IXP   Config     N/A                             N/A                           N/A               N/A            N/A
82     IXP   Config     N/A                             N/A                           N/A               N/A            N/A
80     IXP   Config     N/A                             N/A                           N/A               N/A            N/A

```

Below you find the description for each column:
* **C1:** AS number.
* **C2:** Type of the network (either AS or IXP).
* **C3:** `Config` means the AS will be automatically configured (VLANs, OSPF, BGP, ...) whereas `NoConfig` means the AS is started without configuration (i.e., important for student ASes). Note: an IXP must be configured by default.
* **C4:** Name of the configuration file that lists the layer 3 routers within the AS and their parameters.
* **C5:** Name of the configuration file that describes the layer 3 internal topology.
* **C6:** Name of the configuration file that lists the layer 2 switches and their parameters.
* **C7:** Name of the configuration file that lists the hosts within the layer 2 network with their parameters.
* **C8:** Name of the configuration file that describes the layer 2 topology

In this example, the platform will build a mini-Internet comprising 12 ASes and 3 IXPs. Every AS comes preconfigured but AS 13 and 14.

:information_source: At ETH Zürich, we use different topologies for the Tier1/Stub ASes (which are operated by the TA team) and the transit ASes (which are operated by the students) to limit the amount of resources used on our server. This is why we use different configuration files for these two types of ASes. By default, we also set krill (the Certificate Authority used for [RPKI](enable_rpki)) in AS1.

:warning: You can only configure the layer-2 networks in the configuration files `l2_switches.txt`, `l2_hosts.txt` and `l2_links.txt` (and only in those files). On the contrary, for the layer 3 networks, you can use different configuration files to define different layer-3 networks (like we do above).
