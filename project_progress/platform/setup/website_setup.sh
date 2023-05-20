#!/bin/bash
#
# Start the containers that will run the webserver and all the tools
# related to it
#
# Concretely, we use two containers
# - WEB: the webserver container delivering the pages.
# - PROXY: a container running the reverse proxy traefik, which takes care
#          of letsencrypt certificates, too.
#
# TODO:
# - We could make HTTPS optional.
# - How to make hostname and mail easy to configure?

set -o errexit
set -o pipefail
set -o nounset

DIRECTORY="$1"
DOCKERHUB_USER="${2:-thomahol}"
BUILD="false"

if [ "$#" -gt 2 ]; then
    if [ "$3" == "-b" ]; then
        BUILD="true"
    fi
fi

echo "Build: ${BUILD}"

######################################
### UPDATE THE FOLLOWING VARIABLES ###
######################################
# Hostname and ACME mail for letsencrypt.
# You need to specify the hostname of the server and an email for
# LetsEncrypt to be enabled.
# UPDATE THOSE VARIABLES. HOSTNAME -> hostname of the server and EMAIL -> empty string (for http)
HOSTNAME="pc-10328.ethz.ch"
ACME_MAIL=""

# Hostname and ports for the webserver and krill on the host.
# (must be publicly available)
# you can change http and https ports, but letsencrypt won't work, so its not recommended.
SERVER_PORT_HTTP="80"
SERVER_PORT_HTTPS="443"

# Use the one you want, make sure to make it reachable from outside.
PORT_KRILL="3000"

# Put your timezone here.
TZ="Europe/Athens"
######################################

# Directories on host.
DIRECTORY="$1"

# Source directories.
DATADIR="$(pwd ${DIRECTORY})/groups"
CONFIGDIR="$(pwd ${DIRECTORY})/config"
IMAGESDIR="$(pwd ${DIRECTORY})/docker_images"
UTILSDIR="$(pwd ${DIRECTORY})/utils"

# Directory for server config.
mkdir -p "${DATADIR}/webserver"
PROJECTCONFIGFILE="${DATADIR}/webserver/project_config.py"
ADMINCONFIGFILE="${DATADIR}/webserver/admin_config.py"
LETSENCRYPT="${DATADIR}/webserver/letsencrypt"

# Directories inside the container.
SERVER_DIR="/server"
DATADIR_SERVER='/server/data'
CONFIGDIR_SERVER='/server/configs'

DOCKERHUB_USER="${2:-thomahol}"
source "${DIRECTORY}"/config/subnet_config.sh
source "${DIRECTORY}"/setup/_parallel_helper.sh

# TLS and LetsEncrypt
if [ ! -z "$ACME_MAIL" ] && [ ! -z "$HOSTNAME" ] && [ "$HOSTNAME" != "localhost" ] ; then
    IFS=" " read -ra TLSCONF <<< "\
    --entrypoints.web.http.redirections.entrypoint.to=websecure \
    --entrypoints.web.http.redirections.entrypoint.scheme=https \
    --entrypoints.web.http.redirections.entrypoint.permanent=true \
    --certificatesresolvers.project_resolver.acme.tlschallenge=true \
    --certificatesresolvers.project_resolver.acme.email=${ACME_MAIL} \
    --certificatesresolvers.project_resolver.acme.storage=/letsencrypt/acme.json \
    --entrypoints.websecure.http.tls.certresolver=project_resolver \
    --entrypoints.krill.http.tls.certresolver=project_resolver"
    KRILL_SCHEME="https"
else
    TLSCONF=""
    KRILL_SCHEME="http"
fi

# Write the webserver config file
cat > "$PROJECTCONFIGFILE" << EOM
LOCATIONS = {
    "config_directory": "${CONFIGDIR_SERVER}",
    'as_config': "${CONFIGDIR_SERVER}/AS_config.txt",
    "as_connections_public": "${CONFIGDIR_SERVER}/aslevel_links_students.txt",
    "as_connections": "${CONFIGDIR_SERVER}/aslevel_links.txt",
    'groups': '${DATADIR_SERVER}',
    "matrix": "${DATADIR_SERVER}/matrix/connectivity.txt",
    "as_passwords": "${DATADIR_SERVER}/passwords.txt",
    "docker_pipe": "${SERVER_DIR}/docker_pipe"
}
KRILL_URL="${KRILL_SCHEME}://{hostname}:${PORT_KRILL}/index.html"
BASIC_AUTH_USERNAME = 'admin'
BASIC_AUTH_PASSWORD = 'admin'
BACKGROUND_WORKERS = True
AUTO_START_WORKERS = True
MATRIX_UPDATE_FREQUENCY = 60  # seconds
ANALYSIS_UPDATE_FREQUENCY = 300  # seconds
CANCELLATION_BLOCKING_TIME = 60  # minutes
HOST = '0.0.0.0'
PORT = 8000
SQLALCHEMY_DATABASE_URI = "sqlite:////server/routing_project_server/database.db"
SECRET_KEY = "@+5b+Wg+DF2.jWq8Rt;Ti26xvXDG)kK1N1MSp)Pf5ohoYi#X,Pi+L;%sD_yvT-w3"
EOM

