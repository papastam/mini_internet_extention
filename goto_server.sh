#!/bin/bash
as=$1

if [ -z "$as" ]; then
	echo "Invalid syntax!"
	echo "./gotoAS.sh <AS#>"
	exit
fi

if [ $1 = "server" ]; then
	sshpass -p !hy335bhy335b! ssh -o StrictHostKeyChecking=no csduser01@147.52.203.13
else
	portn=$((2000+${as}))
	echo "Connecting to AS ${as}..."
	sshpass -p pastroumas ssh -o StrictHostKeyChecking=no -p ${portn} root@147.52.203.13
	exit
fi
