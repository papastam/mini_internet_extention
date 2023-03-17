#!/usr/bin/python3
"""Create and run the app using bjoern."""

import bjoern
from multiprocessing import Process

from routing_project_server import create_project_server
from admin_server import create_admin_server

if __name__ == "__main__":

    #Clear the databases
    with open("/server/routing_project_server/database.db",'r+') as file:
        file.truncate(0)
    with open("/server/admin_server/database.db",'r+') as file:
        file.truncate(0)

    #Clear the admin login log
    with open("/server/admin_server/admin_login.log",'r+') as file:
        file.truncate(0)
    
    project_server = create_project_server()
    project_host = project_server.config['HOST']
    project_port = project_server.config['PORT']
    
    # bjoern.run(project_server, project_host, project_port)
    
    admin_server = create_admin_server()
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