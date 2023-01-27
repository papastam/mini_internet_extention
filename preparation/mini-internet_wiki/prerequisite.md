## Prerequisite

We run our mini-Internet on a server with Ubuntu 20.04 and the linux kernel 5.4.0. 
To build the mini-Internet, you need sudo privileges and must install the following software on the server that hosts the mini-Internet.

:information_source:  We allocate two cores to the docker containers, thus the server hosting the mini-Internet needs at least two cores.
If you want to try it out with one core, you will have to update the [`container_setup.sh`](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/setup/container_setup.sh) script and allocate one core only to every docker container.

#### Install the Docker Engine

To run all the different components in the mini-Internet (hosts, switches, routers, ...) we use Docker containers.

Follow this [installation guide](https://docs.docker.com/install/linux/docker-ce/ubuntu/) to install docker.
In the directory `docker_images` you can find all the Dockerfile and docker-start files used to build the containers.
In case you want to add some functionality into some of the docker containers, you can
update these files and build you own docker images:

```
docker build --tag=your_tag your_dir/
```

Then, you have to manually update the scripts in the `setup` directory and run
your custom docker images instead of the ones we provide by default.

#### Install Open vSwitch

We use the Open vSwitch framework in two ways: (i) to build the L2 component of the mini-Internet and (ii) to connect Docker containers together.

```
sudo apt-get install openvswitch-switch
```

For further information, see the [installation guide](http://docs.openvswitch.org/en/latest/intro/install/).

#### Install OpenVPN

Finally, we also need Open VPN which allows the students to connect their own devices to the mini-Internet.

```
sudo apt-get install openvpn
```

#### Install OpenSSL

You must have OpenSSL installed with `SECLEVEL`<=2. It should be the case by default.

#### Miscellaneous

- To prevent accidental shutdowns/reboots, you can also install the [`molly-guard`](https://packages.ubuntu.com/impish/molly-guard) package.

- Some servers may list all the existing interfaces in the greeting message using the following script: `etc/update-motd.d/50-landscape-sysinfo`. Because the mini-internet creates a lot of virtual interfaces, generating this greeting message thus takes time, preventing promptly sshing into the server. We thus recommend preventing this script from generating its output at login using `sudo chmod -x /etc/update-motd.d/50-landscape-sysinfo`.