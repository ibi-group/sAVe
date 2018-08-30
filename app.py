from flask import (
    Flask, render_template, jsonify, session, request, Response, redirect,
    url_for
)
import api
from multidict import MultiDict
import users
import businessdata
import json
import collections
import statistics
from flask_wtf import FlaskForm
from wtforms import (
    widgets, StringField, BooleanField, PasswordField,
    SubmitField, RadioField, SelectMultipleField, FormField,
    DecimalField, FloatField, IntegerField, FieldList,
    SelectField
)
from wtforms.validators import DataRequired, ValidationError, NumberRange
from flask_login import (
    LoginManager, UserMixin, login_required, login_user, logout_user
)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# This is to manage the login, through flask-login package.
login_manager = LoginManager()
login_manager.init_app(app)
# Set the login page view.
login_manager.login_view = "login"

app.secret_key = "Very big secret"


class User(UserMixin):

    def __init__(self, username, business=False):
        self.username = username
        if (business):
            temp_id = businessdata.get_business_id(username)
            session["business"] = True
        else:
            temp_id = users.get_user_id(username)
            session["business"] = False
        if (temp_id):
            self.id = temp_id[0]

    def __repr__(self):
        return "{}".format(self.id)


# This is supposed to validate the income field, so as not to use commas.
def income_validator(form, field):
    # print(field.data)
    # if field.data:
    raise ValidationError('Please do not use commas!')


# Checkboxes instead of the weird select fields.
class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


# Form for the filters that can be applied to statistics.
class FilterForm(FlaskForm):
    and_or = RadioField(choices=[
        ("AND", "Coincident Filter"),
        ("OR", "Regular Filter")
    ],
        validators=[DataRequired()]
    )
    filters = MultiCheckboxField(
        u'<b>Filters:</b>',
        validators=[DataRequired()]
    )
    categories = MultiCheckboxField(
        u'Categories (never coincident with each other):'
    )
    map_all = SubmitField("See Map of All")
    submit = SubmitField("Filter Map")


# Form for settings page.
# One could do this using a MultipleCheckboxField instead, by the way.
class PreferenceForm(FlaskForm):
    ada = BooleanField('I require accessible transit.')
    student = BooleanField('I am a student.')
    senior = BooleanField('I am a senior citizen. (65+)')
    income = FloatField('Yearly Income: $', validators=[])


# Wrapper for settings form, to make it super easy to pass data into database.
class PreferenceSubmit(FlaskForm):
    preferences = FormField(PreferenceForm)
    save = SubmitField("Save")


# Form for getting the addresses and walk radius.
class AddressForm(FlaskForm):
    origin = StringField('Origin Address:', validators=[DataRequired()])
    dest = StringField('Destination Address:', validators=[DataRequired()])
    radius = DecimalField(
        'Maximum Walking Distance(in km):',
        validators=[DataRequired()]
    )


# Form for logging in or registering.
class LoginForm(FlaskForm):
    username = StringField('Username:', validators=[DataRequired()])
    password = PasswordField('Password:', validators=[DataRequired()])
    login = SubmitField("Login")
    register = SubmitField("Register")


# Login/Register Form for Businesses
class BusinessLoginForm(FlaskForm):
    username = StringField('Username:', validators=[DataRequired()])
    password = PasswordField('Password:', validators=[DataRequired()])
    login = SubmitField("Login")
    register = SubmitField("Register")


# Business Preference Form
class BusinessForm(FlaskForm):
    category_list = [
        ('', '---'),
        ('Education', 'Education'),
        ('Housing', 'Housing'),
        ('Health and Medical', 'Health and Medical'),
        ('Retail (Grocery)', 'Retail (Grocery)'),
        ('Office', 'Office'),
        ('Recreational', 'Recreational'),
        ('Retail', 'Retail',),
        ('Religious', 'Religious'),
        ('Non-Profit', 'Non-Profit')

    ]
    category = SelectField(
        'Category:',
        choices=category_list,
        validators=[DataRequired()]
    )
    address = StringField('Address:', validators=[DataRequired()])
    discount = FloatField(
        'Discount:',
        validators=[
            NumberRange(
                min=0,
                max=100,
                message=u"Please input from a range of 0-100"
            )
        ]
    )
    promotion = IntegerField(
        'Promotion:',
        validators=[
            NumberRange(
                min=0,
                max=100,
                message=u"Please input from a range of 0-100"
            )
        ]
    )
    time_list = [
        ('', '---'), ('24 hours', '24 hours'),
        ('48 hours', '48 hours'), ('72 hours', '72 hours')
    ]
    promotion_time = SelectField(
        'Promotion Time:',
        choices=time_list
    )
    display_on_map = BooleanField('Display on Map:')


