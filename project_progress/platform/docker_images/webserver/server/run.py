#!/usr/bin/python3
"""Create and run the app using bjoern."""

import bjoern

from routing_project_server import create_app

if __name__ == "__main__":

    #Clear the database
    with open("/server/routing_project_server/database.db",'r+') as file:
        file.truncate(0)

    #Clear the login log
    with open("/server/routing_project_server/admin_login_log.txt",'r+') as file:
        file.truncate(0)

    app = create_app()
    host = app.config['HOST']
    port = app.config['PORT']
    print(f"Running server on `{host}:{port}`.")
    bjoern.run(app, host, port)
