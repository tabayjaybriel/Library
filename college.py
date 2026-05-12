from flask import render_template, Blueprint, request, flash, redirect, url_for, jsonify
from models import College, Course # Assuming this is correctly imported
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from extension import db

# Define a simple WTForms form for consistency, if you're using it in your templates
class CollegeForm(FlaskForm):
    college_name = StringField('College Name')
    submit = SubmitField('Submit')

# Define the blueprint
college_bp = Blueprint('college', __name__, url_prefix='/college')

# Main route to view colleges - ALWAYS renders the full page now
@college_bp.route('/list_college', methods=['GET'])
def list_college():
    
    colleges = College.query.order_by(College.name.asc()).all()
    form = CollegeForm() # Still needed for your forms in college.html

    courses_count = Course.query.count()

    # Always render the full college.html template
    return render_template('college/college.html', colleges=colleges, form=form, courses_count=courses_count)


# Add a college
@college_bp.route('/add', methods=['POST'])
def add_college():
    name = request.form['college_name']
    category = 'danger'
    message = 'An unknown error occurred.'

    if name.strip() == '':
        message = 'College name cannot be empty.'
    elif College.query.filter_by(name=name).first():
        message = f'College "{name}" already exists.'
    else:
        new_college = College(name=name)
        db.session.add(new_college)
        try:
            db.session.commit()
            message = f'College "{name}" added successfully!'
            category = 'success'
        except Exception as e:
            db.session.rollback()
            message = f'Error adding college: {str(e)}'

    # Always flash the message, then redirect to the list view (full page reload)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': category})

    flash(message, category)
    return redirect(url_for('auth.dashboard'))

""" 
@college_bp.route('/add_course', methods=['POST'])
# @login_required # Uncomment this line if you want to require user login to add courses
def add_course():
   
    # Use .get() to safely retrieve form data, returning None if key is not found
    course_name = request.form.get('course_name')
    college_id = request.form.get('college_id')
    major = request.form.get('major')

    category = 'danger' # Default flash message category for errors
    message = 'An unknown error occurred while saving data for New Course.'

    try:
        # --- Input Validation ---
        if not course_name or course_name.strip() == '':
            message = 'Course name cannot be empty.'
        elif not college_id:
            message = 'Please select a college.'
        elif Course.query.filter_by(courseName=course_name.strip()).first():
            # Check if a course with this name already exists (case-insensitive check might be better)
            message = f'Course "{course_name.strip()}" already exists.'
        else:
            # --- Check if College Exists ---
            college = College.query.get(college_id)
            if not college:
                message = 'Selected college does not exist. Please choose a valid college.'
            else:
                # --- Create and Save New Course ---
                new_course = Course(
                    courseName=course_name.strip(),
                    major=major.strip() if major else None, # Save major, or None if empty
                    collegeID=college_id
                )
                db.session.add(new_course) # Add the new course object to the session
                db.session.commit() # Commit the transaction to save to the database

                message = f'Course "{course_name.strip()}" added successfully to {college.name}.'
                category = 'success' # Set success category for flash message

    except Exception as e:
        # Rollback the session in case of any database error
        db.session.rollback()
        message = f'Error adding Course: {str(e)}'
        # Log the error for debugging purposes (e.g., app.logger.error(e))

    flash(message, category) # Display a flash message to the user

    # Redirect to the dashboard or appropriate page after the operation
    # Ensure 'auth.dashboard' is a valid endpoint in your application
    # You might need to import 'auth' blueprint or adjust the redirect URL
    return redirect(url_for('auth.dashboard')) 
 """

@college_bp.route('/add_course', methods=['POST'])
# @login_required # Uncomment this line if you want to require user login to add courses
def add_course():
    
    
    course_name = request.form.get('course_name')
    college_id_str = request.form.get('college_id')
    major = request.form.get('major')

    category = 'danger' # Default flash message category for errors
    message = 'An unknown error occurred while saving data for New Course.'

    try:
        if not course_name or course_name.strip() == '':
            message = 'Course name cannot be empty.'
        elif not college_id_str:
            message = 'Please select a college.'
        elif Course.query.filter_by(courseName=course_name.strip()).first():
            message = f'Course "{course_name.strip()}" already exists.'
        else:
            try:
                college_id = int(college_id_str)
            except ValueError:
                message = 'Invalid college ID provided.'
                raise

            college = College.query.get(college_id)
            if not college:
                message = 'Selected college does not exist. Please choose a valid college.'
            else:
                new_course = Course(
                    courseName=course_name.strip(),
                    major=major.strip() if major else None,
                    collegeID=college_id
                )
                db.session.add(new_course)
                db.session.commit()

                message = f'Course "{course_name.strip()}" added successfully to {college.name}.'
                category = 'success'
    except Exception as e:
        db.session.rollback()
        message = f'Error adding Course: {str(e)}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': category})

    flash(message, category) # This is your regular user-facing flash message
    
    # Ensure a valid response is returned for standard form submissions
    return redirect(url_for('auth.dashboard'))

