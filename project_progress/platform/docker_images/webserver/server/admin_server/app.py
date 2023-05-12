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
    create_test_db_snapshot(db_session)

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
        for team in db_session.query(db.AS_team).all():
            if not team.active_as:
                continue

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
            debug(f"POST request received: {form_args}")

            if "asn" in form_args:
                team = db_session.query(db.AS_team).get(form_args["asn"])

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

        teams_list = []
        students_list = []

        for team in db_session.query(db.AS_team).all():
            teams_list.append({
                "asn": team.asn,
                "password": team.password,
                "active_as": "true" if team.active_as else "false",
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
        
            if "id" in request_args:
                '''Update existing student'''
                student = db_session.query(db.Student).get(request_args["id"])
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
                student = db.Student(name=request_args["name"], email=request_args["email"])
                db_session.add(student)
                db_session.commit()
                flash(f"Student {request_args['name']} added successfully.", "success")
                
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
            if request_args["type"] == "new-period":
                '''Add new period'''
                # TODO: checks
                period = db.Period(name=request_args["name"], start=datetime.strptime(request_args["start"],"%Y-%d-%m"), end=datetime.strptime(request_args["end"],"%Y-%d-%m"))
                db_session.add(period)
                db_session.commit()
                flash(f"Period {request_args['name']} added successfully.", "success")
            elif request_args["type"] == "edit-period":
                '''Edit existing period'''
                period = db_session.query(db.Period).get(request_args["id"])
                                
                if "delete" in request_args:
                    count=0
                    for rendezvous in db_session.query(db.Rendezvous).filter(db.Rendezvous.period==period.id).all():
                        db_session.delete(rendezvous)
                        count+=1
                    flash(f"Deleted {count} rendezvous because of the period deletion.", "success")
                    
                    db_session.delete(period)
                    flash(f"Period \"{request_args['name']}\" deleted successfully.", "success")
                
                else:
                    period.name     = request_args["name"]
                    if request_args["start"] != "":
                        period.start    = datetime.strptime(request_args["start"],"%Y-%d-%m")
                    if request_args["end"] != "":
                        period.end      = datetime.strptime(request_args["end"],"%Y-%d-%m")

                    db_session.add(period)
                    flash(f"Period \"{request_args['name']}\" updated successfully.", "success")

                # TODO: checks
                db_session.commit()

            elif request_args["type"] == "new-rendezvous":
                '''Add new rendezvous'''
                rendezvous = db.Rendezvous(period=request_args["period"], datetime=datetime.strptime(request_args["start"],"%Y-%d-%mT%H:%M"), duration=request_args["duration"])
                db_session.add(rendezvous)
                db_session.commit()
                flash(f"Rendezvous added successfully.", "success")

            elif request_args["type"] == "new-rendezvous-range":
                '''Add new rendezvous range'''
                period = db_session.query(db.Period).get(request_args["period"])
                start = datetime.strptime(request_args["start"],"%Y-%d-%mT%H:%M")
                end = datetime.strptime(request_args["end"],"%Y-%d-%mT%H:%M")
                duration = int(request_args["duration"])
                count=0
                while start < end:
                    count+=1
                    rendezvous = db.Rendezvous(period=period.id, datetime=start, duration=duration)
                    db_session.add(rendezvous)
                    start += timedelta(minutes=duration)
                
                db_session.commit()
                flash(f"Added {count} rendezvous successfully.", "success")

            elif request_args["type"] == "edit-rendezvous":
                '''Edit existing rendezvous'''
                rendezvous = db_session.query(db.Rendezvous).get(request_args["id"])
                if "delete" in request_args:
                    db_session.delete(rendezvous)
                    flash(f"Rendezvous deleted successfully.", "success")
                else:
                    rendezvous.team     = request_args["team"]
                    db_session.add(rendezvous)
                    flash(f"Rendezvous updated successfully.", "success")

                db_session.commit()

        periods_list = []
        for period in db_session.query(db.Period).all():
            periods_list.append({
                "id": period.id,
                "name": period.name,
                "start": date_to_dict(period.start),
                "end": date_to_dict(period.end)
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
                "is_active": 1 if team.is_active else 0,
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
    for student in db_session.query(db.Student).filter(db.Student.team == team).all():
        student.team = None
        db_session.add(student)
        db_session.commit()

    """Then, add the new ones"""
    membersarr=[member1, member2, member3, member4]
    for member in membersarr:
        if member != "-1":
            student = db_session.query(db.Student).filter(db.Student.id == member).first()
            student.team = team
            db_session.add(student)
    
    db_session.commit()

def create_test_db_snapshot(db_session):
    """Create sample tables"""
    # Create sample students from dict.
    students =  {
                1: {"name": "Chris Papastamos", "email": "csd4569@csd.uoc.gr", "team": 1}, 
                2: {"name": "Dimitris Bisias", "email": "csd1111@csd.uoc.gr", "team": 1}, 
                3: {"name": "Orestis Chiotakis", "email": "csd2222@csd.uoc.gr", "team": 2}, 
                4: {"name": "Manousos Manouselis", "email": "csd3333@csd.uoc.gr", "team": 2}, 
                5: {"name": "Test Student" , "email": "teststudent@provider.com", "team": 2},
                6: {"name": "Unassigned Student" , "email": "unassigned@provider.com", "team": None},
                }

    for student_id, info in students.items():
        new_student = db.Student(id=student_id, name=info["name"], email=info["email"], team=info["team"] if "team" in info else None)
        db_session.add(new_student)
        db_session.commit()
    
    team1 = db_session.query(db.AS_team).get(1)
    team1.member1 = 1
    team1.member2 = 2
    team1.active_as = True
    db_session.add(team1)
    
    team2 = db_session.query(db.AS_team).get(2)
    team2.member1 = 3
    team2.member2 = 4
    team2.member3 = 5
    db_session.add(team2)

    db_session.commit()

    periods =   {
                1: {"id": 1, "name": "Phase 1", "start": datetime(year=2023,month=2,day=1,hour=12), "end": datetime(year=2023,month=2,day=2,hour=12)},
                2: {"id": 2, "name": "Phase 2", "start": datetime(year=2023,month=6,day=1,hour=12), "end": datetime(year=2023,month=6,day=15,hour=12)},
                3: {"id": 3, "name": "Phase 3", "start": datetime(year=2023,month=7,day=1,hour=12), "end": datetime(year=2023,month=7,day=15,hour=12)},
                }
    
    for period_id, info in periods.items():
        new_period = db.Period(id=period_id, name=info["name"], start=info["start"], end=info["end"])
        db_session.add(new_period)
        db_session.commit()

    rendezvous =    {
                    1: {"id": 1, "datetime": datetime(year=2023,month=5,day=1,hour=12),"period": 1, "duration": 60, "team": 1},
                    2: {"id": 2, "datetime": datetime(year=2023,month=5,day=2,hour=13),"period": 1, "duration": 60, "team": 2},
                    3: {"id": 3, "datetime": datetime(year=2023,month=5,day=3,hour=14),"period": 1, "duration": 60},
                    4: {"id": 4, "datetime": datetime(year=2023,month=6,day=4,hour=15),"period": 2, "duration": 60, "team": 2},
                    5: {"id": 5, "datetime": datetime(year=2023,month=6,day=5,hour=16),"period": 2, "duration": 60},
                    6: {"id": 6, "datetime": datetime(year=2023,month=6,day=6,hour=17),"period": 2, "duration": 60},
                    7: {"id": 7, "datetime": datetime(year=2023,month=7,day=7,hour=18),"period": 3, "duration": 60, "team": 1},
                    8: {"id": 8, "datetime": datetime(year=2023,month=7,day=8,hour=19),"period": 3, "duration": 60, "team": 2},
                    9: {"id": 9, "datetime": datetime(year=2023,month=7,day=9,hour=20),"period": 3, "duration": 60},
                    }

    for rendezvous_id, info in rendezvous.items():
        new_rendezvous = db.Rendezvous(id=rendezvous_id, datetime=info["datetime"], period=info["period"], duration=info["duration"], team=info["team"] if "team" in info else None)
        db_session.add(new_rendezvous)
        db_session.commit()    

def date_to_dict(date):
    """Convert datetime object to dict."""
    return {
        "year": date.strftime("%Y"),
        "month": date.strftime("%b"),
        "day": date.strftime("%d"),
        "day_str": date.strftime("%a"),
        "hour": date.strftime("%H"),
        "minute": date.strftime("%M"),
        "date": date.strftime("%Y-%m-%d"),
        "time": date.strftime("%H:%M"),
        "past": 1 if date < dt.utcnow() else 0,
        "actual": str(date)
    }