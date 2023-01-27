# Delete the mini-Internet

The are two ways to delete the mini-Internet. First, you can delete all the virtual ethernet pairs, docker containers, OVS switches and OpenVPN processes used in the mini-Internet (as well as the created `groups` folder) with the following command:

```
sudo ./cleanup/cleanup.sh .
```

However, this script uses the configuration files as basis, thus if they have changed since the time the mini-Internet was built, or if the mini-Internet did not set up properly, some parts might not be deleted. That could be problematic if you try to start a new mini-Internet afterwards. We thus also provide a script that simply deletes **all** the ethernet pairs, containers, switches and OpenVPN processes.

:warning: :warning: :warning: This also includes containers, switches and ethernet pairs which do _not_ belong to the mini-Internet (e.g., your very important Docker container running experiments)!

```
sudo ./cleanup/hard_reset.sh
```
