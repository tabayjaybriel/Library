from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash,session, current_app
from models import Thesis, Subject,User,Personnel, student_thesisTitle, subjectandStudent
from extension import db  # Import db instance
from sqlalchemy.orm import relationship
from werkzeug.utils import secure_filename
from auth import generate_academic_years # Import the function
import os
import requests, datetime
# from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

faculty_bp= Blueprint('faculty', __name__, url_prefix='/faculty')


@faculty_bp.route('/listofSubject')
def listofSubject():
    
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to view subjects.", "error")
        return redirect(url_for('auth.login'))

    # 1. GET THE FILTER VALUE from the URL query string
    # It will be None if "All Academic Years" is selected or if the page is loaded first time
    current_acad_year = request.args.get('filter_acad_year', '')

    try:
        # 2. Build the base query for the logged-in user
        query = Subject.query.filter_by(user_ID=user_id)
        
        # 3. APPLY THE FILTER CONDITION
        if current_acad_year:
            # Add the filter if a specific academic year is selected
            query = query.filter(Subject.acad_year == current_acad_year)
            
        # Execute the query to get the final filtered list
        subjects_list = query.all()
        
        # 4. Fetch the unique academic years for the dropdown (as before)
        db_years_tuples = db.session.query(Subject.acad_year).filter_by(user_ID=user_id).distinct().all()
        db_years = [year[0] for year in db_years_tuples]

        # Generate a list of years based on the system's current date
        system_years = generate_academic_years(num_years_back=3, num_years_forward=1)

        # Combine the lists, remove duplicates, and sort descending for the filter dropdown
        academic_years = sorted(list(set(db_years + system_years)), reverse=True)

        # Generate academic years for the "Add Subject" modal
        modal_academic_years = generate_academic_years(num_years_back=3, num_years_forward=1)

        # 5. Render the template
        return render_template(
            'faculty/subjectList.html', 
            subjects=subjects_list,
            academic_years=academic_years,
            modal_academic_years=modal_academic_years, # Pass the new list for the modal
            current_acad_year=current_acad_year # <-- Pass the filter value back to the template
        )
    
    except Exception as e:
        print(f"Error fetching subjects: {e}")
        flash("An error occurred while fetching the list of subjects.", "error")
        return redirect(url_for('auth.facultyPortal'))


@faculty_bp.route('/studentListPersubject/<int:subject_id>', methods=['GET'])
def studentListPersubject(subject_id):
    """
    Fetches and displays a list of students for a specific subject
    using a single, efficient SQLAlchemy query that mirrors the working SQL.
    """
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view this page.", "error")
        return redirect(url_for('auth.login'))

    try:
        subject = Subject.query.filter_by(id=subject_id).first()
        if not subject:
            flash("Subject not found.", "error")
            return redirect(url_for('faculty.listofSubject'))

        
        results = (
            db.session.query(
                student_thesisTitle, 
                User,               
            )
            .join(User, student_thesisTitle.userID == User.id)
            .filter(student_thesisTitle.subjectID == subject_id)
            .all()
        )

        # Process the results into the desired format for the template
        listofStudentinSubject = []
        for thesis, student in results:
            listofStudentinSubject.append({
                'thesis_details': thesis,
                'student_details': student
            })
        
        # AJAX requests load partial content into #facultyContainer
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template(
                'faculty/_studentInSubject_partial.html',
                subject=subject,
                listofStudentinSubject=listofStudentinSubject
            )

        # Normal full page render
        return render_template(
            'faculty/studentIn_aSubject.html',
            subject=subject,
            listofStudentinSubject=listofStudentinSubject
        )

    except Exception as e:
        print(f"Error fetching data of student in subject: {e}")
       
        raise
       
@faculty_bp.route('/approve_thesis', methods=['POST'])
def approve_thesis():
    
    thesis_id = request.form.get('thesis_id', type=int)
    
    if not thesis_id:
        flash("Error: Thesis ID is missing.", "danger")
        
        return redirect(url_for('auth.facultyPortal')) 
    
    thesis = student_thesisTitle.query.get_or_404(thesis_id)
    

    thesis.teacherStatus = 2
    db.session.commit()
    
    
    flash(f"Thesis '{thesis.title}' has been approved.", "success")
    return redirect(url_for('faculty.studentListPersubject', subject_id=thesis.subjectID))



@faculty_bp.route('/denyThesis', methods=['POST'])
def deny_thesis():
    thesis_id = request.form.get('thesis_id', type=int)
    thesis = student_thesisTitle.query.get_or_404(thesis_id)
    thesis.teacherStatus = 0
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': f"Thesis '{thesis.title}' has been denied.", 'subject_id': thesis.subjectID})

    flash(f"Thesis '{thesis.title}' has been denied.", "danger")
    return redirect(url_for('faculty.studentListPersubject', subject_id=thesis.subjectID))

@faculty_bp.route('/deleteSubject/<int:subject_id>', methods=['POST'])
def deleteSubject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash(f"Subject '{subject.courseDescription}' Has been deleted.", "success")
    return redirect(url_for('auth.facultyPortal'))

@faculty_bp.route('/editSubject/<int:subject_id>', methods=['POST'])
def editSubject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject.courseDescription = request.form.get('description')
    subject.acad_year = request.form.get('academicYear')
    subject.subjectCode = request.form.get('subjectCode')

    db.session.commit()
    flash(f"Subject '{subject.courseDescription}' has been updated.", "success")
    return redirect(url_for('auth.facultyPortal'))
