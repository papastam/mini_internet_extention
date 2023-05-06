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

from flask_login import login_user, login_required, fresh_login_required, LoginManager, logout_user, current_user
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


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),], render_kw={"placeholder": "Username"}, )
    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')
    
def debug(message):
    print("\033[35mDEBUG: " + message + "\033[0m")

def admin_log(message):
    """Log message to admin log."""
    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    with open("/server/admin_server/admin_login.log", "a") as file:
        file.write(time + ' | ' + message+'\n')

def create_admin_server(db_session, config=None):
    """Create and configure the app."""
    debug("Creating admin server. with name "+str(__name__))
    app = Flask(__name__)
    app.config.from_mapping(config_defaults)
    app.jinja_env.undefined = StrictUndefined

    if config is None:
        config = os.environ.get("ADMIN_SERVER_CONFIG", None)

    if config is not None and isinstance(config, dict):
        app.config.from_mapping(config)
    elif config is not None:
        app.config.from_pyfile(config)

    #Admin login init
    login_manager = LoginManager(app)
    login_manager.login_view = '/login'
    login_manager.session_protection = "strong"
    
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

    #Init database
    init_db_base(db_session)

    @app.route("/")
    @fresh_login_required
    def index():
        """Redict to dashboard as starting page."""
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=['GET', 'POST'])
    def admin_login():
        form = LoginForm()
        if form.is_submitted():
            admin_log(f"LOGIN: User {form.username.data} requested login")
            admin_user = db_session.query(db.Admin).filter(db.Admin.username==form.username.data).first()

            if admin_user and bcrypt.check_password_hash(admin_user.password, form.password.data):
                login_user(admin_user)
            
                admin_log(f"LOGIN: User {form.username.data} logged in sucesfully from {request.remote_addr}")
                flash('Logged in successfully.', 'success')
            
                return redirect(url_for('dashboard'))
            
            elif admin_user:
                admin_log(f"LOGIN: User {form.username.data} tried to login with wrong password (from {request.remote_addr})")
                flash('Login unsuccessful. Please check username and password', 'error')
            
            else:
                admin_log(f"LOGIN: Login attemt from invalid user: {form.username.data} (from {request.remote_addr})")
                flash('Login unsuccessful. Please check username and password', 'error')


        return render_template('login.html', form=form)

    @app.route("/dashboard", methods=["GET"])
    @fresh_login_required
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
    @fresh_login_required
    def as_teams():
        teams_dict = {}
        for team in db_session.query(db.AS_teams).all():
            teams_dict[str(team.asn)] = {}
            teams_dict[str(team.asn)]["password"] = team.password
            
            if team.member1 is not None:
                teams_dict[str(team.asn)]["member1"] = {}
                teams_dict[str(team.asn)]["member1"]["id"] = team.member1
                teams_dict[str(team.asn)]["member1"]["name"] = db_session.query(db.Students).get(team.member1).name
            else:
                teams_dict[str(team.asn)]["member1"] = 'None'

            if team.member2 is not None:
                teams_dict[str(team.asn)]["member2"] = {}
                teams_dict[str(team.asn)]["member2"]["id"] = team.member2
                teams_dict[str(team.asn)]["member2"]["name"] = db_session.query(db.Students).get(team.member2).name
            else:
                teams_dict[str(team.asn)]["member2"] = 'None'

            if team.member3 is not None:
                teams_dict[str(team.asn)]["member3"] = {}
                teams_dict[str(team.asn)]["member3"]["id"] = team.member3
                teams_dict[str(team.asn)]["member3"]["name"] = db_session.query(db.Students).get(team.member3).name
            else:
                teams_dict[str(team.asn)]["member3"] = 'None'

            if team.member4 is not None:
                teams_dict[team.asn]["member4"] = {}
                teams_dict[team.asn]["member4"]["id"] = team.member4
                teams_dict[team.asn]["member4"]["name"] = db_session.query(db.Students).get(team.member4).name
            else:
                teams_dict[str(team.asn)]["member4"] = 'None'

        return render_template("as_teams.html", teams=str(teams_dict).replace("'", '"'))

    @app.route("/config")
    @fresh_login_required
    def config():
        return render_template("config.html")

    @app.route("/config/teams", methods=["GET", "POST"])
    @fresh_login_required
    def config_teams():
        if request.method == "POST":
            form_args = dict(request.form)
            debug(f"POST request received: {form_args}")

            if "asn" in form_args:
                team = db_session.query(db.AS_teams).get(form_args["asn"])

                if check_for_dupes(form_args["member1"], form_args["member2"], form_args["member3"], form_args["member4"]):
                    update_students(db_session, team.asn, form_args["member1"], form_args["member2"], form_args["member3"], form_args["member4"])

                    if "password" not in form_args:
                        '''No password change'''
                    elif  form_args["password"] == team.password:
                        '''No need to change password'''
                        pass
                    elif len(form_args["password"]) < 8:
                        '''Password too short'''
                        flash("Password must be at least 8 characters long. Password not updated", "info")
                    else:
                        # Change password in database
                        team.password = form_args["password"]
                        
                        # Change password in docker
                        with open(app.config['LOCATIONS']['docker_pipe'], 'w') as pipe:
                            pipe.write(f"changepass {team.asn} {form_args['password']}\n")
                            pipe.flush()
                            pipe.close()

                    team.member1 = form_args["member1"] if form_args["member1"]!="-1" else None
                    team.member2 = form_args["member2"] if form_args["member2"]!="-1" else None
                    team.member3 = form_args["member3"] if form_args["member3"]!="-1" else None
                    team.member4 = form_args["member4"] if form_args["member4"]!="-1" else None
                    team.active_as = True if form_args["active_as"]=="1" else False

                    db_session.add(team)
                    db_session.commit()

                    flash(f"Team {team.asn} updated successfully.", "success")
                else:
                    flash("Duplicate student detected. Please check your input.", "error")

        configdict = {"teams":[], "students":[]}
        for team in db_session.query(db.AS_teams).all():
            configdict["teams"].append({
                "asn": team.asn,
                "password": team.password,
                "active_as": "true" if team.active_as else "false",
                "members": [team.member1 if team.member1!=None else -1, 
                            team.member2 if team.member2!=None else -1, 
                            team.member3 if team.member3!=None else -1, 
                            team.member4 if team.member4!=None else -1
                            ]
            })

        for student in db_session.query(db.Students).all():
            configdict["students"].append({
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "team": student.team if student.team!=None else -1
            })



        return render_template("config_teams.html", configdict=configdict)

    @app.route("/config/students", methods=["GET", "POST"])
    @fresh_login_required
    def config_students():
        if request.method == "POST" and ("name" in dict(request.form) and "email" in dict(request.form)):
            request_args = dict(request.form)
            debug(f"POST request received: {request_args}")
        
            if "id" in request_args:
                '''Update existing student'''
                student = db_session.query(db.Students).get(request_args["id"])
                student.name    = request_args["name"]
                student.email   = request_args["email"]

                student.P1Q1        = request_args["p1q1"] if "p1q1" in request_args else None
                student.P1Q2        = request_args["p1q2"] if "p1q2" in request_args else None
                student.P1Q3        = request_args["p1q3"] if "p1q3" in request_args else None
                student.P1Q4        = request_args["p1q4"] if "p1q4" in request_args else None
                student.P1Q5        = request_args["p1q5"] if "p1q5" in request_args else None
                student.midterm1    = request_args["midterm1"] if "midterm1" in request_args else None

                student.P2Q1        = request_args["p2q1"] if "p2q1" in request_args else None
                student.P2Q2        = request_args["p2q2"] if "p2q2" in request_args else None
                student.P2Q3        = request_args["p2q3"] if "p2q3" in request_args else None
                student.P2Q4        = request_args["p2q4"] if "p2q4" in request_args else None
                student.P2Q5        = request_args["p2q5"] if "p2q5" in request_args else None
                student.midterm2    = request_args["midterm2"] if "midterm2" in request_args else None

                db_session.add(student)
                db_session.commit()
                flash(f"Student {request_args['name']} updated successfully.", "success")

            else:
                '''Add new student'''
                
                # TODO: Check for duplicate students
                student = db.Students(name=request_args["name"], email=request_args["email"])
                db_session.add(student)
                db_session.commit()
                flash(f"Student {request_args['name']} added successfully.", "success")
                    
        configdict = {"teams":[], "students":[]}
        
        for student in db_session.query(db.Students).all():
            configdict["students"].append({
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "team": student.team if student.team!=None else -1,
                "grades": {
                    "p1q1": student.P1Q1,
                    "p1q2": student.P1Q2,
                    "p1q3": student.P1Q3,
                    "p1q4": student.P1Q4,
                    "p1q5": student.P1Q5,
                    "midterm1": student.midterm1,
                    "p2q1": student.P2Q1,
                    "p2q2": student.P2Q2,
                    "p2q3": student.P2Q3,
                    "p2q4": student.P2Q4,
                    "p2q5": student.P2Q5,
                    "midterm2": student.midterm2,
                }
            })

        return render_template("config_students.html", configdict=configdict)

    @app.route("/config/rendezvous", methods=["GET", "POST"])
    @fresh_login_required
    def config_rendezvous():
        return render_template("config_rendezvous.html")

    @app.route("/logout")
    @fresh_login_required
    def logout():
        admin_log(f"LOGOUT: User {current_user.username} logged out")
        logout_user()
        flash('Logged out successfully.', 'info')
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

