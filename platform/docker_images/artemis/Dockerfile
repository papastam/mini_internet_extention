FROM golang:latest

# Install debug tools
# ping ifconfig netstat traceroute make
RUN apt-get update \
    && apt-get install -y iputils-ping net-tools traceroute make \
    && apt-get clean

# copy artemis_go
COPY ./artemis_go /artemis_go

# build artemis_go
RUN cd /artemis_go \
    && go build -o ihd main.go utils.go \
    && cd ..

# Begin artemis_go interval
COPY ./run_artemis_interval.sh /run_artemis_interval.sh

ENTRYPOINT ["/artemis_go/ihd", "interval", \
	        "--updates", "/parser/output.csv", \
	        "--prefixes", "/parser/as_prefixes.csv", \
	        "--output", "AS_hijacks.csv", \
            "--interval", "1", \
            "--debug", "true" \
            ]