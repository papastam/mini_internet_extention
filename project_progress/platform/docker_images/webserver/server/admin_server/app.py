"""A webserver specifically for the admin interface.
"""

import os
import traceback
from datetime import datetime as dt
from multiprocessing import Process
from time import sleep, strftime, gmtime
from flask import Flask, jsonify, redirect, render_template, request, url_for, flash
from flask_basicauth import BasicAuth
from jinja2 import StrictUndefined

from flask_login import login_user, login_required, logout_user, current_user
# from flask_sqlalchemy import SQLAlchemy
# from wtforms.validators import InputRequired, Length, ValidationError
# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt
from datetime import datetime
# import json
# import time
# import string


import psutil

from . import admin

config_defaults = {
    'LOCATIONS': {
        'groups': '../../../groups',
        'as_config': "../../../config/AS_config.txt",
        "config_directory": "../../../config",
    },
    'BASIC_AUTH_USERNAME': 'admin',
    'BASIC_AUTH_PASSWORD': 'admin',
    'HOST': '0.0.0.0',
    'PORT': 8010,
    # Background processing for resource-intensive tasks.
    'BACKGROUND_WORKERS': False,
    'AUTO_START_WORKERS': True,
    "STATS_UPDATE_FREQUENCY": 60,
    #admin login page config
    'SQLALCHEMY_DATABASE_URI' : 'sqlite:////server/routing_project_server/database.db',
    'SECRET_KEY' : 'HY335_papastam'
}

admin_users= {
    "papastam": "admin"
}   

def debug(message):
    print("\033[35mDEBUG: " + message + "\033[0m")

def admin_log(message):
    """Log message to admin log."""
    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    with open("/server/routing_project_server/admin_login.log", "a") as file:
        file.write(time + ' | ' + message+'\n')

def create_admin_server(config=None):
    """Create and configure the app."""
    app = Flask(__name__)
    app.config.from_mapping(config_defaults)
    app.jinja_env.undefined = StrictUndefined

    if config is None:
        config = os.environ.get("ADMIN_SERVER_CONFIG", None)

    if config is not None and isinstance(config, dict):
        app.config.from_mapping(config)
    elif config is not None:
        app.config.from_pyfile(config)

    #Used for bgp analysis, to be removed
    basic_auth = BasicAuth(app)



    #Admin login init
    admin.login_manager.init_app(app)
    bcrypt = Bcrypt(app) 

    admin.db.init_app(app)
    with app.app_context():
        admin.db.create_all()

        #Add admin users
        for user, password in admin_users.items():
            admin.Admin.query.delete()
            new_user = admin.Admin(username=user, password=bcrypt.generate_password_hash(password).decode('utf-8'))
            admin.db.session.add(new_user)
            admin.db.session.commit()
            admin_log("INIT: Added user: " + user)

    @app.route("/")
    @login_required
    def index():
        """Redict to matrix as starting page."""
        return redirect(url_for("dashboard"))


    #############################################
    ################ Admin side #################
    #############################################

    @app.route("/login", methods=['GET', 'POST'])
    def admin_login():
        form = admin.LoginForm()
        if form.validate_on_submit():
            admin_log(f"LOGIN: User {form.username.data} requested login")
            admin_user = admin.Admin.query.filter_by(username=form.username.data).first()
            if admin_user and bcrypt.check_password_hash(admin_user.password, form.password.data):
                admin_log(f"LOGIN: User {form.username.data} logged in sucesfully from {request.remote_addr}")
                login_user(admin_user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
            elif admin_user:
                admin_log(f"LOGIN: User {form.username.data} tried to login with wrong password (from {request.remote_addr})")
                flash('Login unsuccessful. Please check username and password', 'danger')
            else:
                admin_log(f"LOGIN: Login attemt from invalid user: {form.username.data} (from {request.remote_addr})")
                flash('Login unsuccessful. Please check username and password', 'danger')


        return render_template('login.html', form=form)

    @app.route("/dashboard", methods=["GET"])
    @login_required
    def dashboard():
        if 'stats' in request.args:
            start = request.args.get('start', default=0)
            start_datetime = datetime(int(start[0:4]), int(start[5:7]), int(start[8:10]), int(start[11:13]), int(start[14:16]))
            
            end = request.args.get('end', default=0)
            if (end == '0') or (end == 0):
                end_datetime = datetime.now()
            else:
                end_datetime = datetime(int(end[0:4]), int(end[5:7]), int(end[8:10]), int(end[11:13]), int(end[14:16]))
            
            debug(f"Querying measurements from {start_datetime} to {end_datetime}")

            res = admin.Measurement.query.filter(admin.Measurement.time.between(start_datetime, end_datetime)).all()

            debug(f"Query returned {len(res)} measurements")

            retarr=[]
            for measurement in res:
                retarr.append({
                    "time": measurement.time,
                    "cpu": measurement.cpu,
                    "memory": measurement.memory,
                    "disk": measurement.disk
                })

            debug(f"Returning {len(retarr)} measurements: {retarr}")

            return jsonify(retarr)
        return render_template("dashboard.html")

    @app.route("/logout")
    @login_required
    def logout():
        admin_log(f"LOGOUT: User {current_user.username} logged out")
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('admin_login'))

    # Start workers if configured.
    if app.config["BACKGROUND_WORKERS"] and app.config['AUTO_START_WORKERS']:
        start_workers(app)

    return app

# Worker functions.
# =================

def start_workers(given_app):
    """Create background processes"""
    processes = []

    stats = Process(
        target=loop,
        args=(measure_stats,
              given_app.config['STATS_UPDATE_FREQUENCY'], given_app.config, given_app),
        kwargs=dict(worker=True)
    )
    stats.start()
    processes.append(stats)

    return processes


def loop(function, freq, *args, **kwargs):
    """Call function in loop. Freq must be in seconds."""
    print(f"\033[32mRunning worker `{function.__name__}` \033[03m(every {freq}s).\033[00m")
    while True:
        starttime = dt.utcnow()
        try:
            try:
                function(*args, **kwargs)
            except Exception as error:
                # Attach message to exception.
                raise RuntimeError(
                    f"\033[41mWorker `{function.__name__}` crashed! Restarting.\033[00m"
                ) from error
        except:  # pylint: disable=bare-except
            traceback.print_exc()
        remaining_secs = freq - (dt.utcnow() - starttime).total_seconds()
        if remaining_secs > 0:
            sleep(remaining_secs)

def measure_stats(config, app, worker=False):

    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory()[2]
    disk = psutil.disk_usage('/')[3]

        #Add admin users
        # for user, password in admin_users.items():
    with app.app_context():
        new_measurement = admin.Measurement(cpu=cpu, memory=memory, disk=disk)
        admin.db.session.add(new_measurement)
        admin.db.session.commit()
        print("\033[93mMeasured stats \033[03m(%s)\033[00m" % str(time))

    return (time, cpu, memory, disk)
