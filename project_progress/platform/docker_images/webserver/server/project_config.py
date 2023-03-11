LOCATIONS = {
    "config_directory": "${CONFIGDIR_SERVER}",
    'as_config': "${CONFIGDIR_SERVER}/AS_config.txt",
    "as_connections_public": "${CONFIGDIR_SERVER}/aslevel_links_students.txt",
    "as_connections": "${CONFIGDIR_SERVER}/aslevel_links.txt",
    'groups': '${DATADIR_SERVER}',
    "matrix": "${DATADIR_SERVER}/matrix/connectivity.txt",
    "as_passwords": "/server/data/passwords.txt"
}
KRILL_URL="${KRILL_SCHEME}://{hostname}:${PORT_KRILL}/index.html"
BASIC_AUTH_USERNAME = 'admin'
BASIC_AUTH_PASSWORD = 'admin'
BACKGROUND_WORKERS = True
HOST = '0.0.0.0'
PORT = 8000
SQLALCHEMY_DATABASE_URI = "sqlite:////server/routing_project_server/database.db"
SECRET_KEY = "HY335_papastam"