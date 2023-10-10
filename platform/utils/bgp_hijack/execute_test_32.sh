#!/bin/bash

if (($UID != 0)); then
    echo "Please run as root"
    exit
fi

# List of targets
targets=(1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 31)

rm -rf tests | True > /dev/null 2>&1
mkdir tests | True > /dev/null 2>&1

# Loop through each target and execute hijack.sh
for attacker in "${targets[@]}"
do
    echo "Executing hijack.sh for AS${target}"
    /bin/bash $(pwd)/hijack.sh -a ${attacker} -p $((attacker+1)).0.0.0/8 -r EAST -t 60 > tests/test_${attacker}.log 2>&1 &

    echo "Sleeping for 15 minutes"
    sleep 900
done

