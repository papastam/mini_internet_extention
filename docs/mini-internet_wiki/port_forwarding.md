# Port forwarding

To configure their devices, students first access a proxy container. There is one proxy container for every AS,
and from a proxy container students can only access the devices that are within their AS.

The access to the proxy container (from the real Internet) is made possible by installing SSH tunnels
that forward SSH connections to the corresponding proxy container based on the port number used.
We now explain how to setup the port forwarding.

First of all, make sure the following options are set to true in `/etc/sshd_config` on your host server:

```
GatewayPorts yes
PasswordAuthentication yes
AllowTcpForwarding yes
```

Then restart the ssh service: 

```
sudo service ssh restart
```

Finally, you must use the script [portforwarding.sh](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/utils/ssh/portforwarding.sh) that configures all the SSH tunnels automatically
based on the configuration files. It also opens the corresponding ports using `ufw`.
You can run this script with the following command from the `platform` directory:

```
sudo ./utils/ssh/portforwarding.sh
```

In case you want to delete the SSH forwarding rules that were created, you can use the following command:

```
for pid in $(ps aux | grep ssh | grep StrictHostKeyChecking | tr -s ' ' | cut -f 2 -d ' '); do sudo kill -9 $pid; done
```

:warning: This command might also delete SSH tunnels that are unrelated to the mini-Internet.
