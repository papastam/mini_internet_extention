# Enable RPKI

The mini-Internet can run an RPKI infrastructure so that routers can perform route origin validation. 
While in the actual Internet RPKI uses several root Certificate Authorities (CA) and relies on a hierarchy of CAs with multiple layers (e.g., using delegated RPKI), our mini-Internet uses a rather simple RPKI setup: there is only one root CA and then each AS has its own CA that is a child of the root CA. The CA of an AS runs in a host located in its AS. One AS hosts the root CA. 
To implement RPKI in the mini-Internet, we use [Krill](https://www.nlnetlabs.nl/projects/rpki/krill/) and its test environment, which means that there is a single publication server that runs in the host responsible for the CA.

We now explain how to activate RPKI in the mini-Internet.

## Turn on the RPKI option in FRR

In the [daemons](https://github.com/nsg-ethz/mini_internet_project/blob/master/platform/config/daemons) configuration file used by FRR instances, we need to activate RPKI by adding the `-M rpki` option:
```
bgpd_options="   -A 127.0.0.1 -M rpki"
```
Note that this is the default configuration.

## Activating the Certificate Authority

To activate the CA, we need configure one host within the mini-Internet to be the Krill host.
To do that configure it in the `l3_routers.txt` file by setting the value in C3 before the colon to `krill`.
For instance, in the default configuration that we provide, the host connected to the router `ZURI` in AS1 hosts krill.

:exclamation: For now, the implementation allows only one CA within the mini-Internet. We ensure this by using different `l3_routers.txt`, 
one for AS1 that includes the CA, and other ones without the CA for the other ASes.

The CA comes preconfigured, there is nothing else do that but updating the `l3_routers.txt` configuration file. The publication server will also be automatically created.

## Activating the Validator

RPKI Validators are needed to fetch Route Origin Authorizations (ROAs) from the publication server and verify their signatures.
As the CA, the validators can run in the hosts of the mini-Internet. This is configurable in the `l3_routers.txt` configuration file, 
using the keyword `routinator` for the value in C3 before the colon. 

In the default configuration files, there is one validator in each AS. In the transit ASes, they run in the hosts connected to `LUGA`.
As for the CA, everything comes preconfigured: the validator listens on port 3323 for new connections with the routers.

:point_right: We use [routinator](https://github.com/NLnetLabs/routinator) for the validator, yet there exists several other validators such as [OpenBSD rpki-client](https://www.rpki-client.org/).

## Default ROAs

You can configure default ROAs in the `config/roas/` directory (which first needs to be created). For every AS for which you want to create default ROAs, create the file `gX.txt` in this folder, with X the corresponding AS number. For instance the file for group group 2 (`g2.txt`) could look like this:

```
# This file describes the ROAs that should be issued or removed by the group's CA on startup

R: 2.0.0.0/8 => 2
A: 2.0.0.0/8 => 3
```

The first line starting with `R` means that a ROA for `2.0.0.0/8` and AS2 is automatically removed at startup. The second line starting with `A` means that a ROA for `2.0.0.0/8` and AS3 is automatically created at startup.
