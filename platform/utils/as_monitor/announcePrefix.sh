#!/bin/bash

# This script is used to announce a BGP prefix to a given AS

duration=0
while getopts 'a:p:t:' OPTION; do
    case "$OPTION" in
        a)
            as_number="$OPTARG"
            ;;
        p)
            prefix="$OPTARG"
            ;;
        t)
            # If duration is zero, then advertise indefinitely
            duration="$OPTARG"
            ;;
        ?)
            echo "script usage: ./announcePrefix.sh [-a <AS number>] [-p <Prefix to announce>] (-t <duration in minutes>)" >&2
            exit 1
            ;;
    esac
done
shift "$(($OPTIND -1))"

if [[ ! $duration =~ ^[0-9]+$ ]]; then
    echo "Error: Duration is not a number"
    exit 1
elif [ "$duration" -lt 0 ]; then
    echo "Error: Duration must not be a negative number"
    exit 1
fi

if [ -z "$as_number" ] || [ -z "$prefix" ]; then
    echo "script usage: ./announcePrefix.sh [-a <AS number>] [-p <Prefix to announce>] (-t <duration in minutes>)" >&2
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

# Advertise the prefix for each router of the as
routers=($(docker ps --format '{{.Names}}' | grep -w -E "${as_number}_.*router"))
for router in "${routers[@]}"; do
    echo "(AS${as_number})Advertising prefix ${prefix} from ${router_name}router"

    # Advertise the prefixes
    {
        echo "#!/bin/bash"
        echo "vtysh  -c 'conf t' \\"
        echo " -c 'ip route ${prefix} Null0' \\"
        echo " -c 'router bgp ${as_number}' \\"
        echo " -c 'network ${prefix}' \\"
        echo " -c 'exit' \\"
        echo " -c 'exit' \\"
    } | docker exec -i "${router}" bash
done

# If the duration is 0 then exit
if [ "$duration" -eq 0 ]; then
    exit 0
fi

# Sleep for the duration of the advertisement
for (( i=duration; i>0; i-- )); do
    if [ "$i" -eq 1 ]; then
        echo "(AS${as_number})1 minute Remaining"
    else
        echo "(AS${as_number})$((i)) minutes Remaining"
    fi
    sleep 1m
done

for router in "${routers[@]}"; do
    echo "(AS${as_number})Withdrawing the advertisements for ${prefix} from ${router_name}router"

    # Withdraw the prefix
    {
        echo "#!/bin/bash"
        echo "vtysh  -c 'conf t' \\"
        echo " -c 'no ip route ${prefix} Null0' \\"
        echo " -c 'router bgp ${as_number}' \\"
        echo " -c 'no network ${prefix}' \\"
        echo " -c 'exit' \\"
        echo " -c 'exit' \\"
    } | docker exec -i "${router}" bash
done