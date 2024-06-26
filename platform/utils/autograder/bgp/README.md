# BGP checker

The tools in this directory are used to disconnect an entire AS from
the mini-internet and reconnect it to a special test container.  This
special test container (bgptest) then establishes BGP sessions with
the various border routes of the AS and these sessions can be used to
send arbitrary announcements.  In addition it is possible to send UDP
packets, pings and doing traceroutes.  After the tests, the results
are saved and the AS is connected back into the mini-internet.

The primary target are tier 2 ASes, but other ASes may work as well.

## General note

Some of the actions performed require super user privileges.  For
that reason some scripts and the runner require a username argument to
drop privileges when applicable.

## Setup

### Test container

First build the test container like this:

```
$ cd ../docker_images/bgptest/
$ sudo docker image build --tag my_bgp .
```

### Databases

Run `python3 make_db.py path/to/config/directory`.  `config.db` contains
information about the mini-internet topology parsed from the various config
files.  `config.db` needs to be regenerated if the mini-internet configuration
changes.

Now we need to generate `ovs.db`, `links.db` and `bgp.db`.  They get their
information specific the currently running mini-internet and have to be
regenerated every time the mini-internet is restarted. They can be generated
either by running `make dbs` which uses the `USER` environment variable to drop
privileges, or by executing the commands below:

Collect information about network namespaces and ovs setup (replace `user` with
your username):
```
 $ sudo bash getlinks.sh user
 $ sudo bash parse_ovs.sh user
```
This results in the `links.db` and `ovs.db` databases.

These two files are then combined into `bgp.db` using `make_db_useful.py` (if
`bgp.db` already exists remove it first):
```
 $ python3 make_db_useful.py
```

## Configuration
The actions to execute inside the container are generated by `gentest.py`.
Inside the container `test_as.py` executes those tests.  The output of
`gentest.py` is a database, which next to the tests also contains setup
information.  This database is then filled inside the bgptest container with
the test results and copied out again.

## Running
To run the tests, compile `runner.go` using the `Makefile` (or by hand):
```
 $ make
```
Execute the runner with:
```
 $ sudo ./runner user n aslist
```
`user` has to be again replaced by your username.  `n` is the number of bgptest
containers to use in parallel.  `aslist` is a comma separated list of integers,
specifying the AS numbers to test.

Various scripts exists to generate a comma separated list of ASes
to use as an argument to the runner:

 - `tier2.sh`: Outputs all tier 2 ASes
 - `region.sh`: Outputs all tier 2 ASes in a region

To see the specific commands executed by the runner, check the source
file `runner.go`.  The bgptest container setup and teardown are in the
launch function, the AS connect/disconnect and test running is in the
`runTests` function.  Below are also some short instruction how to
manually execute these steps.

## Results
The results are in databases named after the following scheme:
`results_runnerId_ASnumber.db`.  `runnerId` depends on the id of bgptest
container and can be ignored.

## Manual operation

### Launching test containers
To launch a test container do
```
$ sudo bash launch_container.sh nr
```
where nr is a positive number to identify the container.  The container
will be called bgptest\_nr.

To cleanup the container and associated resources do
```
$ sudo bash cleanup_container.sh nr
```

### Connect/disconnect ASes
To disconnect AS x
```
$ sudo bash disconnect.sh x
```

To connect it back to the network
```
$ sudo bash connect.sh x
```

Note that there is no command to disconnect it from the test environment,
connect.sh automatically takes disconnects it first should it be connected.

## Files

### bgplib.py
Used by test_as.py in the bgptest container.

### bgptest.sh
Shell library containing functions common to the different scripts manipulating
the mini-internet.

### bundle_results.py
Puts the json and lg output into the results database of that AS.

### cleanup_container.sh
Kills the bgptest container and deletes its bridges and links.

### configure_container.sh
Connects a disconnected AS to a bgptest container.

### connect.sh
Connects a AS back to the mini-internet

### copy_back.sh
Copies the result database from the bgptest container into the current
directory.

### copy.sh
Copies results database, bgplib and test\_2020.py into the bgptest
container.

### disconnect.sh
Disconnect an AS from the mini-internet.

### display.sh
Displays each veth interface name of the host and the name of the other end.

### fake_network.sh
*EXPERIMENTAL* The same as configure_container.sh except that the bgptest
container can be configured with a different AS number.  E.g. AS 3 is
disconnected and connected to test container 1, but everything is configured
like it would be for AS 4.

### gentest.py
Creates the results database to be used in the test.

### gentest.py
Precursor to gentest.py when the approach to testing was different.

### getlinks.py/getlinks.sh
Used to get and parse the output of various ip(8) commands into the links
database.
Only getlinks.sh should be called.  It executes the required ip(8) commands
and pipes them into the Python script.  This split exists so that Python
can be executed as non-root.

### launch_container.sh
Launches a new test container and creates interfaces and bridges it requires.

### link_bridge.py
Returns the bridge the interface is a member of in the connected mini-internet.

### make_db.py
Extracts topology information from the configs directory into config.db.

### make_db_useful.py
Combines links.db and ovs.db into bgp.db in an useful ways.

### Makefile
Compile go code and generate databases.

### parse_ovs.py/parse_ovs.sh
Used to create ovs.db witht the current state of bridges and ports.  Only
parse_ovs.sh should be called.  It executes the required ovs-vsctl commands and
pipes the output into parse_ovs.py.  This split exists so that Python can be
executed as non-root.

### random.sh
Creates random-log.

### region.sh
Returns a comma separated list of all tier2 ASes in a region.  To be used as an
input to the runner.

### runall.sh
Executes a command on all routers of an AS.

### runner.go
Contains the code for the runner.  Calls all other scripts as required to test
an AS.

### start_exabgp.sh
Starts exabgp inside the bgptest container and also handles initial
announcements.

### test_as.py
Contains the test code run inside the container.  Collects its findings in
bgp.db.

### tier2.sh
Returns a comma separated list of all tier2 ASes.  To be used as an input to
the runner.

### upload.sh
*EXPERIMENTAL* Rewrites and uploads FRR configurations into an AS.  The rewriting
is used to change interface names accordingly to the AS in which the files are
uploaded.  Related to the fake_network.sh script.
