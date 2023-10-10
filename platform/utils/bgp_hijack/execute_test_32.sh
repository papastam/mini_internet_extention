#!/bin/bash

if (($UID != 0)); then
    echo "Please run as root"
    exit
fi

# Parse command line arguments
while getopts ":n:s" opt; do
    case $opt in
        n)
            type="normal"
            ;;
        s)
            type="stress"
            ;;
        \?)
            type="all"
            ;;
    esac
done
echo "Executing ${type} tests"
# List of targets

rm -rf tests | True > /dev/null 2>&1
mkdir tests | True > /dev/null 2>&1

# Execute tests
if [ "$type" = "normal" ] | [ "$type" = "all" ]; then
    # Execute normal tests
    echo "Executing normal tests"
    targets=(1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 31)
    for attacker in "${targets[@]}"
    do
        echo "Executing hijack.sh for AS${attacker}"
        /bin/bash $(pwd)/hijack.sh -a ${attacker} -p $((attacker+1)).0.0.0/8 -r EAST -t 60 > tests/test_${attacker}.log 2>&1 &

        echo "Sleeping for 15 minutes"
        sleep 900
    done
fi
if [ "$type" = "stress" ] | [ "$type" = "all" ]; then
    # Execute stress test
    echo "Executing stress tests"
    targets=(1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 \
             18 19 20 21 22 23 24 25 26 27 28 29 30 31 32)
    for attacker in "${targets[@]}"
    do
        echo "Executing hijack.sh for AS${attacker}"
        if [ "$attacker" -eq 32 ]; then
            /bin/bash $(pwd)/hijack.sh -a ${attacker} -p 1.0.0.0/8 -r EAST -t 60 > tests/test_${attacker}.log 2>&1 &
        else
            /bin/bash $(pwd)/hijack.sh -a ${attacker} -p $((attacker+1)).0.0.0/8 -r EAST -t 60 > tests/test_${attacker}.log 2>&1 &
        fi
    done
fi

