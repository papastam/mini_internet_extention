from time import strftime, gmtime
from datetime import datetime

import database as db
import datetime as dt

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
                1: {"id": 1, "name": "Phase 1", "live": True},
                2: {"id": 2, "name": "Phase 2", "live": True},
                3: {"id": 3, "name": "Phase 3", "live": True},
                }
    
    for period_id, info in periods.items():
        new_period = db.Period(id=period_id, name=info["name"], live=info["live"])
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