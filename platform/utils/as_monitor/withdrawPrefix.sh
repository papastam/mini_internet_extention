#!/bin/bash

# This script is used to withdraw a BGP prefix to a given AS

duration=0
while getopts 'a:p:t:' OPTION; do
    case "$OPTION" in
        a)
            as_number="$OPTARG"
            ;;
        p)
            prefix="$OPTARG"
            ;;
        ?)
            echo "Script usage: ./withdrawPrefix.sh [-a <AS number>] [-p <Prefix to withdraw>]" >&2
            exit 1
            ;;
    esac
done
shift "$(($OPTIND -1))"

if [ -z "$as_number" ] || [ -z "$prefix" ]; then
    echo "Script usage: ./withdrawPrefix.sh [-a <AS number>] [-p <Prefix to withdraw>]" >&2
    echo "AS number and prefix are required" >&2

    exit 1
fi

# Check wether the AS number is a number or not
if [[ ! $as_number =~ ^[0-9]+$ ]]; then
    echo "Error: Not an AS number"
    exit 1
fi

# Check wether the prefix is an IPv4 address or not
if [[ $prefix =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/[0-9]+$ ]]; then
    # Check quads are 0-255 and the subnet mask is 0-32
    IFS='/' read -r -a array <<< "$prefix"
    IFS='.' read -r -a quads <<< "${array[0]}"
    for quad in "${quads[@]}"; do
        if [ "$quad" -lt 0 ] || [ "$quad" -gt 255 ]; then
            echo "Error: Not an IPv4 address"
            exit 1
        fi
    done
    if [ "${array[1]}" -lt 0 ] || [ "${array[1]}" -gt 32 ]; then
        echo "Error: Not an IPv4 address"
        exit 1
    fi
else
    echo "Error: Not an IPv4 address"
    exit 1
fi

# Withdraw the prefix for each router of the as
routers=($(docker ps --format '{{.Names}}' | grep -w -E "${as_number}_.*router"))
for router in "${routers[@]}"; do
    echo "(AS${as_number})Withdrawing prefix ${prefix} from ${router_name}router"

    # Withdraw the prefix
    {
        echo "#!/bin/bash"
        echo "vtysh  -c 'conf t' \\"
        echo " -c 'ip route ${prefix} Null0' \\"
        echo " -c 'router bgp ${as_number}' \\"
        echo " -c 'no network ${prefix}' \\"
        echo " -c 'exit' \\"
        echo " -c 'exit' \\"
    } | docker exec -i "${router}" bash
done