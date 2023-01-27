# Save configuration

While doing the project, students may need to save their router and switch configurations (e.g., to submit it at the end of the project).
When building the mini-Internet, a script called `save_configs.sh` is automatically generated and aims at saving all the router and switch configurations into a zip file. There is one `save_configs.sh` script for each group, which is available in the SSH proxy container of the corresponding group (use `./save_configs.sh`).
Students can then download the zip file to their local machine (e.g., using `scp`).

### Restore configuration

A complementary script `restore_configs.sh` is also available and restores a router's configuration (or all routers') from a saved configuration. Reloading a configuration of a switch is not supported at the moment.

### Restarting ospfd

Students may encounter the message _For this router-id change to take effect, save config and restart ospfd_ when configuring a router. The `restart_ospfd.sh` script deletes and reinstalls the OSPF configuration running on a given router. Deleting and reinstalling the OSPF configuration effectively restarts ospfd and will cause the new router-id to take effect.
