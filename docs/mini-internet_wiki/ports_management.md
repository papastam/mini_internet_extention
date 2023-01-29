# Ports management

In this section we list all the ports that the mini-Internet uses for various purposes.

More generally, we recommend to use a firewall such as `ufw` and close all ports but the one 
used by SSH and the ones used for the mini-Internet.

Here is short summary of what you have to do.

Open the following ports:
```
2000+: for the SSH port forwarding towards the student ASes.
2099: for the MEASUREMENT container.
10000+: for the VPN servers.
443: for the web server access with HTTPS.
80: for the web server access with HTTP.
3000: for the krill webserver (RPKI).
```

Close the following ports:
```
3080: used to access the krill webserver locally with HTTP.
8080: used to access the main webserver locally with HTTP.
all the other unnecessary ports.
```

## Ports for SSH access

Students access their devices from a proxy container that is accessible via SSH.
SSH port forwarding must be used within the server hosting the mini-Internet
to tunnel ssh connections for a particular port to 
the proxy container of one particular group. A port number is thus 
assigned to every group.

By default, we adopt the following scheme for the mapping port to group number: `2000+group_number`.
These ports must be open. The script [portforwarding.sh](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/utils/ssh/portforwarding.sh), which is used to [make the SSH tunnels](port_forwarding)
automatically opens these ports using `ufw`.

## Ports for VPN access

Students can also access the mini-Internet using VPN servers that are running within the mini-Internet.
To do that, one port per VPN server must be opened.

You can find the ports of the VPN servers by looking at their configuration files, which are 
available in the `groups` directory (after the mini-Internet is running). For instance, for group X and the VPN server Y, the port
is indicated in the file `groups/gX/vpn/vpn_Y/server.conf`. 
Basically, the scheme that we follow to allocate the ports for the VPN servers is the following:
We start at port 10000 and iterate over all the groups and VPN servers. In every iteration we increment the port number by one.

## Ports for the Website

When the mini-Internet starts, it runs two webservers: the main one and one for krill.
However, we use a proxy container to access these two servers from outside.
The proxy listens on ports `443` and `80` for HTTPS and HTTP connections respectively, that it then forwards to the main webserver using port `8080` and HTTP.
The proxy also listens on port `3000` for HTTPS connections that it then forwards to the krill webserver using port `3080` and HTTP.
