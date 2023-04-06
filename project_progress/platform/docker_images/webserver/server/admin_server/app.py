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

from flask_login import login_user, login_required, LoginManager, logout_user, current_user
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt
from datetime import datetime
import database as db
import psutil


# CAUTION: These default values are overwritten by the config file.
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
    'AUTO_START_WORKERS': True
}

admin_users= {
    "papastam": "admin"
}   

# db = SQLAlchemy()

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),], render_kw={"placeholder": "Username"}, )
    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')
    

def debug(message):
    print("\033[35mDEBUG: " + message + "\033[0m")

def admin_log(message):
    """Log message to admin log."""
    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    with open("/server/routing_project_server/admin_login.log", "a") as file:
        file.write(time + ' | ' + message+'\n')

def create_admin_server(db_session, config=None):
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
    login_manager = LoginManager()
    login_manager.login_view = '/login'
    login_manager.init_app(app)
    bcrypt = Bcrypt(app) 

    @login_manager.user_loader
    def load_user(user_id):
        return db_session.query(db.Admin).get(int(user_id))


    #Add admin users
    for user, password in admin_users.items():
        new_user = db.Admin(username=user, password=bcrypt.generate_password_hash(password).decode('utf-8'))
        db_session.add(new_user)
        db_session.commit()
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
        form = LoginForm()
        if form.is_submitted():
            admin_log(f"LOGIN: User {form.username.data} requested login")
            admin_user = db_session.query(db.Admin).filter(db.Admin.username==form.username.data).first()
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

            res = db_session.query(db.Measurement).filter(db.Measurement.time.between(start_datetime, end_datetime)).all()

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

    @app.route("/as_teams")
    @login_required
    def as_teams():
        pass

    @app.route("/teams_config")
    @login_required
    def teams_config():
        pass

    @app.route("/logout")
    @login_required
    def logout():
        admin_log(f"LOGOUT: User {current_user.username} logged out")
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('admin_login'))

    # Start workers if configured.
    if app.config["BACKGROUND_WORKERS"] and app.config['AUTO_START_WORKERS']:
        start_workers(app, db_session)

    return app

# Worker functions.
# =================

def start_workers(given_app,app_db_session=None):
    """Create background processes"""
    processes = []

    stats = Process(
        target=loop,
        args=(measure_stats,
              given_app.config['STATS_UPDATE_FREQUENCY'], given_app.config, given_app, app_db_session),
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

def measure_stats(config, app, db_session, worker=False):

    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory()[2]
    disk = psutil.disk_usage('/')[3]

    #Add admin users
    # for user, password in admin_users.items():
    with app.app_context():
        new_measurement = db.Measurement(cpu=cpu, memory=memory, disk=disk)
        db_session.add(new_measurement)
        db_session.commit()
        print("\033[93mMeasured stats \033[03m(%s)\033[00m" % str(time))

    return (time, cpu, memory, disk)
