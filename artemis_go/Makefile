all: build
	 ./ihd detect \
	--updates ~/Classes/mini_internet_extention/project_progress/platform/docker_images/exabgp_monitor/parser/output.csv \
	--prefixes ~/Classes/mini_internet_extention/project_progress/platform/docker_images/exabgp_monitor/as_prefixes.csv \
	--output ~/Classes/mini_internet_extention/project_progress/platform/mini-internet_hijacks.csv
test:
	./ihd detect  --updates test.csv --prefixes ../Dataset/ASNs/ukrainian-org/UA_202201-ips-ases-filtered.csv --output hijacks8.csv
build:
	go build -o ihd main.go	utils.go
