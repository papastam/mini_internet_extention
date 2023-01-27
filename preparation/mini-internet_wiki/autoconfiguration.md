# Autoconfiguration

During the project, it may happen that you need to configure an AS that was not preconfigured by default (i.e., while starting the mini-Internet).
For instance, it is usually advisable to have a few more student ASes ready than what is actually needed, e.g., in case more students join the project after it starts. 
However, in case they are really not used, you will need to configure these ASes to enable network-wide connectivity.
We thus provide a script that autoconfigures the layer 3 part of a given AS. 

The script is available in the `utils/autoconfiguration/configure_as.sh` directory.
Before running it, you simply need to update the following three variables:
`PLATFORM_DIR`, `ASN_TO_CONFIGURE`, and `ROUTER_NAMES`. Further information about these variables is available in the script.