"""A small web-server hosting all mini-internet tools.

The webserver needs access to the config and group directory,
or concretely to all paths present in the config under the key `LOCATIONS`.
Check the default config below for the list of paths.

Computing the connectivity matrix as well as the BGP analysis can take quite
a while, so it is possible to enabled `BACKGROUND_WORKERS` in the config to
start two background processes taking care of the updates in specified
intervals (`MATRIX_UPDATE_FREQUENCY`, `ANALYSIS_UPDATE_FREQUENCY`).

By default, these workers are started automatically when the app is created.
"""

import math
import os
import pickle
import traceback
from datetime import datetime as dt
from datetime import timezone, timedelta
from multiprocessing import Process
from pathlib import Path
from time import sleep, strftime, gmtime
from typing import Optional
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, render_template, request, url_for, flash
from flask_basicauth import BasicAuth
from jinja2 import StrictUndefined

from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from wtforms.validators import InputRequired, Length, ValidationError
from wtforms.fields import SelectField
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from flask_bcrypt import Bcrypt
import database as db

from utils import parsers
from utils import as_log, date_to_dict, debug, change_pass

from . import bgp_policy_analyzer, matrix

# CAUTION: These default values are overwritten by the setup script.
# ./setup_webserver.sh will write to file 'groups/webserver/admin_config.py' and 'groups/webserver/project_config.py' 
# and then mount them to the docker /server directory.
config_defaults = {
    'LOCATIONS': {
        'groups': '../../../groups',
        'as_config': "../../../config/AS_config.txt",
        "as_connections_public":
        "../../../config/external_links_config_students.txt",
        "as_connections": "../../../config/external_links_config.txt",
        "config_directory": "../../../config",
        "matrix": "../../../groups/matrix/connectivity.txt",
        "as_passwords": "../data/passwords.txt"
    },
    'BASIC_AUTH_USERNAME': 'admin',
    'BASIC_AUTH_PASSWORD': 'admin',
    'HOST': '127.0.0.1',
    'PORT': 8000,
    # Background processing for resource-intensive tasks.
    'BACKGROUND_WORKERS': False,
    'AUTO_START_WORKERS': True,
    'MATRIX_UPDATE_FREQUENCY': 60,  # seconds
    'ANALYSIS_UPDATE_FREQUENCY': 300,  # seconds
    'MATRIX_CACHE': '/tmp/cache/matrix.pickle',
    'ANALYSIS_CACHE': '/tmp/cache/analysis.db',
}

#inittialize global variables
bcrypt = Bcrypt() 
login_choices = []

class ChangePassForm(FlaskForm):
    old_pass = PasswordField('Old Password', validators=[InputRequired(), Length(min=8, max=80)])
    new_pass = PasswordField('New Password', validators=[InputRequired(), Length(min=8, max=80)])
    confirm_pass = PasswordField('Confirm New Password', validators=[InputRequired(), Length(min=8, max=80)])
    submit = SubmitField('Change Password')

