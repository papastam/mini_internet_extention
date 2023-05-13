from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func

from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .build_db import create_test_db_snapshot

db = SQLAlchemy()

Base = declarative_base()
engine = create_engine("sqlite:////server/database/database.db", echo=False)
Session = sessionmaker(bind=engine)

class Admin(Base):
    __tablename__ = "admin"
 
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

    # Needed to be a User class for Flask-Login
    is_authenticated    = db.Column(db.Boolean, nullable=False, default=True)
    is_active           = db.Column(db.Boolean, nullable=False, default=True)
    is_anonymous        = db.Column(db.Boolean, nullable=False, default=False)

    def get_id(self):
        return self.id

class Measurement(Base):
    __tablename__ = "measurement"
 
    time    = db.Column(db.DateTime(timezone=True), server_default=func.now(), primary_key=True)
    cpu     = db.Column(db.Float, nullable=False)
    memory  = db.Column(db.Float, nullable=False)
    disk    = db.Column(db.Float, nullable=False)

class AS_team(Base):
    __tablename__ = "as_team"
 
    asn         = db.Column(db.Integer, primary_key=True)
    password    = db.Column(db.String(20), nullable=False)
    active_as   = db.Column(db.Boolean, nullable=False, default=False)
    # Members are addressed by their unique ID
    member1     = db.Column(db.Integer, ForeignKey("student.id"), nullable=True, default=None)
    member2     = db.Column(db.Integer, ForeignKey("student.id"), nullable=True, default=None)
    member3     = db.Column(db.Integer, ForeignKey("student.id"), nullable=True, default=None)
    member4     = db.Column(db.Integer, ForeignKey("student.id"), nullable=True, default=None)

    # Needed to be a User class for Flask-Login
    is_authenticated    = db.Column(db.Boolean, nullable=False, default=True)
    is_active           = db.Column(db.Boolean, nullable=False, default=True)
    is_anonymous        = db.Column(db.Boolean, nullable=False, default=False)

    def get_id(self):
        return self.asn

class Student(Base):
    __tablename__ = "student"
 
    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(50), nullable=False)
    email   = db.Column(db.String(50), nullable=True)
    team    = db.Column(db.Integer, ForeignKey("as_team.asn"), nullable=True, default=None)
    # Grades
    P1Q1    = db.Column(db.Float, nullable=True, default=None)
    P1Q2    = db.Column(db.Float, nullable=True, default=None)
    P1Q3    = db.Column(db.Float, nullable=True, default=None)
    P1Q4    = db.Column(db.Float, nullable=True, default=None)
    P1Q5    = db.Column(db.Float, nullable=True, default=None)
    
    midterm1   = db.Column(db.Float, nullable=True, default=None)

    P2Q1    = db.Column(db.Float, nullable=True, default=None)
    P2Q2    = db.Column(db.Float, nullable=True, default=None)
    P2Q3    = db.Column(db.Float, nullable=True, default=None)
    P2Q4    = db.Column(db.Float, nullable=True, default=None)
    P2Q5    = db.Column(db.Float, nullable=True, default=None)

    midterm2   = db.Column(db.Float, nullable=True, default=None)

class Rendezvous(Base):
    __tablename__ = "rendezvous"
 
    id          = db.Column(db.Integer, primary_key=True)
    period      = db.Column(db.Integer, ForeignKey('period.id'), nullable=False)
    datetime    = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    duration    = db.Column(db.Integer, nullable=False)
    team        = db.Column(db.Integer, ForeignKey('as_team.asn'), nullable=True, default=None)
    
class Period(Base):
    __tablename__ = "period"
 
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String, nullable=False)
    live        = db.Column(db.Boolean, nullable=False, default=False)

def init_db(build: bool = False):
    # Create the database
    if build:
        Base.metadata.create_all(engine)
    session = Session()
    return session
