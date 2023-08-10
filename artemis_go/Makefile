all: build
	 ./ihd detect \
	--updates ~/Classes/mini_internet_extention/platform/docker_images/exabgp_monitor/parser/output.csv \
	--prefixes ~/Classes/mini_internet_extention/platform/docker_images/exabgp_monitor/as_prefixes.csv \
	--output ~/Classes/mini_internet_extention/platform/mini-internet_hijacks.csv
build:
	go build -o ihd main.go	utils.go
