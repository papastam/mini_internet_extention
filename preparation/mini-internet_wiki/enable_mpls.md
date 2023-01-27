# Enable MPLS

Following we explain the parameters to modify so that the routers support MPLS within the mini-Internet.

## Turn on LDP on the FRR routers

You must turn on the LDP daemon in the FRR routers by replacing
`ldpd=no` with `ldpd=yes` in the [daemons](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/config/daemons) configuration file. By default, the option is disabled.

## Give full privilege to the containers running a router

To enable MPLS on the interfaces of the routers, the containers hosting the routers must start with the `--privileged` option.
You need to update the `setup/container_setup.sh` script to do that. 

:warning: Whenever possible you should avoid using `--privileged` and give access to the router containers using bash (with the `linux` option in the `l3_routers.txt` configuration file) to prevent security issues.
