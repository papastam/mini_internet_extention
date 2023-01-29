# Build the mini-Internet

To build the mini-Internet, first clone the mini-Internet repository to your server, and go to the `platform` directory.

```
git clone git@github.com:nsg-ethz/mini_internet_project.git
cd mini_internet_project/platform/
```

After editing the configuration files, run the startup script:

```
sudo ./startup.sh
```

By default, this will run a mini-Internet with 12ASes (default configuration files).
When building the mini-Internet, a directory called `groups` is created and all the configuration files, passwords, automatically-generated scripts, etc will be stored in this directory.

:warning: Make sure your server has enough resources to sustain the configured mini-Internet (around 16GB of memory and at least 4 CPU cores are recommended for the default setup). Otherwise, you can configure a smaller mini-Internet using the previously introduced configuration files.

:information_source: You may need to increase the number of INotify instances that can be created per real user ID with the command 

```
fs.inotify.max_user_instances = 1024
```

#### Default configuration

Using the default configuration, most of the hosts, routers and switches will come preconfigured and there 
will be nearly full connectivity. We explain how to change the default configuration (the topology and the various parameters) in the _Configure the mini-Internet_ section.
