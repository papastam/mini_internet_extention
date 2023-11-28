#!/bin/bash
# Description: Hijack a BGP route

while getopts 'a:m:p:i:o:d:' OPTION; do
    case "$OPTION" in
        a)
            as_number="$OPTARG"
            ;;
        m)
            monitor_output="$OPTARG"
            ;;
        p)
            prefix_file="$OPTARG"
            ;;
        i)
            interval="$OPTARG"
            ;;
        o)
            output_file="$OPTARG"
            ;;
        d)
            docker_pipe="$OPTARG"
            ;;
        ?)
            echo "script usage: ./setup_artemis.sh [-a <AS number to monitor>] [-m <Monitor output file (csv)>] [-p <AS prefixes output file (.csv)>] [-i <Artemis update interval (in seconds)>] [-d <Docker pipe>] (-o <Output file>)" >&2
            exit 1
            ;;
    esac
done
shift "$(($OPTIND -1))"

# INTERVAL
if [ -z "$interval" ]; then
    interval=1 # Default interval is 1 second
elif [[ ! $interval =~ ^[0-9]+$ ]]; then
    echo "Error: Interval is not a number"
    exit 1
elif [ "$interval" -lt 1 ]; then
    echo "Error: Interval must be more than 1 second"
    exit 1
fi

# AS NUMBER
if [ -z "$as_number" ]; then
    echo "script usage: ./setup_artemis.sh [-a <AS number to monitor>] [-m <Monitor output file (csv)>] [-p <AS prefixes output file (.csv)>] [-i <Artemis update interval (in seconds)>] [-d <Docker pipe>] (-o <Output file>)" >&2
    echo "AS number is required" >&2

    exit 1
fi

if [[ ! $as_number =~ ^[0-9]+$ ]]; then
    echo "Error: Not an AS number"
    exit 1
fi

# CONFIGS DIR
if [ -z "$monitor_output" ]; then
    echo "script usage: ./setup_artemis.sh [-a <AS number to monitor>] [-m <Monitor output file (csv)>] [-p <AS prefixes output file (.csv)>] [-i <Artemis update interval (in seconds)>] [-d <Docker pipe>] (-o <Output file>)" >&2
    echo "Monitor output file is required" >&2

    exit 1
elif [ ! -f "$monitor_output" ]; then
    echo "Error: Monitor output file does not exist"
    exit 1
else 
    monitor_output="$(realpath $monitor_output)"
fi


# PREFIX FILE
if [ -z "$prefix_file" ]; then
    echo "script usage: ./setup_artemis.sh [-a <AS number to monitor>] [-m <Monitor output file (csv)>] [-p <AS prefixes output file (.csv)>] [-i <Artemis update interval (in seconds)>] [-d <Docker pipe>] (-o <Output file>)" >&2
    echo "Prefix file is required" >&2

    exit 1
elif [ ! -f "$prefix_file" ]; then
    echo "Error: Prefix file does not exist"
    exit 1
else
    prefix_file="$(realpath $prefix_file)"
fi

# OUTPUT FILE
if [ -z "$output_file" ]; then
    output_file="${as_number}_artemis_output.csv"
    umask 000; touch "${output_file}"
    umask 666
    echo "Created ./${output_file}"
elif [ -f "$output_file" ]; then
    output_file="$(realpath $output_file)"
fi

# DOCKER PIPE
if  [ ! -p "$docker_pipe" ]; then
    echo "Error: Docker pipe does not exist"
    exit 1
else
    docker_pipe="$(realpath $docker_pipe)"
fi

# Kill any existing ARTEMIS containers
echo "Killing any existing ARTEMIS containers"
docker kill "${as_number}_ARTEMIS" | true
docker rm "${as_number}_ARTEMIS" | true

# start ARTEMIS container
docker run -itd --net='none' --name="${as_number}_ARTEMIS"  \
    -v ${monitor_output}:/parser/output.csv \
    -v ${prefix_file}:/parser/as_prefixes.csv \
    -v ${output_file}:/output/astemis_output.csv \
    -v ${docker_pipe}:/pipe \
    -e "ASN=${as_number}" \
    -e "ARTEMIS_INTERVAL=30" \
    --hostname="${as_number}_ARTEMIS" --cpus=2 --pids-limit 100 \
    papastam/mi-artemis

passwd="$(openssl rand -hex 8)"
echo -e ""${passwd}"\n"${passwd}"" | docker exec -i ${as_number}_ARTEMIS passwd root
echo "Changed root password for ${as_number}_ARTEMIS container to: ${passwd}"

echo "Created ARTEMIS container for AS ${as_number}"