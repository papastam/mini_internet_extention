build:
	# Build the image
	docker kill EXABGP_MONITOR || true
	docker rm EXABGP_MONITOR || true
	docker rmi exabgp_monitor || true
	docker build --tag="exabgp_monitor" .
	docker tag exabgp_monitor:latest papastam/mi-exabgp_monitor:latest
	docker push papastam/mi-exabgp_monitor:latest

stop:
	docker stop EXABGP_MONITOR