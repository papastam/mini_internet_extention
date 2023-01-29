# The mini-Internet website

The mini-Internet automatically creates a webserver that runs in a dedicated container called `WEB` and 
in which several monitoring tools are available.

> To access the `WEB` container from outside, we use a `PROXY` container.

Once the mini-Internet has started, you can access the webserver with the following URL: `https://your-server-domain`.
We now explain how to configure the mini-Internet webserver.

## Configure the website

The configuration must be done in the `setup/website_setup.sh` script.
You must fill in the hostname and give an email to enable HTTPS. This information is then used to automatically obtain a certificate using LetsEncrypt (done by the `PROXY` container). In case HTTP is enough your you, just keep these variables empty.

You can also configure the ports used by the webserver setup or just use the default ones.
By default, port `80` is used for HTTP, `443` is used for HTTPS and `3000` is used to access the krill webserver.
Note that the `krill` tab of the mini-Internet website is just a redirection to the krill webserver on port `3000`.

Finally, you can configure your timezone.

## Webserver log

You can see the log of the webserver simply with the following command:

```
docker logs WEB
```

## Port filtering to prevent DDoS

Since the webserver is running in the server hosting the mini-Internet, we must avoid potential DDoS attacks on the server.
We provide the script `utils/iptables/filters.sh` that applies basic port filtering rules to mitigate some of these potential threats.
