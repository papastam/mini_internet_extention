run: build
	 ./ihd active \
	--updates 1_output.csv \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--interval 5 \
	--pipename pipe \
	--asn 2 \
	--debug
build:
	go build -o ihd main.go	utils.go
