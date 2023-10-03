from time import strftime, gmtime
from datetime import datetime as dt
from datetime import timedelta
import os

import database as db

def info(message):
    print("\033[43mINFO: " + str(message) + "\033[0m")

def debug(message):
    print("\033[35mDEBUG: " + str(message) + "\033[0m")

def warrning(message):
    print("\033[93mWARRNING: " + str(message) + "\033[0m")

def error(message):
    print("\033[31mERROR: " + str(message) + "\033[0m")

def as_log(message):
    """Log message to admin log."""
    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    with open("/server/routing_project_server/as.log", "a") as file:
        file.write(time + ' | ' + message+'\n')

def admin_log(message):
    """Log message to admin log."""
    time = strftime("%d-%m-%y %H:%M:%S", gmtime())
    with open("/server/admin_server/admin_login.log", "a") as file:
        file.write(time + ' | ' + message+'\n')

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

def reset_files():
    # Check if the database exists and if not create it
    if not os.path.isfile("/server/database/database.db"):
        open("/server/database/database.db", 'w+').close()
    else:
        # Clear the database
        with open("/server/database/database.db",'r+') as file:
            file.truncate(0)

    #Clear the log files if they exist
    if os.path.isfile("/server/routing_project_server/as.log"):
        with open("/server/routing_project_server/as.log",'r+') as file:
            file.truncate(0)    
    if os.path.isfile("/server/admin_server/admin_login.log"):
        with open("/server/admin_server/admin_login.log",'r+') as file:
            file.truncate(0)

def detect_rend_collision(db_session,date,duration,period):
    """Check if the new rendezvous collides with an existing one."""
    rends = db_session.query(db.Rendezvous).filter(db.Rendezvous.period==period).all()
    for rend in rends:
        if rend.datetime == date:
            return True
        if rend.datetime < date and rend.datetime + timedelta(minutes=rend.duration) > date:
            return True
        if rend.datetime > date and rend.datetime < date + timedelta(minutes=duration):
            return True
    return False

def change_pass(db_session, pipe_name, asn, newpass):
    '''Faulty input checks'''
    if not asn or not newpass:
        raise ValueError("Invalid input")
    elif ' ' in newpass:
        raise ValueError("New password contains spaces")
    elif '    ' in newpass:
        raise ValueError("New password contains tabs")
    elif '\n' in newpass:
        raise ValueError("New password contains newlines")
    elif '\t' in newpass:
        raise ValueError("New password contains tabs")
    elif len(newpass) < 8:
        raise ValueError("New password is too short")
    else:
        """Change password of a student."""
        with open(pipe_name, 'w') as pipe:
            pipe.write(f"changepass {asn} {newpass}\n")
            pipe.flush()
            pipe.close()

        # Change password in database
        as_team = db_session.query(db.AS_team).filter(db.AS_team.asn == asn).first()
        as_team.password = newpass