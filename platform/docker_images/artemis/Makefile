build:
	# Build the image
	docker kill ARTEMIS || true
	docker rm ARTEMIS || true
	docker rmi artemis || true
	docker build --tag="artemis" .
	docker tag artemis:latest papastam/mi-artemis:latest
	docker push papastam/mi-artemis:latest

stop:
	docker stop ARTEMIS || true
	docker rm ARTEMIS || true

run: stop build
	docker run -d --name ARTEMIS \
	-v /home/chris/Classes/mini_internet_extention/platform/groups/exabgp_monitor/output/1_output.csv:/parser/output.csv \
	-v /home/chris/Classes/mini_internet_extention/platform/groups/exabgp_monitor/output/as_prefixes.csv:/parser/as_prefixes.csv \
	artemis
	docker logs ARTEMIS -f