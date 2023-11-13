build:
	# Build the image
	docker kill ARTEMIS || true
	docker rm ARTEMIS || true
	docker rmi artemis || true
	docker build --tag="artemis" .

stop:
	docker stop ARTEMIS || true
	docker rm ARTEMIS || true

run: stop
	docker run -d --name ARTEMIS \
	-v /home/chris/Classes/mini_internet_extention/platform/groups/exabgp_monitor/output/1_output.csv:/parser/output.csv \
	-v /home/chris/Classes/mini_internet_extention/platform/groups/exabgp_monitor/output/as_prefixes.csv:/parser/as_prefixes.csv \
	artemis
	docker logs ARTEMIS -f