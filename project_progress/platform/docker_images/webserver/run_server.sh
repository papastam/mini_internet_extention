DIRECTORY='/home/chris/Classes/mini_internet_extention/project_progress/platform'
DOCKERHUB_USER="miniinterneteth"

# docker build --tag="miniinterneteth/d_webserver" "."

docker stop WEB
docker rm WEB
docker stop PROXY
docker rm PROXY

cd ../..
time ./setup/website_setup.sh "${DIRECTORY}" "${DOCKERHUB_USER}"