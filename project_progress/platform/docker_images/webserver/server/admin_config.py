LOCATIONS = {
    "config_directory": "${CONFIGDIR_SERVER}",
    'as_config': "${CONFIGDIR_SERVER}/AS_config.txt",
    "as_connections_public": "${CONFIGDIR_SERVER}/aslevel_links_students.txt",
    "as_connections": "${CONFIGDIR_SERVER}/aslevel_links.txt",
    'groups': '${DATADIR_SERVER}',
}
BASIC_AUTH_USERNAME = 'admin'
BASIC_AUTH_PASSWORD = 'admin'
BACKGROUND_WORKERS = True
HOST = '0.0.0.0'
PORT = 8010
STATS_UPDATE_FREQUENCY = 60
SQLALCHEMY_DATABASE_URI = "sqlite:////server/admin_server/database.db"
SECRET_KEY = "HY335_papastam"