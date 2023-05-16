import database as db
import os
from utils import *

def create_as_login(db_session, as_pass_file):

    as_cridentials = parsers.parse_as_passwords(as_pass_file)
    if not as_cridentials:
        error("AS login info was not loaded. AS Teams Login will not be available.")

    #Add admin users
    for asn, password in as_cridentials.items():
        if db_session.query(db.AS_team).filter_by(asn=asn).first():
            continue
        new_user = db.AS_team(asn=asn, password=password)
        db_session.add(new_user)
    db_session.commit()

def create_admin_login(db_session, admin_users, bcrypt):
    for user, password in admin_users.items():
        new_user = db.Admin(username=user, password=bcrypt.generate_password_hash(password).decode('utf-8'))
        db_session.add(new_user)
        db_session.commit()
        admin_log("INIT: Added user: " + user)

def create_as_accounts(app, db_session):
    as_cridentials = parsers.parse_as_passwords(app.config['LOCATIONS']['as_passwords'])
    if not as_cridentials:
        error("AS login info was not loaded. AS Teams Login will not be available.")

    #Add admin users
    for asn, password in as_cridentials.items():
        new_user = db.AS_team(asn=asn, password=password)
        db_session.add(new_user)

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
    team1.is_authenticated = True
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
                    1: {"id": 1, "datetime": dt(year=2023,month=5,day=1,hour=12),"period": 1, "duration": 60, "team": 1},
                    2: {"id": 2, "datetime": dt(year=2023,month=5,day=2,hour=13),"period": 1, "duration": 60, "team": 2},
                    3: {"id": 3, "datetime": dt(year=2023,month=5,day=3,hour=14),"period": 1, "duration": 60},
                    4: {"id": 4, "datetime": dt(year=2023,month=6,day=4,hour=15),"period": 2, "duration": 60, "team": 2},
                    5: {"id": 5, "datetime": dt(year=2023,month=6,day=5,hour=16),"period": 2, "duration": 60},
                    6: {"id": 6, "datetime": dt(year=2023,month=6,day=6,hour=17),"period": 2, "duration": 60},
                    7: {"id": 7, "datetime": dt(year=2023,month=7,day=7,hour=18),"period": 3, "duration": 60, "team": 1},
                    8: {"id": 8, "datetime": dt(year=2023,month=7,day=8,hour=19),"period": 3, "duration": 60, "team": 2},
                    9: {"id": 9, "datetime": dt(year=2023,month=7,day=9,hour=20),"period": 3, "duration": 60},
                    }

    for rendezvous_id, info in rendezvous.items():
        new_rendezvous = db.Rendezvous(id=rendezvous_id, datetime=info["datetime"], period=info["period"], duration=info["duration"], team=info["team"] if "team" in info else None)
        db_session.add(new_rendezvous)
        db_session.commit()    