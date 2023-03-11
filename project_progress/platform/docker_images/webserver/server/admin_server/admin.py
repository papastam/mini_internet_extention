from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import InputRequired, Length, ValidationError
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt
from sqlalchemy.sql import func

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = '/login'

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),], render_kw={"placeholder": "Username"}, )

    password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

class Measurement(db.Model):
    time    = db.Column(db.DateTime(timezone=True), server_default=func.now(), primary_key=True)
    cpu     = db.Column(db.Float, nullable=False)
    memory  = db.Column(db.Float, nullable=False)
    disk    = db.Column(db.Float, nullable=False)



@login_manager.user_loader
def login_user(user):
    return Admin.query.get(int(user))