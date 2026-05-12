from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file,jsonify
from sqlalchemy import text  # For raw SQL queries
from forms import LoginForm, CreateAccountForm
from models import User, Thesis, ThesisActivity, College,Course, Subject, student_thesisTitle,EResource, EResourceActivity
from werkzeug.utils import secure_filename
from extension import db
from pypdf import PdfReader, PdfWriter

import logging, io
from datetime import datetime, timedelta, date
from sqlalchemy.sql import func,extract, case,literal_column,asc  # Import func
from functools import wraps
from research import research_bp
import os
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, validators

logging.basicConfig(level=logging.DEBUG)

auth_bp = Blueprint('auth', __name__, template_folder='templates')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_level' not in session or session['user_level'] != 1:
            flash("You are not authorized to access this page.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Renders a simplified admin dashboard with basic statistics.
    """
    total_thesis_uploads = Thesis.query.count()
    hold_count = Thesis.query.filter(Thesis.thesis_status == 2).count()
    publish_count = Thesis.query.filter(Thesis.thesis_status == 0).count()
    new_thesis = Thesis.query.filter(Thesis.thesis_status == 1).count()
    total_users = User.query.count()
    online_users = User.query.filter_by(is_online=True).count()
    
    
    #-------------------analytics porpuses-------------------
    
    view_dates = []
    view_counts = []

    download_dates = []
    download_counts = []

       
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    # end_dt = datetime.strptime(end_date, "%Y-%m-%d")

# include full end day (23:59:59)
    # end_dt = end_dt.replace(hour=23, minute=59, second=59)


    activity_filter = []

    if start_date:
        activity_filter.append(
            ThesisActivity.activity_date >= datetime.strptime(start_date, "%Y-%m-%d")
        )

    if end_date:
        activity_filter.append(
            ThesisActivity.activity_date <= datetime.strptime(end_date, "%Y-%m-%d")
        )
    
    
         # ---- SUMMARY COUNTS ----
    total_theses = db.session.query(func.count(Thesis.id)).scalar()
    total_users = db.session.query(func.count(User.id)).scalar()

    total_views = db.session.query(func.count(ThesisActivity.id))\
        .filter(ThesisActivity.activity_type == 'view')\
        .scalar()

    total_downloads = db.session.query(func.count(ThesisActivity.id))\
        .filter(ThesisActivity.activity_type == 'download')\
        .scalar()

    # ---- TOP VIEWED THESES ----
    top_viewed = (
        db.session.query(
            Thesis.title,
            func.count(ThesisActivity.id).label('views')
        )
        .join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id)
        .filter(ThesisActivity.activity_type == 'view')
        .group_by(Thesis.id)
        .order_by(func.count(ThesisActivity.id).desc())
        .limit(5)
        .all()
    )

    # ---- MONTHLY VIEWS ----
    monthly_views = (
        db.session.query(
            extract('month', ThesisActivity.activity_date),
            func.count(ThesisActivity.id)
        )
        .filter(ThesisActivity.activity_type == 'view')
        .group_by(extract('month', ThesisActivity.activity_date))
        .order_by(extract('month', ThesisActivity.activity_date))
        .all()
    )
    
   #----------- daily analytics--------------------#
   
   # 1. Get Filters from the new UI form
    time_filter = request.args.get('resourceFilter', 'Monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    date_formats = {'Daily': '%Y-%m-%d', 'Monthly': '%Y-%m', 'Yearly': '%Y'}
    fmt = date_formats.get(time_filter, '%Y-%m')

    # 2. Build Thesis Query
    t_query = db.session.query(
        func.date_format(ThesisActivity.activity_date, fmt).label('period'),
        func.sum(case((ThesisActivity.activity_type == 'view', 1), else_=0)).label('t_views'),
        func.sum(case((ThesisActivity.activity_type == 'download', 1), else_=0)).label('t_downloads'),
        literal_column("0").label('e_views'),
        literal_column("0").label('e_downloads')
    )
    
    # Apply date filters if provided
    if start_date:
        t_query = t_query.filter(ThesisActivity.activity_date >= start_date)
    if end_date:
        t_query = t_query.filter(ThesisActivity.activity_date <= end_date)
    
    t_query = t_query.group_by(func.date_format(ThesisActivity.activity_date, fmt))

    # 3. Build E-Resource Query
    e_query = db.session.query(
        func.date_format(EResourceActivity.activity_date, fmt).label('period'),
        literal_column("0").label('t_views'),
        literal_column("0").label('t_downloads'),
        func.sum(case((EResourceActivity.activity_type == 'view', 1), else_=0)).label('e_views'),
        func.sum(case((EResourceActivity.activity_type == 'download', 1), else_=0)).label('e_downloads')
    )
    
    if start_date:
        e_query = e_query.filter(EResourceActivity.activity_date >= start_date)
    if end_date:
        e_query = e_query.filter(EResourceActivity.activity_date <= end_date)
        
    e_query = e_query.group_by(func.date_format(EResourceActivity.activity_date, fmt))

    # 4. Combine and Re-aggregate
    combined = t_query.union_all(e_query).subquery()
    final_stats = db.session.query(
        combined.c.period,
        func.sum(combined.c.t_views).label('thesis_views'),
        func.sum(combined.c.t_downloads).label('thesis_downloads'),
        func.sum(combined.c.e_views).label('eresource_views'),
        func.sum(combined.c.e_downloads).label('eresource_downloads')
    ).group_by(combined.c.period).order_by(combined.c.period.desc()).all()

    #5. Format data for JSON response for the frontend charts
    
    

    return render_template(
            'auth/dashboard.html',
            total_thesis_uploads=total_thesis_uploads,
            hold_count=hold_count,
            publish_count=publish_count,
            new_thesis=new_thesis,
            total_users=total_users,
            online_users=online_users, 
            total_theses=total_theses,
            
            total_views=total_views,
            total_downloads=total_downloads,
            top_viewed=top_viewed,
            monthly_views=monthly_views,
            activity_filter=activity_filter,
            
            
            view_dates=view_dates,
            view_counts=view_counts,
            download_dates=download_dates,
            download_counts=download_counts, 
            final_stats=final_stats,
            fmt=fmt,
            time_filter=time_filter,
            start_date=start_date,
            end_date=end_date,
            analytics_data=final_stats
        )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        username_or_email = form.username.data.strip()
        password = form.password.data

        # Initialize user to None
        user = None

        # Fetch user by username or email
        user = User.query.filter(
            (User.user_userName == username_or_email) |
            (User.user_email == username_or_email)
        ).first()

        if user:
            if user.user_password == password:  
                session['user_id'] = user.id
                session['user_username'] = user.user_userName
                session['user_fullname'] = user.user_fullName

                # Data type handling for user.level
                try:
                    user_level = int(user.level)  # Convert to integer
                except ValueError:
                    print(f"Error: user.level is not a valid integer: {user.level}")
                    user_level = -1  # Or some other default value

                session['user_level'] = user_level

                print(f"Logged in user: {user.user_userName}, Level from DB: {user.level}, Level (int): {user_level}")
                print(f"Session after setting user_level: {session}")

                user.is_online = True
                db.session.commit()
                                
                #Admin of the system route if user level= 0

                if user_level == 1:
                    print("User level is 1, redirecting to dashboard for admin")
                    return redirect(url_for('auth.dashboard'))
                
                elif user_level == 2:
                    print("user level is 2, redirect to Research Portal")
                    return redirect(url_for('research.researchPortal')) #redirect to research.html
                
                #faculty panel route if user level= 3

                elif user_level== 3:
                    return redirect(url_for('auth.facultyPortal'))
                
                #frontdesk/ information desk route if user level= 4
                elif user_level == 4:
                     return redirect(url_for('auth.informationDeskPortal')) 
                

                elif user_level ==5:
                    return redirect(url_for('auth.EresourcesPortal'))
                
                else:
                    print("User level is  0 redirecting to profile")
                    return redirect(url_for('auth.profile'))
                    # return redirect(url_for('home'))
            else:
                flash("Invalid password.", "danger")
        else:
            flash("Invalid username or email.", "danger")

    return render_template('auth/login.html', form=form)

def get_dashboard_data():
    data = {}
    # Total thesis uploads
    data['total_thesis_uploads'] = Thesis.query.count()

    # On-hold theses
    data['on_hold_thesis'] = Thesis.query.filter_by(thesis_status=0).count()

    # Total users
    data['total_users'] = User.query.count()

    # Online users
    data['online_users'] = User.query.filter_by(is_online=True).count()
       

    return data


def get_top_theses():
    top_viewed = db.session.query(
        Thesis.title,
        func.count(ThesisActivity.id).label('view_count')
    ).join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id) \
     .filter(ThesisActivity.activity_type == 'view') \
     .group_by(Thesis.id) \
     .order_by(func.count(ThesisActivity.id).desc()) \
     .limit(5).all()

    top_downloaded = db.session.query(
        Thesis.title,
        func.count(ThesisActivity.id).label('download_count')
    ).join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id) \
     .filter(ThesisActivity.activity_type == 'download') \
     .group_by(Thesis.id) \
     .order_by(func.count(ThesisActivity.id).desc()) \
     .limit(5).all()

    return {'top_viewed': top_viewed, 'top_downloaded': top_downloaded}

def get_reports_per_month():
    reports = db.session.query(
        func.date_format(Thesis.upload_date, '%Y-%m').label('month'),
        func.count(Thesis.id).label('upload_count')
    ).group_by(func.date_format(Thesis.upload_date, '%Y-%m')).all()

    return [{'month': r[0], 'upload_count': r[1]} for r in reports]


#about us

@auth_bp.route('/aboutus')
def aboutus():
    return render_template('aboutUs/aboutus.html')


#view thesis counter
@auth_bp.route('/thesis/<int:thesis_id>/view_thesis', methods=['GET', 'POST'])
def view_thesis(thesis_id):
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            activity = ThesisActivity(thesis_id=thesis_id, user_id=user_id, activity_type='view')
            db.session.add(activity)
            db.session.commit()
            print(activity)
            print("User viewed thesis")
            return jsonify({'status': 'success'}), 200
        
        else:
            print("Please Login to view thesis") 
            return jsonify({'status': 'errror', 'message': "Please Login to view thesis"}), 500
            return redirect(url_for('auth.login'))
    
    except Exception as e:
        db.session.rollback()   
        print(f"Error logging view activity: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
     
   


#download thesis
@auth_bp.route('/thesis/<int:thesis_id>/download_thesis')
def download_thesis(thesis_id):
    thesis = Thesis.query.get(thesis_id)
    if thesis is None:
        return "Thesis not found", 404

    # Log the download
    user_id = session.get('user_id')
    if user_id:
        activity = ThesisActivity(thesis_id=thesis_id, user_id=user_id, activity_type='download')
        db.session.add(activity)
        db.session.commit()
        print("User downloaded thesis")
    else:
        print("Anonymous user downloaded thesis")

    file_path = os.path.join(current_app.root_path, 'uploads', thesis.pdf_file)
    watermark_path = os.path.join(current_app.root_path, 'static', 'images', 'watermark.pdf')

    if not os.path.exists(file_path):
        return "File not found", 404
    
    # Apply Watermark logic
    if os.path.exists(watermark_path):
        reader = PdfReader(file_path)
        watermark_reader = PdfReader(watermark_path)
        watermark_page = watermark_reader.pages[0]
        writer = PdfWriter()

        for page in reader.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"WATERMARKED_{thesis.title}.pdf")

    return send_file(file_path, as_attachment=True, download_name=thesis.title + ".pdf")


""" 
    file_path = os.path.join(current_app.root_path, 'uploads', thesis.pdf_file)

    return send_file(file_path, as_attachment=True, download_name=thesis.title + ".pdf")
 """

# Logout route
@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.is_online = False
            db.session.commit()  # Save the change to the database

    # Clear the session
    session.pop('user_id', None)
    session.pop('user_username', None)
    session.pop('user_fullname', None)
    session.pop('user_level', None)

    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


class CreateAccountForm(FlaskForm):
    """
    Defines the form fields for the user creation account page.
    """
    user_fullname = StringField('Full Name', [validators.DataRequired()])
    user_emailCMUID = StringField('Email / CMU ID', [validators.DataRequired(), validators.Email()])
    user_userName = StringField('Username', [validators.DataRequired()])
    
    user_password = PasswordField('Password', [validators.DataRequired()])
    confirm_user_password = PasswordField('Confirm Password', [
        validators.DataRequired(),
        validators.EqualTo('user_password', message='Passwords must match')
    ])


# Create account route
@auth_bp.route('/create-account', methods=['GET', 'POST'])
def create_account():
    
    form = CreateAccountForm()
       
    if form.validate_on_submit():
        fullname = form.user_fullname.data
        email_cmuid = form.user_emailCMUID.data
        username = form.user_userName.data
        password = form.user_password.data
        confirm_password = form.confirm_user_password.data

        if password != confirm_password:
            flash("Passwords do not match", 'danger')
            return redirect(url_for('auth.create_account'))

        existing_user = User.query.filter(
            (User.user_userName == username) | (User.user_email == email_cmuid)
        ).first()
        if existing_user:
            flash("Username or email is already taken.", 'error')
            return redirect(url_for('auth.create_account'))

        level = 0
        new_user = User(
            user_fullName=fullname,
            user_email=email_cmuid,
            # user_college=college_id,
            # user_course=course_id,
            user_userName=username,
            user_password=password,  # Store plain text password
            level=level
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully!", 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", 'error')
            return redirect(url_for('auth.create_account'))

    return render_template('auth/create_account.html', form=form)

# Profile route
def allowed_file(filename):
    """
    Checks if a filename has an allowed extension.
    """
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




def get_total_Resources():
    
    get_total_Resources_CFES = Thesis.query.filter(Thesis.stud_college == 8).count()
    
    return{ 'get_total_Resources_CFES': get_total_Resources_CFES}

@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    get_total_Resources
    
    resourceList= Thesis.query.order_by(Thesis.upload_date.desc()).all()

    # Check if a user is logged in
    if 'user_id' not in session:
        flash("You need to log in to access this page.", "error")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user is None:
        flash("User not found.", "error")
        return redirect(url_for('auth.login'))

    # Handle the form submission for adding a new thesis (POST request)
    if request.method == 'POST':
        try:
            last_name = request.form.get('lastName')
            first_name = request.form.get('firstName')
            title = request.form.get('approvedThesisTitle')
            abstract = request.form.get('abstract')
            college_id = request.form.get('selectCollege')
            course_id = request.form.get('selectCourse')
            copy_year = request.form.get('CopyYY')
            pdf_file = request.files.get('file')
            subject_id = request.form.get('selectSubject')

            # Validate required fields
            if not all([last_name, first_name, title, abstract, college_id, course_id, copy_year, pdf_file, subject_id]):
                flash("All fields are required!", "error")
                return redirect(url_for('auth.profile'))

            # Validate file type (assuming a function named `allowed_file` exists)
            # You should define this function somewhere in your code
            def allowed_file(filename):
                return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

            if not allowed_file(pdf_file.filename):
                flash("Only PDF files are allowed!", "error")
                return redirect(url_for('auth.profile'))

            # Secure filename and save the file
            filename = secure_filename(pdf_file.filename)
            upload_dir = 'uploads'
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file_path = os.path.join(upload_dir, filename)
            pdf_file.save(file_path)

            # Save the new thesis to the database, associating it with the user
            thesis = Thesis(
                user_id=user.id,
                last_name=last_name,
                first_name=first_name,
                title=title,
                abstract=abstract,
                copyright_yy=copy_year,
                course_id=course_id,
                subject_id=subject_id,
                pdf_file=file_path
            )
            print(thesis)
            db.session.add(thesis)
            db.session.commit()

            flash("Thesis added successfully!", "success")
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while saving the thesis: {e}", "error")
            return redirect(url_for('auth.profile'))

    # Handle the GET request to display the profile page
    if request.method == 'GET':
        try:
            # Correctly fetch submitted thesis titles, using a descriptive variable name
            student_thesis_titles = student_thesisTitle.query.filter_by(
                userID=user.id)
            # ).order_by(
            #     # Use the model class here, not the variable
            #     student_thesis_titles.submitted_at.desc()
            # ).all()
          
            user_theses = Thesis.query.filter_by(user_id=user.id).all()
            total_theses = len(user_theses)

            # Calculate views and downloads
            total_views = 0
            total_downloads = 0
            for thesis in user_theses:
                total_views += ThesisActivity.query.filter_by(thesis_id=thesis.id, activity_type='view').count()
                total_downloads += ThesisActivity.query.filter_by(thesis_id=thesis.id, activity_type='download').count()

            # Fetch data for the modal form dropdowns
            colleges = College.query.all()
            courses = Course.query.order_by(Course.courseName).all()
            subjects = Subject.query.all()

            return render_template(
                'auth/profile.html',
                user=user,
                theses=user_theses,
                thesis_count=total_theses,
                total_views=total_views,
                total_downloads=total_downloads,
                colleges=colleges,
                courses=courses,
                subjects=subjects,
                # Pass the variable with the correct name to your template
                student_thesis_titles=student_thesis_titles,
                resourceList=resourceList
            )

        except Exception as e:
            print(f"An error occurred in the profile route: {e}")
            flash("An error occurred while loading your profile data.", "error")
            return redirect(url_for('home'))



@auth_bp.route('/faculty_portal')
def facultyPortal():
    
    # 1. AUTHENTICATION AND AUTHORIZATION CHECKS
    if 'user_id' not in session:
        flash("You need to log in to access this page.", "error")
        return redirect(url_for('auth.login'))
    

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Assuming level 3 is the faculty/personnel level
    if not user or user.level != 3: 
        flash("You do not have permission to view this page.", "error")
        return redirect(url_for('home')) # Redirect to a safe page

    # 2. DATA FETCHING AND FILTERING
    # Get the selected academic year from the URL query parameters
    selected_acad_year = request.args.get('filter_acad_year', '')

    # Base query for subjects handled by the logged-in faculty
    subjects_query = Subject.query.filter_by(user_ID=user_id)

    # If a specific year is selected, filter the query
    if selected_acad_year:
        subjects_query = subjects_query.filter_by(acad_year=selected_acad_year)

    # Execute the query to get the final list of subjects
    listofSubjectYear = subjects_query.order_by(Subject.acad_year.desc()).all()

    # Fetch unique academic years for the dropdown, specific to this faculty
    db_years_tuples = db.session.query(Subject.acad_year).filter_by(user_ID=user_id).distinct().all()
    db_years = [year[0] for year in db_years_tuples]

    # Generate a list of years based on the system's current date
    system_years = generate_academic_years(num_years_back=3, num_years_forward=1)

    # Combine the lists, remove duplicates, and sort descending for the filter dropdown
    academic_years = sorted(list(set(db_years + system_years)), reverse=True)

    # Calculate total enrolled students (this logic might need refinement based on your needs)
    # For now, let's count students in all subjects handled by the faculty
    count = db.session.query(func.count(db.distinct(student_thesisTitle.userID))).join(Subject, student_thesisTitle.subjectID == Subject.id).filter(Subject.user_ID == user_id).scalar()

    # Generate academic years for the "Add Subject" modal
    modal_academic_years = generate_academic_years(num_years_back=3, num_years_forward=1)

    # 3. RENDER TEMPLATE with all the necessary data
    return render_template(
        'auth/facultyportal.html', 
        user=user, 
        academic_years=academic_years,
        modal_academic_years=modal_academic_years, # Pass the new list for the modal
        listofSubjectYear=listofSubjectYear,
        count=count,
        selected_acad_year=selected_acad_year # Pass the selected year back to the template
    )

# ----------------------------------------------------------------------

def count_enrolled_students(academic_year):
    """
    Counts the total number of unique students enrolled in a given academic year.
    (This function remains exactly as you provided it, using the SQLAlchemy models)
    """
    # ... (function body remains the same)
    student_count = db.session.query(func.count(db.distinct(User.id))).join(
        Subject,
        User.id == Subject.user_ID
    ).join(
        student_thesisTitle,
        User.id == student_thesisTitle.userID
    ).filter(
        Subject.acad_year == academic_year
    ).scalar() 

    return student_count



@auth_bp.route('/get_courses')
def get_courses():
    """
    Returns a JSON list of courses for a given college ID.
    This route is called by the JavaScript in the profile modal.
    """
    try:
        # Get the college_id from the query parameters in the URL
        college_id = request.args.get('college_id', type=int)

        # If no college_id is provided, return an empty list or an error
        if not college_id:
            return jsonify([])

        
        courses = Course.query.filter_by(collegeID=college_id).all()

        courses_list = [
            {'id': course.id, 'courseName': course.courseName}
            for course in courses
        ]

        # Return the list as a JSON response
        return jsonify(courses_list)

    except Exception as e:
        print(f"Error fetching courses: {e}")
        # Return an error message with a 500 status code on failure
        return jsonify({'error': 'Failed to load courses'}), 500


    #search click button for thesis 
@auth_bp.route('/thesis/<int:thesis_id>')
def thesis_details(thesis_id):
    thesis = Thesis.query.get(thesis_id)  # Use SQLAlchemy's query.get() method

    if thesis:  # Check if a thesis with that ID was found
        # Log the view
        user_id = session.get('user_id')
        if user_id:
            activity = ThesisActivity(thesis_id=thesis_id, user_id=user_id, activity_type='view')
            db.session.add(activity)
            db.session.commit()
        else:
            print("Anonymous user viewed thesis")

        return render_template('theses/thesis_detail.html', thesis=thesis) # Render a template to display the thesis
    else:
        return "Thesis not found", 404  # Return a 404 error if the thesis is not found
    

@auth_bp.route('/deleteThesis/<int:thesisId>', methods=['POST']) # This route is correct
def deleteThesis(thesisId):
   
    try:
       
        thesis = student_thesisTitle.query.get_or_404(thesisId)
        
        print(thesis)
       
        if 'user_id' not in session:
            flash('You do not have permission to delete this thesis.', 'danger')
            return redirect(url_for('auth.login'))

        db.session.delete(thesis)
        db.session.commit()

        flash('Thesis title successfully deleted.', 'success')

    except Exception as e:
       
        db.session.rollback()
       
        flash(f'An error occurred: {e}', 'danger')

    
    return redirect(url_for('auth.profile'))

# This route was missing the methods=['POST'] argument
@auth_bp.route('/editThesis/<int:thesisId>', methods=['POST'])
def editThesis(thesisId):
    """
    Handles the submission for editing a thesis title.
    """
    try:
        thesis = student_thesisTitle.query.get_or_404(thesisId)
        
        # Ensure the logged-in user owns this thesis title
        if 'user_id' not in session or thesis.userID != session['user_id']:
            flash('You do not have permission to edit this thesis.', 'danger')
            return redirect(url_for('auth.profile'))

        new_title = request.form.get('new_title')
        if new_title:
            thesis.title = new_title
            db.session.commit()
            flash('Thesis title updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while editing the thesis: {e}', 'danger')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/researchPortal')
def researchPortal():
    if 'user_id' not in session:
        flash("You need to log in to access this page.", "error")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)
   
    if not user or user.level != 2:
        flash("You do not have permission to view this page.", "error")
        return redirect(url_for('home')) 
        
    research_list = (
        db.session.query(
            student_thesisTitle, 
            User,               
        )
        .join(User, student_thesisTitle.userID == User.id)
        .all()
    )
    
    countApproveThesis = student_thesisTitle.query.filter(
    student_thesisTitle.teacherStatus == 2,
    student_thesisTitle.researchStatus == 2
    ).count()

    countPendingThesis= student_thesisTitle.query.filter(
    # student_thesisTitle.teacherStatus==2,
    student_thesisTitle.researchStatus==1).count()

    newSubmittedThesis= student_thesisTitle.query.filter(
    student_thesisTitle.teacherStatus==1).count()


    # Now, pass the user object to the template
    return render_template('research/researchAdmin.html', newSubmittedThesis=newSubmittedThesis, user=user,countPendingThesis=countPendingThesis, research_list=research_list, countApproveThesis=countApproveThesis)
    

@auth_bp.route('/informationDeskPortal')
def informationDeskPortal():
    if 'user_id' not in session:
        flash ("You need to login to access this page.", "error")
        return redirect(url_for('auth.login'))
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    

    if not user or user.level != 4:
        flash ("You do not have Permission to view this page", "error")
        return redirect(url_for('home')) # Or to a safer page like 'home'

    return redirect(url_for('informationDesk.frontdeskPortal'))




################################################for E-resources portal for admin##################################################################
@auth_bp.route('/EresourcesPortal')
def EresourcesPortal():
    
    # 1. AUTHENTICATION AND AUTHORIZATION CHECKS
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    user_id= session.get('user_id')
    user= User.query.get(user_id)
      
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    if not start_date or not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # Cover approximately 12 months
    else:
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)
    
    
    # Query for the list of e-resources
    eresourcesList = EResource.query.order_by(EResource.title.asc()).all()

    # --- Calculate Stats for the Dashboard Cards ---
    # Calculate total resources, views, and downloads for the dashboard cards.
    total_resources = EResource.query.count()
    total_views = EResourceActivity.query.filter_by(activity_type='view').count()
    total_downloads = EResourceActivity.query.filter_by(activity_type='download').count()
    countEbooks = db.session.query(func.count(EResource.id)).filter(EResource.resource_type == 'Ebook').scalar()   
    countEjournals = db.session.query(func.count(EResource.id)).filter(EResource.resource_type == 'Ejournal').scalar()
    
    
    topViewsEresources = db.session.query (EResource.title, func.count(EResourceActivity.id).label('views')).join(EResourceActivity, 
            EResource.id == EResourceActivity.eresource_id ).filter(EResourceActivity.activity_type == 'view').group_by(EResource.id).order_by(func.count(EResourceActivity.id).desc()).limit(5).all()
            
    topDownloadsEresources = db.session.query(EResource.title, func.count(EResourceActivity.id).label('downloads')).join(EResourceActivity, 
            EResource.id == EResourceActivity.eresource_id ).filter(EResourceActivity.activity_type == 'download').group_by(EResource.id).order_by(func.count(EResourceActivity.id).desc()).limit(5).all()
    
        
    monthly_stats = (
    db.session.query(
        func.date_format(EResourceActivity.activity_date, '%Y-%m').label('month'),
        func.sum(case((EResourceActivity.activity_type == 'view', 1), else_=0)).label('views'),
        func.sum(case((EResourceActivity.activity_type == 'download', 1), else_=0)).label('downloads')
    )
    .filter(EResourceActivity.activity_date.between(start_date, end_date))
    
    .group_by(func.date_format(EResourceActivity.activity_date, '%Y-%m'))
    
    .order_by(asc('month')) 
    .all()
)
    
    # Convert to JSON serializable format
    chart_data = [{'month': row.month, 'views': int(row.views), 'downloads': int(row.downloads)} for row in monthly_stats]
    
    if not user or user.level !=5:
        flash("You do not have Permission to view this Page", "error")
        return redirect(url_for('auth.login'))
    
    return render_template('eresources/eresourcesAdmin.html', eresourcesList=eresourcesList,
                           countEbooks=countEbooks, countEjournals=countEjournals, user=user, 
                           total_resources=total_resources, total_views=total_views, total_downloads=total_downloads, topViewsEresources=topViewsEresources, 
                           topDownloadsEresources=topDownloadsEresources,
                           monthly_stats=monthly_stats, chart_data=chart_data, start_date=start_date, end_date=end_date)



# This route was missing. It's needed for the "Edit" modal's AJAX call.
@auth_bp.route('/eresources/get-resource-details/<int:resource_id>')
def get_resource_details(resource_id):
    """
    Returns the details of a specific e-resource as JSON.
    """
    if 'user_id' not in session or session.get('user_level') != 5:
        return jsonify({'error': 'Unauthorized'}), 403

    resource = EResource.query.get_or_404(resource_id)
    
    resource_data = {
        'title': resource.title,
        'author': resource.author,
        'year': resource.year,
        'publisher': resource.publisher,
        'doi': resource.doi,
        'issn_isbn': resource.issn_isbn,
        'subject': resource.subject,
        'staff_notes': resource.staff_notes,
        'resource_type': resource.resource_type,
        'volume': resource.volume,
        'issue': resource.issue,
        'pages': resource.pages
    }
    return jsonify(resource_data)

def generate_academic_years(num_years_back=3, num_years_forward=1):
    """
    Generates a list of academic year strings.
    e.g., with default values and current year 2024, it will produce:
    ['2024-2025', '2023-2024', '2022-2023', '2021-2022']
    """
    current_calendar_year = date.today().year
    academic_years = []
    
    # Generate future and current academic years
    for i in range(num_years_forward, -1, -1):
        start_year = current_calendar_year + i -1
        year_string = f"{start_year}-{start_year + 1}"
        academic_years.append(year_string)

    # Generate past academic years
    for i in range(1, num_years_back + 1):
        start_year = current_calendar_year - i
        year_string = f"{start_year}-{start_year + 1}"
        if year_string not in academic_years: # Avoid duplicates if num_years_forward is 0
            academic_years.append(year_string)
            
    return academic_years
