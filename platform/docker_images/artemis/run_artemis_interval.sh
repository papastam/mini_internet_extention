#! bin/bash

touch script.log
echo "Starting Artemis" >> script.log
# Check interval environment variable
if [ -z "$INTERVAL" ]; then
    echo "INTERVAL environment variable not set, defaulting to 120 seconds"
    INTERVAL=120
else
    echo "INTERVAL environment variable set to $INTERVAL seconds"
fi

# Run Artemis every INTERVAL seconds
while true; do
    echo "Running Artemis"

    ./artemis_go/ihd detect \
	--updates /parser/output.csv \
	--prefixes /parser/as_prefixes.csv \
	--output artemis_go/mini-internet_hijacks.csv
    
    echo "Sleeping for $INTERVAL seconds"
    sleep $INTERVAL
done