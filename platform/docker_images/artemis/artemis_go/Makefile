all: build
	 ./ihd interval \
	--updates 1_output.csv \
	--prefixes as_prefixes.csv \
	--output mini-internet_hijacks.csv \
	--interval 1
build:
	go build -o ihd main.go	utils.go
