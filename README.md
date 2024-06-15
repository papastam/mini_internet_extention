# Mini-internet extension

## The mini-internet platform

The [mini-internet](mini-inter.net) platform is a teaching platform (made at ETHZ) that virtualizes a network of ASes. For teaching purposes, each AS is assigned to teams of 2–3 students and provides them with a set of routers and switches to configure and connect to each other. The goal is to learn about the basics of networking and routing protocols.

This platform is being used in the HY335B course at the Computer Science Department of the University of Crete as the main course's project.

## Theis Overview

This github repository contains my bachelor thesis project at CSD, UOC. Through this project, I extended the [mini-internet](mini-inter.net) platform with a couple of new features. The implemented features are grouped into the following two parts:

- **Web-Server new features**: Coming out of the box, the platform contains a web-server that is mainly used by the students as an informative and debugging tool.
- **BGP Hijacks Simulation**: The main feature of this project is the simulation of BGP hijacks. This feature is used to simulate a BGP hijack attack and to study the effects of such an attack on a network. With the implementation of a lightweight version of ARTEMIS Detector, these hijacks can be detected and mitigated.

__All new features are showcased extensively in the [Thesis Report PDF](Thesis/Thesis_Report.pdf).__

## Pre-requisites

In order to run the platform on your system, you need to have the following software installed:

- [Docker](https://docs.docker.com/get-docker/)
- [OpenVSwitch](https://www.openvswitch.org/)

## Configuring the platform

Before running the platform, you need to configure it. The configuration is done by editing the configuration files located under the [`platform/config`](/platform/config) directory. Details about the configuration can be found in the [mini-internet documentation](https://github.com/nsg-ethz/mini_internet_project/wiki).

In the [configuration folder](/platform/config) you can find the following example configuration files:

- [1_AS_topo](/platform/config/1_AS_topo): A simple configuration files that creates a network with a single AS containing 2 connected routers.
- [hy335b](/platform/config/hy335b): The configuration files used for the HY335B project. It creates a network with 78 ASes, each one of which contains 8 routers.
- [hy436_ass4](/platform/config/hy335b_ass4): The configuration files used for the 4th assignment of the HY436 course. It creates a network with 32 ASes and 4 routers each. _More information about this topology can be found in the [Thesis Report](Thesis/Thesis_Report.pdf)_.
- [hy436_ass4_mini2](/platform/config/hy335b_ass4_mini2): A smaller version of the hy436_ass4 topology. It creates a network with 4 ASes and 4 routers each. This topology is used for demonstration purposes _More information about this topology can be found in the [Thesis Report](Thesis/Thesis_Report.pdf)_.

In order to use any of the above configurations, you need to copy the configuration files to the [`platform/config`](/platform/config) directory.

## Running the platform

Using the script located in the platform's directory, you can easily run the platform. The script is called [`startup.sh`](/platform/startup.sh). The script needs to be executed with root privileges.

## Accessing the platform

### Topology devices

Accessing the devices of the topology can be done in one of the following ways:

- **SSH to the proxy container**: The proxy container is used to access all the devices of an AS. You can access the proxy container by running the following command: `ssh -p <2000+AS#> <Server IP>`. In order for the ssh connection to work, you need to first forward the ports using the [port forwarding script](/platform/utils/ssh/portforwarding.sh). The port forwarding script needs to be executed with root privileges.

- **Docker exec**: You can also access the devices of the topology by using the `docker exec` command. For example, to access the CLI of the router with name _R1_ of a certain AS, you need to execute the following command: `docker exec -it <AS#>_<R1>router vtysh`. Accessing a host of router _R1_ is done in a similar way: `docker exec -it <AS#>_<R1>host bash`.

The platform's web-server can be accessed by visiting the following URL: `http://<Server IP>:8000`.