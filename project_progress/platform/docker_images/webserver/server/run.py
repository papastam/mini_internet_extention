#!/usr/bin/python3
"""Create and run the app using bjoern."""

import bjoern

from routing_project_server import create_app

if __name__ == "__main__":

    with open("/server/routing_project_server/database.db",'r+') as file:
        file.truncate(0)

    app = create_app()
    host = app.config['HOST']
    port = app.config['PORT']
    print(f"Running server on `{host}:{port}`.")
    bjoern.run(app, host, port)
