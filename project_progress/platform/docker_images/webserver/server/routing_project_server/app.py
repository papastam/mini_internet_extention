"""A small web-server hosting all mini-internet tools.

The webserver needs access to the config and group directory,
or concretely to all paths present in the config under the key `LOCATIONS`.
Check the default config below for the list of paths.

Computing the connectivity matrix as well as the BGP analysis can take quite
a while, so it is possible to enabled `BACKGROUND_WORKERS` in the config to
start two background processes taking care of the updates in specified
intervals (`MATRIX_UPDATE_FREQUENCY`, `ANALYSIS_UPDATE_FREQUENCY`).

By default, these workers are started automatically when the app is created.
"""

import math
import os
import pickle
import traceback
from datetime import datetime as dt
from datetime import timezone
from multiprocessing import Process
from pathlib import Path
from time import sleep, strftime, gmtime
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request, url_for, flash
from flask_basicauth import BasicAuth
from jinja2 import StrictUndefined

from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import InputRequired, Length, ValidationError
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt
from datetime import datetime
import json
import time
import string


import psutil

from . import bgp_policy_analyzer, matrix, parsers, admin

config_defaults = {
    'LOCATIONS': {
        'groups': '../../../groups',
        'as_config': "../../../config/AS_config.txt",
        "as_connections_public":
        "../../../config/external_links_config_students.txt",
        "as_connections": "../../../config/external_links_config.txt",
        "config_directory": "../../../config",
        "matrix": "../../../groups/matrix/connectivity.txt"
    },
    'KRILL_URL': "http://{hostname}:3080/index.html",
    'BASIC_AUTH_USERNAME': 'admin',
    'BASIC_AUTH_PASSWORD': 'admin',
    'HOST': '127.0.0.1',
    'PORT': 8000,
    # Background processing for resource-intensive tasks.
    'BACKGROUND_WORKERS': False,
    'AUTO_START_WORKERS': True,
    'MATRIX_UPDATE_FREQUENCY': 60,  # seconds
    'ANALYSIS_UPDATE_FREQUENCY': 300,  # seconds
    "STATS_UPDATE_FREQUENCY": 60,
    'MATRIX_CACHE': '/tmp/cache/matrix.pickle',
    'ANALYSIS_CACHE': '/tmp/cache/analysis.db',
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

def create_app(config=None):
    """Create and configure the app."""
    app = Flask(__name__)
    app.config.from_mapping(config_defaults)
    app.jinja_env.undefined = StrictUndefined

    if config is None:
        config = os.environ.get("SERVER_CONFIG", None)

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
            new_user = admin.Admin(username=user, password=bcrypt.generate_password_hash(password).decode('utf-8'))
            admin.db.session.add(new_user)
            admin.db.session.commit()
            admin_log("INIT: Added user: " + user)

    @app.template_filter()
    def format_datetime(utcdatetime, format='%Y-%m-%d at %H:%M'):
        if utcdatetime.tzinfo is None:  # Attach tzinfo if needed
            utcdatetime = utcdatetime.replace(tzinfo=timezone.utc)
        localtime = utcdatetime.astimezone()
        return localtime.strftime(format)

    @app.template_filter()
    def format_timedelta_int(seconds):
        seconds = int(seconds)
        if seconds == 1:
            return "second"
        elif seconds == 60:
            return "minute"
        elif (seconds % 60) == 0:
            return f"{seconds // 60} minutes"
        return f"{seconds} seconds"

    @app.route("/")
    def index():
        """Redict to matrix as starting page."""
        return redirect(url_for("connectivity_matrix"))

    @app.route("/krill")
    def krill():
        """Allow access to krill, which is embedded as an iframe."""
        hostname = urlparse(request.base_url).hostname
        krill_url = app.config['KRILL_URL'].format(hostname=hostname)
        return render_template("krill.html", krill_url=krill_url)

    @app.route("/matrix")
    def connectivity_matrix():
        """Create the connectivity matrix."""
        # Prepare matrix data (or load if using background workers).
        updated, frequency, connectivity, validity = prepare_matrix(app.config)

        if 'raw' in request.args:
            # Only send json data
            return jsonify(
                last_updated=updated, update_frequency=frequency,
                connectivity=connectivity, validity=validity,
            )

        # Compute percentages as well.
        valid, invalid, failure = 0, 0, 0
        for src, dsts in connectivity.items():
            for dst, connected in dsts.items():
                if connected:
                    # We have connectivity, now check if valid.
                    # If validity could not be checked, assume valid.
                    if validity.get(src, {}).get(dst, True):
                        valid += 1
                    else:
                        invalid += 1
                else:
                    failure += 1
        total = valid + invalid + failure
        if total:
            invalid = math.ceil(invalid / total * 100)
            failure = math.ceil(failure / total * 100)
            valid = 100 - invalid - failure

        return render_template(
            'matrix.html',
            connectivity=connectivity, validity=validity,
            valid=valid, invalid=invalid, failure=failure,
            last_updated=updated, update_frequency=frequency,
        )

    #TODO: Move it to the admin side
    @app.route("/bgp-analysis")
    @basic_auth.required
    def bgp_analysis():
        """Return the full BGP analysis report."""
        updated, freq, messages = prepare_bgp_analysis(app.config)
        return render_template(
            "bgp_analysis.html", messages=messages,
            last_updated=updated, update_frequency=freq,
        )

    @app.route("/looking-glass")
    @app.route("/looking-glass/<int:group>")
    @app.route("/looking-glass/<int:group>/<router>")
    def looking_glass(
            group: Optional[int] = None, router: Optional[str] = None):
        """Show the looking glass for group (AS) and router."""
        looking_glass_files = parsers.find_looking_glass_textfiles(
            app.config['LOCATIONS']['groups']
        )
        need_redirect = False

        if (group is None) or (group not in looking_glass_files):
            # Redict to a possible group.
            group = min(looking_glass_files.keys())
            need_redirect = True

        groupdata = looking_glass_files[group]

        if (router is None) or (router not in groupdata):
            # Redirect to first possible router.
            router = next(iter(groupdata))
            need_redirect = True

        if need_redirect:
            return redirect(
                url_for("looking_glass", group=group, router=router))

        # Now get data for group. First the actual looking glass.
        with open(groupdata[router]) as file:
            filecontent = file.read()

        # Next the analysis.
        updated, freq, messages = prepare_bgp_analysis(app.config, asn=group)

        # Prepare template.
        dropdown_groups = list(looking_glass_files.keys())
        dropdown_routers = list(groupdata.keys())
        return render_template(
            "looking_glass.html",
            filecontent=filecontent,
            bgp_hints=messages,
            group=group, router=router,
            dropdown_groups=dropdown_groups, dropdown_routers=dropdown_routers,
            last_updated=updated, update_frequency=freq,
        )

    @app.route("/as-connections")
    @app.route("/as-connections/<int:group>")
    @app.route("/as-connections/<int:group>/<int:othergroup>")
    def as_connections(group: int = None, othergroup: int = None):
        """Show the AS connections, optionally for selected groups only."""
        connections = parsers.parse_public_as_connections(
            app.config['LOCATIONS']['as_connections_public'])
        all_ases = {c[0]["asn"] for c in connections}.union(
            {c[1]["asn"] for c in connections})

        def _check_as(data_a, data_b):
            if ((group is None) or (data_a['asn'] == group)) and \
                    ((othergroup is None) or (data_b['asn'] == othergroup)):
                return True
            return False

        selected_connections = []
        for _a, _b in connections:
            if _check_as(_a, _b):
                selected_connections.append((_a, _b))
            elif _check_as(_b, _a):
                selected_connections.append((_b, _a))

        return render_template(
            "as_connections.html",
            connections=selected_connections,
            group=group,
            othergroup=othergroup,
            # All ASes
            dropdown_groups=all_ases,
            # Only matching ASes for first one.
            dropdown_others={conn[1]['asn'] for conn in selected_connections},
        )

    #############################################
    ########### Admin side ######################
    #############################################

    @app.route("/admin", methods=['GET', 'POST'])
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


        return render_template('admin/login.html', form=form)

    @app.route("/admin/dashboard", methods=["GET"])
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
        return render_template("admin/dashboard.html")

    @app.route("/admin/logout")
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

    pmatrix = Process(
        target=loop,
        args=(prepare_matrix, given_app.config['MATRIX_UPDATE_FREQUENCY'], given_app.config),
        kwargs=dict(worker=True)
    )
    pmatrix.start()
    processes.append(pmatrix)

    pbgp = Process(
        target=loop,
        args=(prepare_bgp_analysis,
              given_app.config['ANALYSIS_UPDATE_FREQUENCY'], given_app.config),
        kwargs=dict(worker=True)
    )
    pbgp.start()
    processes.append(pbgp)

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


def prepare_matrix(config, worker=False):
    """Prepare matrix.

    Without background workers, create it from scratch now.
    With background workers, only read result if `worker=False`, and
    only create result if `worker=True`.
    """
    cache_file = Path(config["MATRIX_CACHE"])
    if config["BACKGROUND_WORKERS"] and not worker:
        try:
            with open(cache_file, 'rb') as file:
                return pickle.load(file)
        except FileNotFoundError:
            return (None, None, {}, {})

    # Load all required files.
    as_data = parsers.parse_as_config(
        config['LOCATIONS']['as_config'],
        router_config_dir=config['LOCATIONS']['config_directory'],
    )
    connection_data = parsers.parse_as_connections(
        config['LOCATIONS']['as_connections']
    )
    looking_glass_data = parsers.parse_looking_glass_json(
        config['LOCATIONS']['groups']
    )
    connectivity_data = parsers.parse_matrix_connectivity(
        config['LOCATIONS']['matrix']
    )

    # Compute results
    connectivity = matrix.check_connectivity(
        as_data, connectivity_data)
    validity = matrix.check_validity(
        as_data, connection_data, looking_glass_data)

    last_updated = dt.utcnow()
    update_frequency = (config["MATRIX_UPDATE_FREQUENCY"]
                        if config["BACKGROUND_WORKERS"] else None)

    results = (last_updated, update_frequency, connectivity, validity)

    if config["BACKGROUND_WORKERS"] and worker:
        os.makedirs(cache_file.parent, exist_ok=True)
        with open(cache_file, "wb") as file:
            pickle.dump(results, file)

    return results


def prepare_bgp_analysis(config, asn=None, worker=False):
    """Prepare matrix.

    Without background workers, create it from scratch now.
    With background workers, only read result if `worker=False`, and
    only create result if `worker=True`.
    """
    db_file = Path(config["ANALYSIS_CACHE"])

    # Don't even load configs, just immediately return results.
    if config["BACKGROUND_WORKERS"] and not worker:
        freq = config['ANALYSIS_UPDATE_FREQUENCY']
        if not db_file.is_file():
            last = None
            msgs = []
        elif asn is not None:
            last, msgs = bgp_policy_analyzer.load_analysis(db_file, asn)
        else:
            last, msgs = bgp_policy_analyzer.load_report(db_file)
        return last, freq, msgs

    # Now we need configs and compute.
    as_data = parsers.parse_as_config(
        config['LOCATIONS']['as_config'],
        router_config_dir=config['LOCATIONS']['config_directory'],
    )
    connection_data = parsers.parse_as_connections(
        config['LOCATIONS']['as_connections']
    )
    looking_glass_data = parsers.parse_looking_glass_json(
        config['LOCATIONS']['groups']
    )

    if config["BACKGROUND_WORKERS"] and worker:
        os.makedirs(db_file.parent, exist_ok=True)
        # Update db, return nothing
        bgp_policy_analyzer.update_db(
            db_file, as_data, connection_data, looking_glass_data)
        return

    # Compute on the fly
    freq = None
    if asn is not None:
        last, msgs = bgp_policy_analyzer.analyze_bgp(
            asn, as_data, connection_data, looking_glass_data)
    else:
        last, msgs = bgp_policy_analyzer.bgp_report(
            as_data, connection_data, looking_glass_data)
    return last, freq, msgs

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
