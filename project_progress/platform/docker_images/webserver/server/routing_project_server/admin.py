from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from wtforms.validators import InputRequired, Length, ValidationError
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
login_manager = LoginManager()

class LoginForm(FlaskForm):
        username = StringField(validators=[InputRequired(),], render_kw={"placeholder": "Username"}, )

        password = PasswordField(validators=[InputRequired()], render_kw={"placeholder": "Password"})

        submit = SubmitField('Login')

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return Admin.get(user_id)

def login_user(user):
    pass