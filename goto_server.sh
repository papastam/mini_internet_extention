#!/bin/bash
as=$1

if [ -z "$as" ]; then
	echo "Invalid syntax!"
	echo "./gotoAS.sh <AS#>"
	exit
fi

portn=$((2000+${as}))
echo "Connecting to AS ${as}..."
sshpass -p pastroumas ssh -o StrictHostKeyChecking=no -p ${portn} root@147.52.203.13
exit
