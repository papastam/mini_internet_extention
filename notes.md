# Objectives
## 1. Restore mechanism from configuration file for Hosts, Switches, Routers
   - [X] [./restore_configs.sh](https://github.com/nsg-ethz/mini_internet_project/pull/19) Pull Request

## 2. Visualization tool
   - Tools:
      - [networkx](https://networkx.github.io/) for python
      - [LibreNMS](https://github.com/librenms)
   - [ ] Visualization tool for AS topology
   - [ ] Visualization tool for traffic (traceroute, ping)

## 3. Ping all/Traceroute all implementation
   - [ ] pingall
   - [ ] tracerouteall

## 4. Auto grading and auto debuging tools for TA use
   - [ ] Create script which will parese all configurations of a specified AS and check if they are correct
   - [ ] False pattern detection for debuging purposes

## 5. Improvements on the website
   - [X] Add AS login 
      - [X] Automate the account creation based on the AS passwords
      - [X] Password changing option
         - Password storing and communicating between frontend and backend is not encrypted
         - [ ] Change passwords in the passwords text file @server host as well

   - Admin Server 
      - [X] Login page **(Example)[https://github.com/arpanneupane19/Python-Flask-Authentication-Tutorial]**
      - [ ] Auto grading/debugnihg tools
      - [X] Resource usage monitoring
      - [X] AS teams table (info of each student included)
      - [X] Creation of teams (Admin TA can assign Students to teams)
      - [ ] BGP updates monitoring
      - [ ] Inpact on performance (periodical ping between hosts)

## 6. Create a platform containing the __Artemis__ tool for the 4th assignment of the HY436 course

   - [ ] Check on the implementation of the __Artemis__ tool in GO 
   - [ ] Create a docker container where the __Artemis__ tool will be running
   
   - [ ] Examine the ExaBGP monitoring tool [exabgp-monitor](https://hub.docker.com/r/mavromat/exabgp-monitor)
   - [ ] Create a docker container where the ExaBGP tool will be running

   - [ ] Create a pipe between the ExaBGP and the __Artemis__ tool 
