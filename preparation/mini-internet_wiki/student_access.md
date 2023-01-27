# Student access

Student access ensures isolation: a student can only access the virtual devices that are in their AS and not the others.
We use one SSH proxy container for every AS to ensure isolation.
More precisely, students must first access the proxy container from where they can directly go to any device (router, host, ...) belonging to their AS.
The SSH proxy container is accessible via SSH, using port forwarding (see [port_forwarding](port_forwarding) to enable the port forwarding).

Once the port forwarding is configured, students can connect to their ssh proxy container using the following command:

```
ssh -p [2000+X] root@<your_server_domain>
```

with X their corresponding AS number. The passwords of the groups are automatically generated with the openssl's rand function and are available in the file `groups/ssh_passwords.txt` (distribute the passwords to the corresponding students at the beginning of the project/lecture).

Once in a proxy container, a student can use the `goto.sh` script to access a host, switch or router. For instance to jump into the host connected to the router `MIAM`, use the following command:

```
./goto.sh MIAM host
```

If you want to access the router `ZURI`, write:

```
./goto.sh ZURI router
```

And if you want to access the switch `S1` in the L2 network `DCN`, use the following command:

```
./goto.sh DCN S1
```

> The `goto.sh` script supports autocompletion.

Once in a host, switch or router, just type `exit` to go back to the proxy container.

:exclamation: Important to note, as some of our students are not too familiar with SSH, we give each student group a password to access their proxy container. However, it would also be possible to add the student's public keys to the corresponding proxy containers in order to achieve a key-based SSH authentication.