# Edit a college (Will now cause a full page reload)
@college_bp.route('/edit_college/<int:college_id>', methods=['POST'])
def edit_college(college_id):
    college = College.query.get_or_404(college_id)
    new_name = request.form['college_name']
    category = 'danger'
    message = 'An unknown error occurred.'
    
    # Check if the name is empty OR if the name exists and it's a different college (to allow saving if name hasn't changed)
    if new_name.strip() == '':
        message = 'College name cannot be empty.'
    elif College.query.filter_by(name=new_name).first() and new_name != college.name:
        message = f'College "{new_name}" already exists.'
    else:
        college.name = new_name
        try:
            db.session.commit()
            message = f'College "{college.name}" updated successfully!'
            category = 'success'
        except Exception as e:
            db.session.rollback()
            message = f'Error updating college: {str(e)}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': category})

    flash(message, category)
    return redirect(url_for('auth.dashboard'))


# Delete a college (Will now cause a full page reload)
@college_bp.route('/delete/<int:college_id>', methods=['POST'])
def delete_college(college_id):
    college = College.query.get_or_404(college_id)
    category = 'danger'
    message = 'An unknown error occurred.'
    try:
        college_name = college.name
        db.session.delete(college)
        db.session.commit()
        message = f'College "{college_name}" deleted successfully!'
        category = 'success'
    except Exception as e:
        db.session.rollback()
        message = f'Error deleting college: {str(e)}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': category})

    flash(message, category)
    return redirect(url_for('auth.dashboard'))

# @college_bp.route('/view_course')
# def view_course():
    # listofCourse = Course.query.filter(Course.major.isnot(None)).all()
    # listofCourse = Course.query.all()
    # return render_template('college/course.html', listofCourse=listofCourse)


@college_bp.route('/view_course_no_major/<int:collegeID>', methods=['GET'])
def view_course_no_major(collegeID):

    colid = collegeID

    # Fetch the selected college
    college = College.query.get(colid)

    # Fetch courses
    list_ofCourse_no_major = Course.query.filter(
        Course.collegeID == colid
    ).all()

    # Fetch all colleges for dropdown
    colleges = College.query.order_by(College.name.asc()).all()

    return render_template(
        'college/listofcoursePerCollege.html',
        list_ofCourse_no_major=list_ofCourse_no_major,
        colleges=colleges,
        college=college   # <-- ADD THIS
    )


# edit update course
@college_bp.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):

    course = Course.query.get_or_404(course_id)

    # =========================
    # GET REQUEST
    # =========================
    if request.method == 'GET':
        return jsonify({
            'id': course.id,
            'courseName': course.courseName,
            'major': course.major,
            'collegeID': course.collegeID
        })

    # =========================
    # POST REQUEST
    # =========================
    new_course_name = request.form.get('course_name')
    new_major = request.form.get('major')
    new_college_id = request.form.get('college_id')
    
    message = "An unknown error occurred."
    status = "danger"

    if not new_course_name or new_course_name.strip() == '':
        message = 'Course name cannot be empty.'
    elif Course.query.filter(Course.courseName == new_course_name.strip(), Course.id != course_id).first():
        message = f'Course "{new_course_name.strip()}" already exists.'
    elif not new_college_id:
        message = 'Please select a college.'
    else:
        try:
            course.courseName = new_course_name.strip()
            course.major = new_major.strip() if new_major else None
            course.collegeID = int(new_college_id)
            db.session.commit()
            message = f'Course "{course.courseName}" updated successfully!'
            status = "success"
        except Exception as e:
            db.session.rollback()
            message = f'Error updating course: {str(e)}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': status})

    flash(message, status)
    return redirect(url_for('college.view_course'))


# delete course 
@college_bp.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    message = "An unknown error occurred."
    status = "danger"
    try:
        course_name = course.courseName
        db.session.delete(course)
        db.session.commit()
        message = f'Course "{course_name}" deleted successfully!'
        status = "success"
    except Exception as e:
        db.session.rollback()
        message = f'Error deleting course: {str(e)}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'message': message, 'status': status})

    flash(message, status)
    return redirect(url_for('college.view_course'))


#listofcourse and it college
@college_bp.route('/listofcourse')
def listofcourse():
    listofCourse = Course.query.all()
    return render_template('college/list_ofcourse.html', listofCourseOffering=listofCourse)
    
