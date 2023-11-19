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
	-v /home/chris/Classes/mini_internet_extention/platform/docker_images/artemis/mock_files/1_output.csv:/parser/output.csv \
	-v /home/chris/Classes/mini_internet_extention/platform/docker_images/artemis/mock_files/as_prefixes.csv:/parser/as_prefixes.csv \
	-v /home/chris/Classes/mini_internet_extention/platform/docker_images/artemis/mock_files/mock_pipe:/pipe \
	-e ASN=1 \
	artemis
	docker logs ARTEMIS -f