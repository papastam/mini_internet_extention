# Student access with VPN

Finally, you can also access the mini-Internet through a VPN. In the file [`config/l2_hosts.txt`](layer2_configuration#l2_hoststxt), the lines starting with `vpn` correspond to a L2-VPN server which will be automatically installed instead of a normal host. A L2-VPN is connected to a L2 switch (the one written in C4 of the configuration file), and every user connected to this L2-VPN will be virtually connected to that L2 switch.

To use the VPN, a student must first install OpenVPN and run it with the following command (on Ubuntu 18 and 20):

```
sudo openvpn --config client.conf
```

We provide the `client.conf` file below, where `VPN_IP` must be replaced by the IP address of the server hosting the mini-Internet. `VPN_PORT` defines to which VPN server we want to connect to. You can find the port of the VPN servers by looking at their configuration file, which is located here: `groups/gX/vpn/vpn_Y/server.conf` with `X` the group number and `Y` the VPN ID for that group.

```
client
remote VPN_IP VPN_PORT
dev tap
proto udp
resolv-retry infinite
nobind
persist-key
persist-tun
ca ca.crt
cipher AES-256-CBC
verb 3
auth-user-pass
```

The `file ca.crt` is automatically generated during the mini-Internet setup. It is available in the directory `groups/gX/vpn/vpn_Y` and must be given to the student. Finally, the username is `groupX` (X is the group number) and the password is the same than the one used to access the proxy container through SSH.

When connected, the student should see an interface called `tap0` with a corresponding IP address. This interface is directly connected to the mini-Internet.

:exclamation: VPN access from other operating systems than Linux/Ubuntu (such as Windows) might also be possible but was not tested by us.
