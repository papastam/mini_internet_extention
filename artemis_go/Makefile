all: build
	./ihd detect  --updates ../Dataset/ASNs/ukrainian-org/UA_202201/UPDATES_START_2022-01-01\ 00\:00\:00-END_2022-02-01\ 00\:00\:00.csv --prefixes ../Dataset/ASNs/ukrainian-org/UA_202201-ips-ases-filtered.csv --lineno 161719966 --output hijacks8.csv --relations ../20220201.as-rel2.txt
test:
	./ihd detect  --updates test.csv --prefixes ../Dataset/ASNs/ukrainian-org/UA_202201-ips-ases-filtered.csv --output hijacks8.csv
build:
	go build -o ihd main.go	utils.go
