# Enable Multicast

We now explain how to enable Multicast within the mini-Internet.

## Turn on PIM on the FRR routers

You must replace `pimd=no` with `pimd=yes` in the [daemons](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/config/daemons) configuration file to turn on the PIM protocol for the FRR routers.

## Use a host image that provides Multicast tools

The docker containers used for the hosts within the mini-Internet must come with basic Multicast tools
that are required to test it. The `hostm` docker image includes multicast tools such as `smcroute` or `mtools` and can be used instead of the `host` image.
The vlc docker image comes with `vlc`, which is useful to stream a multicast video. Feel free to use your own image if you prefer.  