cat > "$ADMINCONFIGFILE" << EOM
LOCATIONS = {
    "config_directory": "${CONFIGDIR_SERVER}",
    'as_config': "${CONFIGDIR_SERVER}/AS_config.txt",
    "as_connections_public": "${CONFIGDIR_SERVER}/aslevel_links_students.txt",
    "as_connections": "${CONFIGDIR_SERVER}/aslevel_links.txt",
    'groups': '${DATADIR_SERVER}',
    "docker_pipe": "${SERVER_DIR}/docker_pipe"
}
BASIC_AUTH_USERNAME = 'admin'
BASIC_AUTH_PASSWORD = 'admin'
BACKGROUND_WORKERS = True
AUTO_START_WORKERS = True
ALLOW_PARALLEL_RENDEZVOUS = True
HOST = '0.0.0.0'
PORT = 8010
STATS_UPDATE_FREQUENCY = 60
SQLALCHEMY_DATABASE_URI = "sqlite:////server/admin_server/database.db"
SECRET_KEY = "LU85DkRZCc$@r~k%yQzDLRnvn.i.]&qkYYY7(bj^#xPMCzT1&N&1+G]FCOpK<+p4"
EOM

# First start the web container, adding labels for the traefik proxy.
# We only have one webserver; traffic for any hostname will go to it.
# NOTE: Can we define all dynamic labels for krill here?
docker run -itd --name="WEB" --cpus=2 \
    --network bridge -p 8000:8000 -p 8010:8010 \
    --pids-limit 100 \
    -v ${DATADIR}:${DATADIR_SERVER} \
    -v ${CONFIGDIR}:${CONFIGDIR_SERVER} \
    -v ${IMAGESDIR}/webserver/server/:/server/ \
    -v ${PROJECTCONFIGFILE}:/server/project_config.py \
    -v ${ADMINCONFIGFILE}:/server/admin_config.py \
    -v ${UTILSDIR}/pipe/docker_pipe:/server/docker_pipe \
    -e PROJECT_SERVER_CONFIG=/server/project_config.py \
    -e ADMIN_SERVER_CONFIG=/server/admin_config.py \
    -e TZ=${TZ} \
    -e DATADIR_SERVER=${DATADIR_SERVER}\
    -e CONFIGDIR_SERVER=${CONFIGDIR_SERVER}\
    -e BUILD=${BUILD}\
    -l traefik.enable=true \
    -l traefik.http.routers.web.entrypoints=web \
    -l traefik.http.routers.websecure.entrypoints=websecure \
    --hostname="web" \
    --privileged \
    "${DOCKERHUB_USER}/d_webserver"

# Next start the proxy
# Setup based on the following tutorials:
# https://doc.traefik.io/traefik/user-guides/docker-compose/basic-example/
# https://doc.traefik.io/traefik/user-guides/docker-compose/acme-http/
# To enable the dashboard for debugging, add -p 8080:8080
# and the command "--api.insecure=true" (at the very end).
docker run -d --name='PROXY' \
    --network bridge \
    -p ${SERVER_PORT_HTTP}:${SERVER_PORT_HTTP} \
    -p ${SERVER_PORT_HTTPS}:${SERVER_PORT_HTTPS} \
    -p ${PORT_KRILL}:${PORT_KRILL} \
    -v "/var/run/docker.sock:/var/run/docker.sock:ro" \
    -v ${LETSENCRYPT}:/letsencrypt \
    --privileged \
    traefik:v2.6 \
    "--providers.docker=True"\
    "--providers.docker.exposedbydefault=false" ${TLSCONF[@]} \
    "--providers.docker.defaultRule=Host(\"${HOSTNAME}\")" \
    "--entrypoints.web.address=:${SERVER_PORT_HTTP}" \
    "--entrypoints.websecure.address=:${SERVER_PORT_HTTPS}" \
    "--entrypoints.krill.address=:${PORT_KRILL}"
