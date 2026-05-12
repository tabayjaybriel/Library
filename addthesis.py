# addthesis.py
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from werkzeug.utils import secure_filename
import os
from extension import db  # Import db from extension.py
from models import Thesis, College, Course, User,db  # Import models

# Create a Blueprint
add_thesis_bp = Blueprint('add_thesis', __name__, template_folder='templates')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to handle adding a thesis
@add_thesis_bp.route('/add-thesis', methods=['GET', 'POST'])
def add_thesis():
    colleges = College.query.all()
    courses = Course.query.all()

    if request.method == 'POST':
        last_name = request.form.get('lastName')
        first_name = request.form.get('firstName')
        title = request.form.get('title')
        abstract = request.form.get('abstract')
        college_id = request.form.get('selectCollege')
        course_id = request.form.get('selectCourse')
        copy_year = request.form.get('CopyYY')
        pdf_file = request.files.get('file')

        # Validate required fields
        if not all([last_name, first_name, title, abstract, college_id, course_id, copy_year, pdf_file]):
            flash("All fields are required!", "error")
            return redirect(url_for('add_thesis.add_thesis'))

        # Validate file type
        if not allowed_file(pdf_file.filename):
            flash("Only PDF files are allowed!", "error")
            return redirect(url_for('add_thesis.add_thesis'))

        # File handling
        filename = secure_filename(pdf_file.filename)
        file_path = os.path.join('uploads', filename)
        try:
            # Save the file to the UPLOAD_FOLDER
            pdf_file.save(file_path)

            # Save to the database
            thesis = Thesis(
                last_name=last_name,
                first_name=first_name,
                title=title,
                abstract=abstract,
                copyright_yy=copy_year,
                course_id=course_id,  # Corrected to match foreign key
                pdf_file=file_path
            )
            db.session.add(thesis)
            db.session.commit()

            flash("Thesis added successfully!", "success")
            return redirect(url_for('add_thesis.add_thesis'))
        except Exception as e:
            flash(f"An error occurred while saving the thesis: {e}", "error")
            return redirect(url_for('add_thesis.add_thesis'))

    return render_template('theses/addthesis.html', colleges=colleges, courses=courses)


#dropdown for select a college it will reflect on the select course select option drop down

@add_thesis_bp.route('/get_courses_by_college/<int:college_id>', methods=['GET'])
def get_courses_by_college(college_id):
    """
    Fetches courses associated with a given college ID and returns them as JSON.
    """
    try:
        # Query courses filtered by collegeID
        # Ensure 'collegeID' in Course model matches the foreign key column name
        courses = Course.query.filter_by(collegeID=college_id).all()

        # Prepare data for JSON response
        courses_data = [{'id': course.id, 'name': course.courseName} for course in courses]

        return jsonify(courses_data)

    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching courses for college ID {college_id}: {e}")
        return jsonify({'error': 'Could not fetch courses'}), 500
    
