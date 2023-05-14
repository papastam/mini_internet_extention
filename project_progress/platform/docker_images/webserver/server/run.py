#!/usr/bin/python3
"""Create and run the app using bjoern."""

import bjoern
from multiprocessing import Process

from database import init_db
from routing_project_server import create_project_server
from admin_server import create_admin_server
import os
import signal

from utils import debug, reset_files

project_server_run = None
admin_server_run = None

if __name__ == "__main__":
    
    build=False
    if os.getenv('BUILD')=="true":
        debug("Building database...")
        reset_files()
        db_session = init_db(build=True)
        build=True
    else:
        debug("Build environment variable not set. Not building database.")
        db_session = init_db()

    project_server = create_project_server(db_session,build=build)
    project_host = project_server.config['HOST']
    project_port = project_server.config['PORT']
    
    # bjoern.run(project_server, project_host, project_port)
    
    admin_server = create_admin_server(db_session,build=build)
    admin_host = admin_server.config['HOST']
    admin_port = admin_server.config['PORT']

    # bjoern.run(admin_server, admin_host, admin_port)

    project_server_run = Process(
        target=bjoern.run,
        args=(project_server, project_host, project_port)
    )
    project_server_run.start()
    print(f"\033[35mRunning project server on `{project_host}:{project_port}`.\033[00m ")

    admin_server_run = Process(
        target=bjoern.run,
        args=(admin_server, admin_host, admin_port)
    )
    admin_server_run.start()
    print(f"\033[45mRunning admin server on `{admin_host}:{admin_port}`.\033[00m")

def shutdown_handler(signum, frame):
    print("Shutting down...")
    project_server_run.terminate()
    admin_server_run.terminate()
    exit(1)

signal.signal(signal.SIGINT, shutdown_handler)