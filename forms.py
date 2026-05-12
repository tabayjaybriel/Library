from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length,Email, EqualTo
from wtforms import StringField, PasswordField, SelectField  # Import necessary form fields



class LoginForm(FlaskForm):
    username = StringField(
        'Username or Email',
        validators=[
            DataRequired(message="Please enter your username or email."),
            Length(max=150, message="Username or email is too long.")
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Please enter your password."),
            Length(min=6, message="Password must be at least 6 characters long.")
        ]
    )
    submit = SubmitField('Login')



class CreateAccountForm(FlaskForm):
    user_fullname = StringField("Full Name", validators=[DataRequired()])
    user_emailCMUID = StringField("Email", validators=[DataRequired(), Email()])
    dropdown_value = SelectField("College", choices=[], validators=[DataRequired()])
    user_userName = StringField("Username", validators=[DataRequired()])
    user_password = PasswordField("Password", validators=[DataRequired()])
    confirm_user_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("user_password", message="Passwords must match")],
    )
    submit = SubmitField("Create Account")