def check_for_dupes(member1, member2, member3, member4):
    """Check for duplicate students"""
    if member1 != "-1":
        if member1 == member2 or member1 == member3 or member1 == member4:
            return False
    if member2 != "-1":
        if member2 == member3 or member2 == member4:
            return False
    if member3 != "-1":
        if member3 == member4:
            return False
    return True

def update_students(db_session, team, member1, member2, member3, member4):
    """First up, remove all students from the team"""
    for student in db_session.query(db.Students).filter(db.Students.team == team).all():
        student.team = None
        db_session.add(student)
        db_session.commit()

    """Then, add the new ones"""
    if member1 != "-1":
        student = db_session.query(db.Students).filter(db.Students.id == member1).first()
        student.team = team
        db_session.add(student)
        db_session.commit()
    if member2 != "-1":
        student = db_session.query(db.Students).filter(db.Students.id == member2).first()
        student.team = team
        db_session.add(student)
        db_session.commit()
    if member3 != "-1":
        student = db_session.query(db.Students).filter(db.Students.id == member3).first()
        student.team = team
        db_session.add(student)
        db_session.commit()
    if member4 != "-1":
        student = db_session.query(db.Students).filter(db.Students.id == member4).first()
        student.team = team
        db_session.add(student)
        db_session.commit()

