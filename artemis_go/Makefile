build:
	go build -o artemis_detector main.go	utils.go

detect_as: build
	 ./artemis_detector detect_as \
	--updates test2 \
	--input_type directory \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--asn 4 \
	--debug

detect_all: build
	 ./artemis_detector detect_all \
	--updates 1_output.csv \
	--input_type file \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--debug

active: build
	 ./artemis_detector active \
	--mitigation_script_path ../platform/utils/bgp_hijack/mitigate.sh \
	--updates ../platform/groups/exabgp_monitor/output \
	--input_type directory \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--interval 1 \
	--asn 3 \
	--debug

clean:
	rm -f artemis_detector