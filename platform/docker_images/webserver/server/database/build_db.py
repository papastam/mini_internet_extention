import database as db
import os
import random
import datetime
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
    
    # team2 = db_session.query(db.AS_team).get(2)
    # team2.member1 = 3
    # team2.member2 = 4
    # team2.member3 = 5
    # db_session.add(team2)

    db_session.commit()

    periods =   {
                1: {"id": 1, "name": "Phase 1", "live": True},
                2: {"id": 2, "name": "Phase 2", "live": True},
                3: {"id": 3, "name": "Phase 3", "live": False}
                }
    
    for period_id, info in periods.items():
        new_period = db.Period(id=period_id, name=info["name"], live=info["live"])
        db_session.add(new_period)
        db_session.commit()

    rendezvous =    {
                    # Phase 1
                    1: {"id": 1, "datetime": dt(year=2023,month=1,day=1,hour=10),"period": 1, "duration": 30},
                    2: {"id": 2, "datetime": dt(year=2023,month=1,day=1,hour=10,minute=30),"period": 1, "duration": 30,"team": 1},
                    3: {"id": 3, "datetime": dt(year=2023,month=1,day=1,hour=11),"period": 1, "duration": 30},
                    4: {"id": 4, "datetime": dt(year=2023,month=1,day=1,hour=11,minute=30),"period": 1, "duration": 30},


                    # Phase 2
                    100: {"id": 100, "datetime": dt(year=2023,month=1,day=1,hour=10),"period": 2, "duration": 30},

                    5: {"id": 5, "datetime": dt(year=2023,month=10,day=1,hour=10),"period": 2, "duration": 30, "team": 2},
                    6: {"id": 6, "datetime": dt(year=2023,month=10,day=1,hour=10,minute=30),"period": 2, "duration": 30},
                    7: {"id": 7, "datetime": dt(year=2023,month=10,day=1,hour=11),"period": 2, "duration": 30},
                    8: {"id": 8, "datetime": dt(year=2023,month=10,day=1,hour=11,minute=30),"period": 2, "duration": 30},
                    9: {"id": 9, "datetime": dt(year=2023,month=10,day=1,hour=12),"period": 2, "duration": 30},
                    10: {"id": 10, "datetime": dt(year=2023,month=10,day=1,hour=12,minute=30),"period": 2, "duration": 30},
                    11: {"id": 11, "datetime": dt(year=2023,month=10,day=1,hour=13),"period": 2, "duration": 30},
                    12: {"id": 12, "datetime": dt(year=2023,month=10,day=1,hour=13,minute=30),"period": 2, "duration": 30},
                    13: {"id": 13, "datetime": dt(year=2023,month=10,day=1,hour=14),"period": 2, "duration": 30},
                    14: {"id": 14, "datetime": dt(year=2023,month=10,day=1,hour=14,minute=30),"period": 2, "duration": 30},
                    15: {"id": 15, "datetime": dt(year=2023,month=10,day=1,hour=15),"period": 2, "duration": 30},
                    16: {"id": 16, "datetime": dt(year=2023,month=10,day=1,hour=15,minute=30),"period": 2, "duration": 30},
                    17: {"id": 17, "datetime": dt(year=2023,month=10,day=1,hour=16),"period": 2, "duration": 30},
                    18: {"id": 18, "datetime": dt(year=2023,month=10,day=1,hour=16,minute=30),"period": 2, "duration": 30},
                    19: {"id": 19, "datetime": dt(year=2023,month=10,day=1,hour=17),"period": 2, "duration": 30},
                    20: {"id": 20, "datetime": dt(year=2023,month=10,day=1,hour=17,minute=30),"period": 2, "duration": 30},
                    21: {"id": 21, "datetime": dt(year=2023,month=10,day=1,hour=18),"period": 2, "duration": 30},
                    22: {"id": 22, "datetime": dt(year=2023,month=10,day=1,hour=18,minute=30),"period": 2, "duration": 30},
                    
                    23: {"id": 23, "datetime": dt(year=2023,month=10,day=2,hour=10),"period": 2, "duration": 30},
                    24: {"id": 24, "datetime": dt(year=2023,month=10,day=2,hour=10,minute=30),"period": 2, "duration": 30},
                    25: {"id": 25, "datetime": dt(year=2023,month=10,day=2,hour=11),"period": 2, "duration": 30},
                    26: {"id": 26, "datetime": dt(year=2023,month=10,day=2,hour=11,minute=30),"period": 2, "duration": 30},
                    27: {"id": 27, "datetime": dt(year=2023,month=10,day=2,hour=12),"period": 2, "duration": 30},
                    28: {"id": 28, "datetime": dt(year=2023,month=10,day=2,hour=12,minute=30),"period": 2, "duration": 30},
                    }

    for rendezvous_id, info in rendezvous.items():
        new_rendezvous = db.Rendezvous(id=rendezvous_id, datetime=info["datetime"], period=info["period"], duration=info["duration"], team=info["team"] if "team" in info else None)
        db_session.add(new_rendezvous)
        db_session.commit()    