def init_db_base(db_session):
    """Create sample tables"""
    # Create sample students from dict.
    students = {1: {"name": "Chris Papastamos", "email": "csd4569@csd.uoc.gr", "team": 1}, 
                2: {"name": "Dimitris Bisias", "email": "csd1111@csd.uoc.gr", "team": 1}, 
                3: {"name": "Orestis Chiotakis", "email": "csd2222@csd.uoc.gr", "team": 2}, 
                4: {"name": "Manousos Manouselis", "email": "csd3333@csd.uoc.gr", "team": 2}, 
                5: {"name": "Test Student" , "email": "teststudent@provider.com", "team": 2},
                6: {"name": "Unassigned Student" , "email": "unassigned@provider.com", "team": None},
                }

    for student_id, info in students.items():
        new_student = db.Students(id=student_id, name=info["name"], email=info["email"], team=info["team"] if "team" in info else None)
        db_session.add(new_student)
        db_session.commit()
    
    team1 = db_session.query(db.AS_teams).get(1)
    team1.member1 = 1
    team1.member2 = 2
    team1.active_as = True
    db_session.add(team1)
    
    team2 = db_session.query(db.AS_teams).get(2)
    team2.member1 = 3
    team2.member2 = 4
    team2.member3 = 5
    db_session.add(team2)
    

    db_session.commit()