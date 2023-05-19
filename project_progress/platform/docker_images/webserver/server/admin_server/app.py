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
from datetime import datetime, timedelta
import database as db
import psutil

from utils import admin_log, debug, check_for_dupes, update_students, date_to_dict, detect_rend_collision


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

admin_users = {'papastam': 'admin'}

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),], render_kw={"placeholder": "Username"}, )
    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

def create_admin_server(db_session, config=None, build=False):
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

    app.config.update(
        DEBUG=True
    )


    #Admin login init
    login_manager = LoginManager(app)
    login_manager.login_view = '/login'
    login_manager.session_protection = "strong"
    
    bcrypt = Bcrypt(app) 

    if build:
        db.create_admin_login(db_session, admin_users, bcrypt)

    @login_manager.user_loader
    def load_user(user_id):
        return db_session.query(db.Admin).get(int(user_id))

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
        teams_list = []
        for team in db_session.query(db.AS_team).filter(db.AS_team.is_authenticated==True).all():

            teams_list.append({
                "asn": team.asn,
                "password": team.password,
                "member1": db_session.query(db.Student).get(team.member1).name if team.member1 else None,
                "member2": db_session.query(db.Student).get(team.member2).name if team.member2 else None,
                "member3": db_session.query(db.Student).get(team.member3).name if team.member3 else None,
                "member4": db_session.query(db.Student).get(team.member4).name if team.member4 else None,
            })
            
        return render_template("as_teams.html", teams=teams_list)

    @app.route("/config")
    @fresh_login_required
    def config():
        return redirect(url_for("config_teams"))

    @app.route("/config/teams", methods=["GET", "POST"])
    @fresh_login_required
    def config_teams():
        if request.method == "POST":
            form_args = dict(request.form)

            try:
                if "asn" in form_args:
                    team = db_session.query(db.AS_team).get(form_args["asn"])
                    if ("clear" in form_args) and (form_args["clear"]=="1"):
                        '''Clear and deactivate the team'''
                        for student in [team.member1, team.member2, team.member3, team.member4]:
                            if student:
                                student = db_session.query(db.Student).get(student)
                                student.team = None
                                db_session.add(student)
                        
                        team.member1 = None
                        team.member2 = None
                        team.member3 = None
                        team.member4 = None
                        team.is_authenticated = False    

                        '''Clear the team's rendezvous'''
                        for rend in db_session.query(db.Rendezvous).filter(db.Rendezvous.team==team.asn).all():
                            rend.team = None
                            db_session.add(rend)
                        
                        flash(f"Team {team.asn} cleared", "info")

                        db_session.add(team)
                        db_session.commit()
                    elif check_for_dupes(form_args["member1"], form_args["member2"], form_args["member3"], form_args["member4"]):
                        update_students(db_session, team.asn, form_args["member1"], form_args["member2"], form_args["member3"], form_args["member4"])

                        if ("password" not in form_args) or (form_args["password"] == ""):
                            '''No password change'''
                        elif  form_args["password"] == team.password:
                            '''No need to change password'''
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

                        '''Check if team is active'''
                        if (form_args["member1"] == "-1") and (form_args["member2"] == "-1") and (form_args["member3"] == "-1") and (form_args["member4"] == "-1"):
                            '''No active members'''
                            team.is_authenticated = False
                            team.member1 = team.member2 = team.member3 = team.member4 = None
                            flash(f"Team {team.asn} is now inactive because no members were specified.", "info")
                        else:
                            '''Team is active'''
                            team.is_authenticated = True if form_args["active_as"]=="1" else False

                            '''Save to database'''
                            team.member1 = form_args["member1"] if form_args["member1"]!="-1" else None
                            team.member2 = form_args["member2"] if form_args["member2"]!="-1" else None
                            team.member3 = form_args["member3"] if form_args["member3"]!="-1" else None
                            team.member4 = form_args["member4"] if form_args["member4"]!="-1" else None
                            
                            '''Rearange members if needed'''
                            if not team.member1:
                                team.member1 = team.member2
                                team.member2 = team.member3
                                team.member3 = team.member4
                                team.member4 = None
                            if not team.member2:
                                team.member2 = team.member3
                                team.member3 = team.member4
                                team.member4 = None
                            if not team.member3:
                                team.member3 = team.member4
                                team.member4 = None


                            flash(f"Team {team.asn} updated successfully.", "success")

                        db_session.add(team)
                        db_session.commit()
                    else:
                        flash("Duplicate student detected. Please check your input.", "error")
            except Exception as e:
                flash(f"Error: {e}", "error")
                db_session.rollback()

        teams_list = []
        students_list = []

        for team in db_session.query(db.AS_team).all():
            teams_list.append({
                "asn": team.asn,
                "password": team.password,
                "active_as": "true" if team.is_authenticated else "false",
                "members": [team.member1 if team.member1!=None else -1, 
                            team.member2 if team.member2!=None else -1, 
                            team.member3 if team.member3!=None else -1, 
                            team.member4 if team.member4!=None else -1
                            ]
            })

        for student in db_session.query(db.Student).all():
            students_list.append({
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "team": student.team if student.team!=None else -1
            })

        return render_template("config_teams.html", teams=teams_list, students=students_list)

    @app.route("/config/students", methods=["GET", "POST"])
    @fresh_login_required
    def config_students():
        if request.method == "POST" and ("name" in dict(request.form) and "email" in dict(request.form)):
            request_args = dict(request.form)
            debug(f"POST request received: {request_args}")

            try:        
                if len(request_args["name"].split(" ")) < 2:
                    flash("Please enter the student's full name (at least 2 words).", "error")
                elif "id" in request_args:
                    '''Update existing student'''
                    faulty_input = False

                    student = db_session.query(db.Student).get(request_args["id"])
                    student.name    = request_args["name"]
                    student.email   = request_args["email"]

                    for grade in ["p1q1", "p1q2", "p1q3", "p1q4", "p1q5", "midterm1", "p2q1", "p2q2", "p2q3", "p2q4", "p2q5", "midterm2"]:
                        if (grade not in request_args) or (request_args[grade] == "") :
                            request_args[grade] = None
                        elif not request_args[grade].isdigit():
                            flash("Please enter a valid grade.", "error")
                            faulty_input = True
                            break
                        elif int(request_args[grade]) < 0 or int(request_args[grade]) > 10:
                            flash("Please enter a valid grade.", "error")
                            faulty_input = True
                            break
                        

                    if not faulty_input:
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

                        flash(f"Student {request_args['name']} updated successfully.", "success")

                    db_session.add(student)
                    db_session.commit()
                else:
                    '''Add new student'''
                    if db_session.query(db.Student).filter(db.Student.name==request_args["name"]).first():
                        flash(f"Student with name: {request_args['name']} already exists.", "error")
                    else:
                        student = db.Student(name=request_args["name"], email=request_args["email"] if request_args["email"]!="" else None)
                        db_session.add(student)
                        db_session.commit()
                        flash(f"Student {request_args['name']} added successfully.", "success")

            except Exception as e:
                flash(f"Error: {e}", "error")
                db_session.rollback()
                
        '''Create liststs and render frontend template'''
        students = []
        
        for student in db_session.query(db.Student).all():
            students.append({
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

        return render_template("config_students.html", students=students)

    @app.route("/config/rendezvous", methods=["GET", "POST"])
    @fresh_login_required
    def config_rendezvous():    
        if (request.method == "POST") and ("type" in dict(request.form)):
            request_args = dict(request.form)
            debug(f"POST request received: {request_args}")
            
            try:
                if request_args["type"] == "new-period":
                    '''Add new period'''
                    if db_session.query(db.Period).filter(db.Period.name==request_args["name"]).first():
                        flash(f"Period with name: {request_args['name']} already exists.", "error")
                    else:
                        period = db.Period(name=request_args["name"])
                        db_session.add(period)
                        flash(f"Period {request_args['name']} added successfully.", "success")
                elif request_args["type"] == "edit-period":
                    '''Edit existing period'''
                    period = db_session.query(db.Period).get(request_args["id"])
                                    
                    if "delete" in request_args:
                        if "name" not in request_args:
                            flash("Index \"name\" not found in the post request.", "error") 
                        count=0
                        for rendezvous in db_session.query(db.Rendezvous).filter(db.Rendezvous.period==period.id).all():
                            db_session.delete(rendezvous)
                            count+=1
                        if count>0:
                            flash(f"Deleted {count} rendezvous because of the period deletion.", "success")
                        
                        db_session.delete(period)
                        flash(f"Period \"{request_args['name']}\" deleted successfully.", "success")
                    
                    else:
                        '''Faulty input check'''
                        if "name" not in request_args:
                            flash("Index \"name\" not found in the post request.", "error")
                        elif "live" not in request_args:
                            flash("Index \"live\" not found in the post request.", "error")
                        elif request_args["name"] == "":
                            flash("Period name cannot be empty.", "error")
                        else:
                            period_with_name = db_session.query(db.Period).filter(db.Period.name==request_args["name"]).first()
                            if period_with_name and (period_with_name.id != period.id):
                                flash(f"Period with name: {request_args['name']} already exists.", "error")
                            else:
                                period.live     = request_args["live"]=="1"
                                period.name     = request_args["name"]
                                db_session.add(period)
                                flash(f"Period \"{request_args['name']}\" updated successfully.", "success")

                elif request_args["type"] == "new-rendezvous":
                    '''Handle faulty input cases'''
                    if "period" not in request_args:
                        flash("Index \"period\" not found in the post request.", "error")
                    elif "start" not in request_args:
                        flash("Index \"start\" not found in the post request.", "error")
                    elif "duration" not in request_args:
                        flash("Index \"duration\" not found in the post request.", "error")
                    elif datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M") < datetime.now():
                        flash(f"Rendezvous start time: {request_args['start']} is in the past.", "error")
                    elif int(request_args["duration"]) < 1:
                        flash(f"Rendezvous duration: {request_args['duration']} is less than 1 minute.", "error")
                    elif detect_rend_collision(db_session,datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M"),int(request_args["duration"]),int(request_args["period"])):
                        flash(f"Rendezvous for period: {db_session.query(db.Period).filter(db.Period.id==request_args['period']).first().name} and start: {request_args['start']} already exists.", "error")
                    else:
                        '''Add new rendezvous'''
                        rendezvous = db.Rendezvous(period=request_args["period"], datetime=datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M"), duration=request_args["duration"])
                        db_session.add(rendezvous)
                        flash(f"Rendezvous added successfully.", "success")

                elif request_args["type"] == "new-rendezvous-range":
                    '''Handle faulty input cases'''
                    if "period" not in request_args:
                        flash("Index \"period\" not found in the post request.", "error")
                    elif "start" not in request_args:
                        flash("Index \"start\" not found in the post request.", "error")
                    elif "end" not in request_args:
                        flash("Index \"end\" not found in the post request.", "error")
                    elif "duration" not in request_args:
                        flash("Index \"duration\" not found in the post request.", "error")
                    elif datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M") < datetime.now():
                        flash(f"Rendezvous start time: {request_args['start']} is in the past.", "error")
                    elif datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M") > datetime.strptime(request_args["end"],"%Y-%m-%dT%H:%M"):
                        flash(f"Rendezvous start time: {request_args['start']} is after end time: {request_args['end']}.", "error")
                    elif int(request_args["duration"]) < 1:
                        flash(f"Rendezvous duration: {request_args['duration']} is less than 1 minute.", "error")
                    else:
                        '''Add new rendezvous range'''
                        period = db_session.query(db.Period).get(request_args["period"])
                        start = datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M")
                        end = datetime.strptime(request_args["end"],"%Y-%m-%dT%H:%M")
                        duration = int(request_args["duration"])
                        count=0
                        collisions=False
                        while start < end:
                            if detect_rend_collision(db_session, start, duration, period.id):
                                start += timedelta(minutes=duration)
                                collisions=True
                                continue    
                            count+=1
                            rendezvous = db.Rendezvous(period=period.id, datetime=start, duration=duration)
                            db_session.add(rendezvous)
                            start += timedelta(minutes=duration)

                        flash(f"Added {count} rendezvous successfully.", "success")
                        if collisions:
                            flash(f"Some rendezvous were not added because of datetime collisions.", "info")
                elif request_args["type"] == "edit-rendezvous":
                    '''Handle faulty input cases'''
                    if "id" not in request_args:
                        flash("Index \"id\" not found in the post request.", "error")
                    elif "start" not in request_args:
                        flash("Index \"start\" not found in the post request.", "error")
                    elif "duration" not in request_args:
                        flash("Index \"duration\" not found in the post request.", "error")
                    elif datetime.strptime(request_args["start"],"%Y-%m-%dT%H:%M") < datetime.now():
                        flash(f"Rendezvous start time: {request_args['start']} is in the past.", "error")
                    elif int(request_args["duration"]) < 1:
                        flash(f"Rendezvous duration: {request_args['duration']} is less than 1 minute.", "error")
                    else:
                        '''Edit existing rendezvous'''
                        rendezvous = db_session.query(db.Rendezvous).get(request_args["id"])
                        if "delete" in request_args:
                            db_session.delete(rendezvous)
                            flash(f"Rendezvous deleted successfully.", "success")
                        else:
                            if "team" not in request_args:
                                flash("Index \"team\" not found in the post request.", "error")
                            else:
                                rendezvous.team     = request_args["team"]
                                db_session.add(rendezvous)
                                flash(f"Rendezvous updated successfully.", "success")

                db_session.commit()
            except Exception as e: 
                debug(f"DATABASE ERROR: {e.with_traceback}")
                flash(f"Error: {e}", "error")
                db_session.rollback()

        '''Create liststs and render frontend template'''
        periods_list = []
        for period in db_session.query(db.Period).all():
            periods_list.append({
                "id": period.id,
                "name": period.name,
                "live": 1 if period.live else 0
            })

        rendezvous_list = []
        for rendezvous in db_session.query(db.Rendezvous).all():
            rendezvous_list.append({
                "id"        : rendezvous.id,
                "period"    : rendezvous.period,
                "datetime"  : date_to_dict(rendezvous.datetime),
                "duration"  : rendezvous.duration,
                "team"      : rendezvous.team if rendezvous.team!=None else -1
            })

        teams_list = []
        for team in db_session.query(db.AS_team).all():
            teams_list.append({
                "asn": team.asn,
                "active_as": 1 if team.is_authenticated else 0,
                "member1": team.member1 if team.member1!=None else -1,
                "member2": team.member2 if team.member2!=None else -1,
                "member3": team.member3 if team.member3!=None else -1,
                "member4": team.member4 if team.member4!=None else -1
            })

        students_list = []
        for student in db_session.query(db.Student).all():
            students_list.append({
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "team": student.team if student.team!=None else -1,
            })

        return render_template("config_rendezvous.html", periods=periods_list, rendezvous_list=rendezvous_list, teams=teams_list, students=students_list)

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
            try:
                sleep(remaining_secs)
            except KeyboardInterrupt:
                print(f"\033[32mStopping worker `{function.__name__}`.\033[00m")
                exit()

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
        print("\033[34mMeasured stats \033[03m(%s)\033[00m" % str(time))

    return (time, cpu, memory, disk)