class BusinessSubmit(FlaskForm):
    settings = FormField(BusinessForm)
    saveSettings = SubmitField("Save")


# This loads the user or business, as per flask-login.
@login_manager.user_loader
def load_user(userid):
    if "business" not in session:
        return User(userid)
    return User(userid, business=True)


# This is obviously not secure, and is so javascript can make ajax requests.
@app.route("/secret")
def secret_loader():
    with open("secret.json") as f:
        # Return as JSON.
        return jsonify(json.load(f))


# Route for logging in.
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        # Not hashed or salted on either end, I leave that to you.
        password = form.password.data
        correct = False
        if form.login.data:
            correct = users.verify_user(username, password)
        elif form.register.data:
            correct = users.add_user(username, password)
        # If registering or logging in went well. Could rename this "success".
        if correct:
            user = User(username)
            login_user(user)
            return redirect("/settings")
        else:
            return (
                "We couldn't create your user or log you in",
                "for some odd reason.",
                "Either your username or password is wrong,",
                "or your username is already taken."
            )
    else:
        return render_template("login.html", form=form)


# Route for business logging in, very similar to /login.
@app.route("/business", methods=["GET", "POST"])
def business():
    form = BusinessLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        correct = False
        if form.login.data:
            correct = businessdata.verify_business(username, password)
        elif form.register.data:
            correct = businessdata.add_business(username, password)
        if correct:
            business = User(username, True)
            login_user(business)
            return redirect("/businesspreferences")
        else:
            return (
                "We couldn't create your user or log you in",
                "for some odd reason.",
                "Either your username or password is wrong,",
                "or your username is already taken."
            )
    else:
        return render_template("business.html", form=form)


@app.route("/government", methods=["POST", "GET"])
def government_load():
    return render_template("government.html")


# Route for business preferences, very similar to settings.
@app.route("/businesspreferences", methods=["POST", "GET"])
@login_required
def businessPreferences():
    form = BusinessSubmit()
    if form.validate_on_submit():
        businessdata.save_settings(session["user_id"], form.settings.data)
        session["settings"] = form.settings.data
    settings = businessdata.get_setting(session["user_id"])
    if settings:
        settings = dict(settings)
        form.process(settings=settings)
    else:
        businessdata.save_settings(session["user_id"], form.settings.data)
    session["settings"] = form.settings.data
    return render_template("businessSettings.html", form=form)


# Route for after trip has been chosen.
@app.route("/trip", methods=["GET", "POST"])
def trip():
    trip_id = request.form["trip_number"]
    # Marks trip as chosen
    statistics.choose_trip(trip_id)
    return render_template("trip.html")


# Route for logging out.
@app.route("/logout")
@login_required
def logout():
    # From flask-login
    logout_user()
    return redirect("/login")


# Route for user preferences.
@app.route("/settings", methods=["POST", "GET"])
@login_required
def settings():
    form = PreferenceSubmit()
    if form.validate_on_submit():
        # Now that the form is submitted, we definitely have preference data.
        # Set the session, and go to the address page.
        users.save_preference(session["user_id"], form.preferences.data)
        session["preferences"] = form.preferences.data
        return redirect("/")
    # Get my saved preferences. If I have them, fill the form with them. If I
    # don't have any, save a blank template as my preferences. Now, the data-
    # base has some for me. Either way, their in the form, so set my session
    # equal to the form data (in case the user hits home), and load the page.
    preferences = users.get_preference(session['user_id'])
    if preferences:
        preferences = dict(preferences)
        form.process(preferences=preferences)
    else:
        users.save_preference(session["user_id"], form.preferences.data)
    session["preferences"] = form.preferences.data
    return render_template("settings.html", form=form)


