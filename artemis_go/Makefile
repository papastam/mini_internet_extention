detect_as: build
	 ./artemis_detector detect_as \
	--updates output \
	--input_type directory \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--asn 1 \
	--debug

detect_all: build
	 ./artemis_detector detect_all \
	--updates 1_output.csv \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--debug

build:
	go build -o artemis_detector main.go	utils.go
