build:
	# Build the image
	docker kill EXABGP_MONITOR || true
	docker rm EXABGP_MONITOR || true
	docker rmi exabgp_monitor || true
	docker build --tag="exabgp_monitor" .

run:
	# If the container exists remove it
	docker rm -f EXABGP_MONITOR || true
	# Run the container
	docker run -itd --name="EXABGP_MONITOR" -v ./exabgp.conf:/exabgp.conf --hostname="EXABGP_MONITOR" --cpus=2 --pids-limit 100 exabgp_monitor exabgp.conf

stop:
	docker stop EXABGP_MONITOR