# Route for entering addresses.
@app.route("/", methods=["POST", "GET"])
@login_required
def directions():
    form = AddressForm()
    if form.validate_on_submit():
        origin = form.data["origin"]
        dest = form.data["dest"]
        radius = form.data["radius"]
        # Getting the directions as direct, and any special modifiers
        # as subsz.
        # Function get_directions should be further explained in its file.
        direct, subsz = api.get_directions(
            origin, dest, radius,
            session["preferences"], session["user_id"]
        )
        # print(json.dumps(direct["trips"], indent=4))
        # If you somehow didn't receive directions.
        if ((not direct) or (not direct["trips"])):
            return ("There was a problem with your addresses!")
        return render_template("directions.html", obj=direct, subsz=subsz)
    # Display businesses which request to be displayed.
    locations = [
        dict(location) for location in businessdata.get_displayed_locations()
    ]
    return render_template("address.html", form=form, locations=locations)


# Government analytics page.
@app.route("/statistics", methods=["POST", "GET"])
def load_statistics():
    trip_statistics = statistics.get_trip_statistics()
    totals = {}
    totals["Total results"], \
        totals["Number of chosen trips"] = statistics.get_totals()
    user_statistics = users.get_all_preferences()
    form = FilterForm()
    choice_list = [
        (key, key) for key in trip_statistics.keys() if key != "Total"
    ]
    form.filters.choices = choice_list
    filtered_totals = {"Total results": 0, "Number of chosen trips": 0}
    if form.validate_on_submit():
        # If you'd like to map everything.
        if (form.map_all.data):
            locations = statistics.get_all_latitude_longitude()
        # Otherwise, map just the filtered results.
        else:
            data_load = (form.filters.data, form.and_or.data)
            filtered_totals["Total results"], \
                filtered_totals["Number of chosen trips"] = \
                statistics.get_statistic(*data_load)
            locations = (
                statistics.get_filtered_latitude_longitude(*data_load)
            )
    else:
        # Map all if there was no form submitted.
        locations = statistics.get_all_latitude_longitude()
    # In any event, run through and make dictionaries out of the sqlite rows.
    locations = [
        dict(location) for location in locations
    ]
    return render_template(
        "statistics.html", result=trip_statistics, users=user_statistics,
        totals=totals, form=form, filtered_totals=filtered_totals,
        locations=locations
    )


# Government analytics for businesses.
@app.route("/businessdata", methods=["POST", "GET"])
def load_business_statistics():
    business_statistics = dict(businessdata.get_data())
    # List of categories.
    categories = businessdata.get_categories()
    totals = {}
    totals["Businesses Registered"] = business_statistics["registered"]
    totals["Businesses with Promotions"] = business_statistics["promotion"]
    totals["Businesses with Discounts"] = business_statistics["discounted"]
    totals["Number of Categories"] = business_statistics["categories"]
    totals["Businesses on Consumer Map"] = business_statistics["displayed"]
    form = FilterForm()
    choice_list = [
        (key, key) for key in business_statistics.keys()
        if key not in ("registered", "categories")
    ]
    form.categories.choices = [
        (key["category"], key["category"]) for key in categories
    ]
    form.filters.choices = choice_list
    filtered_totals = {
        "Businesses Registered": 0,
        "Businesses with Promotions": 0,
        "Businesses with Discounts": 0,
        "Businesses on Consumer Map": 0
    }
    if form.validate_on_submit():
        # If you'd like to map everything.
        if (form.map_all.data):
            business_locations = businessdata.get_all_locations()
        # Otherwise, map just the filtered results.
        else:
            data_load = (
                form.filters.data,
                form.and_or.data,
                form.categories.data
            )
            filtered_statistics = businessdata.get_filtered_data(*data_load)
            filtered_totals["Businesses Registered"] = \
                filtered_statistics["registered"]
            filtered_totals["Businesses with Promotions"] = \
                filtered_statistics["promotion"]
            filtered_totals["Businesses with Discounts"] = \
                filtered_statistics["discounted"]
            filtered_totals["Businesses on Consumer Map"] = \
                filtered_statistics["displayed"]
            business_locations = (
                businessdata.get_filtered_locations(*data_load)
            )
    else:
        # Map all if there was no form submitted.
        business_locations = businessdata.get_all_locations()
    # In any event, run through and make dictionaries out of the sqlite rows.
    business_locations = [
        dict(location) for location in business_locations
    ]
    return render_template(
        "businessdata.html", result=business_statistics,
        totals=totals, form=form, filtered_totals=filtered_totals,
        locations=business_locations, categories=categories
    )
