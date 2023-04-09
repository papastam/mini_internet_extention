build:
	docker build --tag="miniinterneteth/d_webserver" "."

run:
	sudo ./run_server.sh

logs:
	docker logs -f WEB

rlogs: run 
	docker logs -f WEB

blogs: build run
	docker logs -f WEB

connect:
	docker exec -it WEB bash

stop: 
	./stop_server.sh

db:
	sqlite3 server/database/database.db