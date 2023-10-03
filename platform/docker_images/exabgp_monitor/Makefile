build:
	# Build the image
	docker kill EXABGP_MONITOR || true
	docker rm EXABGP_MONITOR || true
	docker rmi exabgp_monitor || true
	docker build --tag="exabgp_monitor" .

stop:
	docker stop EXABGP_MONITOR