class LoginForm(FlaskForm):
    asn = SelectField('AS#', choices=login_choices, validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    submit = SubmitField('Login')

def create_project_server(db_session, config=None, build=False):
    """Create and configure the app."""
    app = Flask(__name__)
    app.config.from_mapping(config_defaults)
    app.jinja_env.undefined = StrictUndefined

    if config is None:
        config = os.environ.get("PROJECT_SERVER_CONFIG", None)

    if config is not None and isinstance(config, dict):
        app.config.from_mapping(config)
    elif config is not None:
        app.config.from_pyfile(config)

    #Used for bgp analysis, to be removed
    basic_auth = BasicAuth(app)

    #AS Login manager
    login_manager = LoginManager(app)
    login_manager.login_view = '/as_login'
    login_manager.session_protection = "strong"
    
    @login_manager.user_loader
    def load_user(asn):
        return db_session.query(db.AS_team).get(int(asn))

    bcrypt.init_app(app)

    if build:
        db.create_as_login(db_session,app.config['LOCATIONS']['as_passwords'])
        db.create_test_db_snapshot(db_session)

    def create_index_list(db_session):
        index_list = {"connectivity_matrix": "matrix"}
        if db_session.query(db.Settings).filter(db.Settings.name == "enable_LookingGlass").first().value == "1":
            index_list["looking_glass"] = "looking glass"
        if db_session.query(db.Settings).filter(db.Settings.name == "enable_Connections").first().value == "1":
            index_list["as_connections"] = "connections"
        if db_session.query(db.Settings).filter(db.Settings.name == "enable_Rendezvous").first().value == "1":
            index_list["rendezvous"] = "rendezvous"
        if db_session.query(db.Settings).filter(db.Settings.name == "enable_ChangePassword").first().value == "1":
            index_list["change_pass_index"] = "change password"
        return index_list

    @app.template_filter()
    def format_datetime(utcdatetime, format='%Y-%m-%d at %H:%M'):
        if utcdatetime.tzinfo is None:  # Attach tzinfo if needed
            utcdatetime = utcdatetime.replace(tzinfo=timezone.utc)
        localtime = utcdatetime.astimezone()
        return localtime.strftime(format)

    @app.template_filter()
    def format_timedelta_int(seconds):
        seconds = int(seconds)
        if seconds == 1:
            return "second"
        elif seconds == 60:
            return "minute"
        elif (seconds % 60) == 0:
            return f"{seconds // 60} minutes"
        return f"{seconds} seconds"
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html', navigation_bar=create_index_list(db_session)), 404

    @app.route("/")
    def index():
        """Redict to matrix as starting page."""
        return redirect(url_for("connectivity_matrix"))

    @app.route("/matrix")
    def connectivity_matrix():
        # Check if Gao-Rexford is enabled.
        gao_rexford = db_session.query(db.Settings).filter(db.Settings.name == "enable_GaoRexford").first().value
        
        """Create the connectivity matrix."""
        # Prepare matrix data (or load if using background workers).
        updated, frequency, connectivity, validity = prepare_matrix(app.config)

        if 'raw' in request.args:
            # Only send json data
            return jsonify(
                last_updated=updated, update_frequency=frequency,
                connectivity=connectivity, validity=validity,
            )

        # Compute percentages as well.
        valid, invalid, failure = 0, 0, 0
        for src, dsts in connectivity.items():
            for dst, connected in dsts.items():
                if connected:
                    # We have connectivity, now check if valid.
                    # If validity could not be checked, assume valid.
                    if validity.get(src, {}).get(dst, True):
                        valid += 1
                    else:
                        invalid += 1
                else:
                    failure += 1
        total = valid + invalid + failure
        if total:
            failure = math.ceil(failure / total * 100)
            if gao_rexford == "1":
                invalid = math.ceil(invalid / total * 100)
                valid = 100 - invalid - failure
            else:
                invalid = 0
                valid = 100 - failure

        return render_template(
            'matrix.html',
            connectivity=connectivity, validity=validity,
            valid=valid, invalid=invalid, failure=failure,
            last_updated=updated, update_frequency=frequency,
            gao_rexford=gao_rexford, navigation_bar=create_index_list(db_session)
        )

    #TODO: Move it to the admin side
    @app.route("/bgp-analysis")
    @basic_auth.required
    def bgp_analysis():
        """Return the full BGP analysis report."""
        updated, freq, messages = prepare_bgp_analysis(app.config)
        return render_template(
            "bgp_analysis.html", messages=messages,
            last_updated=updated, update_frequency=freq, navigation_bar=create_index_list(db_session)
        )

    @app.route("/looking-glass")
    @app.route("/looking-glass/<int:group>")
    @app.route("/looking-glass/<int:group>/<router>")
    def looking_glass(
            group: Optional[int] = None, router: Optional[str] = None):
        """Show the looking glass for group (AS) and router."""
        looking_glass_files = parsers.find_looking_glass_textfiles(
            app.config['LOCATIONS']['groups']
        )
        # Check if looking glass is enabled.
        looking_glass_enabled = db_session.query(db.Settings).filter(db.Settings.name == "enable_LookingGlass").first().value        
        if looking_glass_enabled == "0":
            return render_template('404.html', navigation_bar=create_index_list(db_session)), 404
        

        gao_rexford = db_session.query(db.Settings).filter(db.Settings.name == "enable_GaoRexford").first().value
        need_redirect = False

        if (group is None) or (group not in looking_glass_files):
            # Redict to a possible group.
            group = min(looking_glass_files.keys())
            need_redirect = True

        groupdata = looking_glass_files[group]

        if (router is None) or (router not in groupdata):
            # Redirect to first possible router.
            router = next(iter(groupdata))
            need_redirect = True

        if need_redirect:
            return redirect(
                url_for("looking_glass", group=group, router=router))

        # Now get data for group. First the actual looking glass.
        with open(groupdata[router]) as file:
            filecontent = file.read()

        # Next the analysis.
        updated, freq, messages = prepare_bgp_analysis(app.config, asn=group)

        # Prepare template.
        dropdown_groups = list(looking_glass_files.keys())
        dropdown_routers = list(groupdata.keys())
        return render_template(
            "looking_glass.html",
            filecontent=filecontent,
            bgp_hints=messages,
            group=group, router=router,
            dropdown_groups=dropdown_groups, dropdown_routers=dropdown_routers,
            last_updated=updated, update_frequency=freq, gao_rexford=gao_rexford, navigation_bar=create_index_list(db_session)
        )

    @app.route("/as-connections")
    @app.route("/as-connections/<int:group>")
    @app.route("/as-connections/<int:group>/<int:othergroup>")
    def as_connections(group: int = None, othergroup: int = None):
        # Check if connections are enabled.
        enable_Connections = db_session.query(db.Settings).filter(db.Settings.name == "enable_Connections").first().value        
        if enable_Connections == "0":
            return render_template('404.html', navigation_bar=create_index_list(db_session)), 404        

        """Show the AS connections, optionally for selected groups only."""
        connections = parsers.parse_public_as_connections(
            app.config['LOCATIONS']['as_connections_public'])
        all_ases = {c[0]["asn"] for c in connections}.union(
            {c[1]["asn"] for c in connections})

        def _check_as(data_a, data_b):
            if ((group is None) or (data_a['asn'] == group)) and \
                    ((othergroup is None) or (data_b['asn'] == othergroup)):
                return True
            return False

        selected_connections = []
        for _a, _b in connections:
            if _check_as(_a, _b):
                selected_connections.append((_a, _b))
            elif _check_as(_b, _a):
                selected_connections.append((_b, _a))

        return render_template(
            "as_connections.html",
            connections=selected_connections,
            group=group,
            othergroup=othergroup,
            # All ASes
            dropdown_groups=all_ases,
            # Only matching ASes for first one.
            dropdown_others={conn[1]['asn'] for conn in selected_connections}, navigation_bar=create_index_list(db_session)
        )
    
    @app.route("/as_login", methods=['GET', 'POST'])
    def as_login():
        login_choices.clear()
        allow_inactive = db_session.query(db.Settings).filter(db.Settings.name == "allow_InactiveASLogin").first().value
        if allow_inactive == "1":
            for as_team in db_session.query(db.AS_team).all():
                login_choices.append((as_team.asn, as_team.asn))
        else:
            for as_team in db_session.query(db.AS_team).filter(db.AS_team.is_authenticated==True).all():
                login_choices.append((as_team.asn, as_team.asn))    

        form = LoginForm()
        next_url = request.form.get("next")
        if form.validate_on_submit():
            as_team = db_session.query(db.AS_team).filter(db.AS_team.asn == form.asn.data).first()

            if as_team and (as_team.password==form.password.data):
                if as_team.is_authenticated == False:
                    flash('Login unsuccessful. Your account is not active', 'error')
                    as_log(f"Unsuccessful attempt for {form.asn.data} with password {form.password.data} - account not active -")
                else:
                    as_log(f"Successful attempt for {form.asn.data} with password {form.password.data}")
                    login_user(as_team)
                    db_session.commit()
                    flash('Logged in successfully.', 'success')
                    
                    if next_url:
                        return redirect(next_url)
                    return redirect(url_for('connectivity_matrix'))
        
        
            elif as_team:
                as_log(f"Unsuccessful attempt for {form.asn.data} with password {form.password.data}")
                flash('Login unsuccessful. Please check username and password', 'error')
        
            else:
                as_log(f"Unsuccessful attempt for {form.asn.data} with password {form.password.data}")
                flash('Login unsuccessful. Please check username and password', 'error')

        return render_template('as_login.html', form=form, navigation_bar=create_index_list(db_session))
    
    @app.route("/change_pass", methods=['GET', 'POST'])
    @login_required
    def change_pass_index():
        # Check if connections are enabled.
        enable_ChangePassword = db_session.query(db.Settings).filter(db.Settings.name == "enable_ChangePassword").first().value        
        if enable_ChangePassword == "0":
            return render_template('404.html', navigation_bar=create_index_list(db_session)), 404         

        form = ChangePassForm()
        if form.is_submitted():

            as_log("change pass request for AS " + str(current_user.asn) + " from address: " + str(request.remote_addr))
            
            # The following faulty pass cases are handled in frontend, i
            # if orverriden dont react to change request and report to log file
            if form.old_pass.data != db_session.query(db.AS_team).filter(db.AS_team.asn == current_user.asn).first().password:
                as_log(f"given old pass !=  old pass ({form.old_pass.data} != {db_session.query(db.AS_team).filter(db.AS_team.asn == current_user.asn).first().password})")
            if form.confirm_pass.data != form.new_pass.data:
                as_log(f"new pass != confirm pass ({form.confirm_pass.data} != {form.new_pass.data})")
            elif form.new_pass.data == form.old_pass.data:
                as_log(f"new pass == old pass ({form.new_pass.data} == {form.old_pass.data})")
            
            else:
                password = form.new_pass.data
                as_log(f"Changing password for {current_user.asn} to '{password}'")

                try:
                    change_pass(db_session, app.config['LOCATIONS']['docker_pipe'], current_user.asn, password)
                except ValueError as e:
                    as_log(f"Error changing password for {current_user.asn} to '{password}'")
                    flash(f"Error changing password: {e}", "error")
                    return render_template('change_pass.html', form=form, navigation_bar=create_index_list(db_session))

                flash('Password changed successfully.', 'success') 

        return render_template('change_pass.html', form=form, navigation_bar=create_index_list(db_session))

    @app.route("/rendezvous", methods=['GET'])
    @app.route("/rendezvous/<int:selected_period>", methods=['GET', 'POST'])
    @login_required
    def rendezvous(selected_period: Optional[int] = None):
        # Check if connections are enabled.
        enable_Rendezvous = db_session.query(db.Settings).filter(db.Settings.name == "enable_Rendezvous").first().value        
        if enable_Rendezvous == "0":
            return render_template('404.html', navigation_bar=create_index_list(db_session)), 404      
        
        cancelation_block = timedelta(minutes=int(app.config["CANCELLATION_BLOCKING_TIME"]))

        if request.method == 'POST':
            request_dict = request.form.to_dict()
            if "rend_id" in request_dict:
                requested_rendezvous = db_session.query(db.Rendezvous).filter(db.Rendezvous.id == request_dict["rend_id"]).first()
                if "cancel" in request_dict:

                    if requested_rendezvous.datetime - cancelation_block < dt.now():
                        flash(f'You cannot cancel a rendezvous {cancelation_block} before its start.', 'error')
                    elif requested_rendezvous.datetime < dt.now():
                        flash('You cannot cancel a rendezvous that has already passed.', 'error')
                    elif requested_rendezvous.team != current_user.asn:
                        flash("You cannot cancel a rendezvous booked by another team", "error")
                    elif requested_rendezvous.team is None:
                        flash('This rendezvous is already cancelled.', 'error')
                    else:
                        requested_rendezvous.team = None
                        db_session.commit()
                        flash('Rendezvous cancelled successfully.', 'success')

                elif ("team_asn" in request_dict):
                    
                    if requested_rendezvous.datetime < dt.now():
                        flash('You cannot book a rendezvous that has already passed.', 'error')
                    elif requested_rendezvous.team == current_user.asn:
                        flash('This rendezvous is already booked by your team', 'error')
                    elif requested_rendezvous.team:
                        flash('This rendezvous is already booked by another team', 'error')
                    else:
                        requested_rendezvous.team = request_dict["team_asn"]
                        db_session.commit()
                        flash('Rendezvous booked successfully.', 'success')

        #Period selection page    
        if (selected_period is None) or (db_session.query(db.Period).filter(db.Period.id == selected_period).first() is None) or (db_session.query(db.Period).filter(db.Period.id == selected_period).first().live == False):
            configdict = {"periods":[]}
            for period in db_session.query(db.Period).filter(db.Period.live==True).all():
                configdict["periods"].append({
                    "id":period.id,
                    "name":period.name,
                    })

            if (selected_period is not None) and ((db_session.query(db.Period).filter(db.Period.id == selected_period).first() is None) or (db_session.query(db.Period).filter(db.Period.id == selected_period).first().live == False)):
                flash('Invalid period selected', 'error')
            return render_template('rendezvous_basic.html', configdict=configdict, cancelation_block=cancelation_block, navigation_bar=create_index_list(db_session))
       
        selected_period_obj = db_session.query(db.Period).filter(db.Period.id == selected_period).first()
        if selected_period_obj is None:
            # Invalid period selected
            flash('Invalid period selected', 'error')
            return redirect(url_for('rendezvous')) 

        #Display the actual rendezvous page
        booked_rendezvous = db_session.query(db.Rendezvous).filter(db.Rendezvous.period == selected_period).filter(db.Rendezvous.team == current_user.asn).first()
        configdict = {"periods":[] }

        if booked_rendezvous:
            # If the user has already booked a rendezvous, display only that one
            configdict["booked_rendezvous"] = {
                "id":booked_rendezvous.id,
                "period":booked_rendezvous.period,
                "can_be_cancelled": 1 if (booked_rendezvous.datetime - cancelation_block < dt.now()) else 0,
                "datetime": date_to_dict(booked_rendezvous.datetime),
                "duration":booked_rendezvous.duration
                }

        else:
            configdict = {"rendezvous":[], "periods":[], "days":{}}

            rendlist = db_session.query(db.Rendezvous).filter(db.Rendezvous.period == selected_period).all()
            
            for rendezvous in rendlist:
                date_str = rendezvous.datetime.date().strftime("%d %B, %Y")
                if date_str not in configdict["days"]:
                    configdict["days"][date_str] = []

                configdict["days"][date_str].append({
                    "id":rendezvous.id,
                    "period":rendezvous.period, 
                    "datetime": date_to_dict(rendezvous.datetime),
                    "available": 1 if rendezvous.team == None else 0,
                    "duration":rendezvous.duration,
                    })
                
                configdict["rendezvous"].append({
                    "id":rendezvous.id,
                    "period":rendezvous.period, 
                    "datetime": date_to_dict(rendezvous.datetime),
                    "available": 1 if rendezvous.team == None else 0,
                    "duration":rendezvous.duration,
                    })                


        #In any case, display the period selection and the selected period        
        for period in db_session.query(db.Period).all():
            if not period.live:
                continue
            configdict["periods"].append({
                "id":period.id,
                "name":period.name,
                })

            configdict["selected"] = {} 
            configdict["selected"]["name"] = selected_period_obj.name
            
        return render_template('rendezvous.html', configdict=configdict, cancelation_block=cancelation_block, navigation_bar=create_index_list(db_session))

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash('Logged out successfully.', 'info')
        return redirect(url_for('connectivity_matrix'))

    # Start workers if configured.
    if app.config["BACKGROUND_WORKERS"] and app.config['AUTO_START_WORKERS']:
        start_workers(app)

    return app

# ===================================================
# ===================================================
# ===================================================
# ================ Worker functions =================
# ===================================================
# ===================================================
# ===================================================

def start_workers(given_app):
    """Create background processes"""
    processes = []

    pmatrix = Process(
        target=loop,
        args=(prepare_matrix, given_app.config['MATRIX_UPDATE_FREQUENCY'], given_app.config),
        kwargs=dict(worker=True)
    )
    pmatrix.start()
    processes.append(pmatrix)

    pbgp = Process(
        target=loop,
        args=(prepare_bgp_analysis,
              given_app.config['ANALYSIS_UPDATE_FREQUENCY'], given_app.config),
        kwargs=dict(worker=True)
    )
    pbgp.start()
    processes.append(pbgp)

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


def prepare_matrix(config, worker=False):
    """Prepare matrix.

    Without background workers, create it from scratch now.
    With background workers, only read result if `worker=False`, and
    only create result if `worker=True`.
    """
    cache_file = Path(config["MATRIX_CACHE"])
    if config["BACKGROUND_WORKERS"] and not worker:
        try:
            with open(cache_file, 'rb') as file:
                return pickle.load(file)
        except FileNotFoundError:
            return (None, None, {}, {})

    # Load all required files.
    as_data = parsers.parse_as_config(
        config['LOCATIONS']['as_config'],
        router_config_dir=config['LOCATIONS']['config_directory'],
    )
    connection_data = parsers.parse_as_connections(
        config['LOCATIONS']['as_connections']
    )
    looking_glass_data = parsers.parse_looking_glass_json(
        config['LOCATIONS']['groups']
    )
    connectivity_data = parsers.parse_matrix_connectivity(
        config['LOCATIONS']['matrix']
    )

    # Compute results
    connectivity = matrix.check_connectivity(
        as_data, connectivity_data)
    validity = matrix.check_validity(
        as_data, connection_data, looking_glass_data)

    last_updated = dt.utcnow()
    update_frequency = (config["MATRIX_UPDATE_FREQUENCY"]
                        if config["BACKGROUND_WORKERS"] else None)

    results = (last_updated, update_frequency, connectivity, validity)

    if config["BACKGROUND_WORKERS"] and worker:
        os.makedirs(cache_file.parent, exist_ok=True)
        with open(cache_file, "wb") as file:
            pickle.dump(results, file)

    return results


def prepare_bgp_analysis(config, asn=None, worker=False):
    """Prepare matrix.

    Without background workers, create it from scratch now.
    With background workers, only read result if `worker=False`, and
    only create result if `worker=True`.
    """
    db_file = Path(config["ANALYSIS_CACHE"])

    # Don't even load configs, just immediately return results.
    if config["BACKGROUND_WORKERS"] and not worker:
        freq = config['ANALYSIS_UPDATE_FREQUENCY']
        if not db_file.is_file():
            last = None
            msgs = []
        elif asn is not None:
            last, msgs = bgp_policy_analyzer.load_analysis(db_file, asn)
        else:
            last, msgs = bgp_policy_analyzer.load_report(db_file)
        return last, freq, msgs

    # Now we need configs and compute.
    as_data = parsers.parse_as_config(
        config['LOCATIONS']['as_config'],
        router_config_dir=config['LOCATIONS']['config_directory'],
    )
    connection_data = parsers.parse_as_connections(
        config['LOCATIONS']['as_connections']
    )
    looking_glass_data = parsers.parse_looking_glass_json(
        config['LOCATIONS']['groups']
    )

    if config["BACKGROUND_WORKERS"] and worker:
        os.makedirs(db_file.parent, exist_ok=True)
        # Update db, return nothing
        bgp_policy_analyzer.update_db(
            db_file, as_data, connection_data, looking_glass_data)
        return

    # Compute on the fly
    freq = None
    if asn is not None:
        last, msgs = bgp_policy_analyzer.analyze_bgp(
            asn, as_data, connection_data, looking_glass_data)
    else:
        last, msgs = bgp_policy_analyzer.bgp_report(
            as_data, connection_data, looking_glass_data)
    return last, freq, msgs
