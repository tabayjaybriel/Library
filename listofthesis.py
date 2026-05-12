from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash,session, current_app, send_file
from models import Thesis, Subject,User,Personnel, student_thesisTitle, College, Course
from extension import db  # Import db instance
from sqlalchemy.orm import relationship
from werkzeug.utils import secure_filename
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import io
import os
import requests
# from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import date
# from serpapi import GoogleSearch
from dotenv import load_dotenv
from sqlalchemy import or_
from scholar_scraper import scholar_scrape
from scrap import perform_scholar_search, process_scholar_results

load_dotenv()  # This loads variables from .env
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
# Define the Blueprint
thesislists_bp = Blueprint('listofthesis', __name__, template_folder='templates')

# Route to display all theses
@thesislists_bp.route('/list',methods=['GET'])
def list_theses():
    theses = Thesis.query.all()
    hold_count = Thesis.query.filter_by(thesis_status=0).count()
    publish_count = Thesis.query.filter_by(thesis_status=1).count()
    print(theses)
    print('hold:', hold_count)
    print('published:',publish_count )
    print(url_for('listofthesis.list_theses'))

    return render_template('theses/listofThesis.html', theses=theses, hold_count=hold_count, publish_count=publish_count)


@thesislists_bp.route('/newTheses', methods=['GET'])
def newTheses():
    # newThesesList= Thesis.filter_by(thesis_status=0).all()
    newThesesList= Thesis.query.all()
    
    return render_template('theses/newThesis.html', theses=newThesesList)

# Route to edit a thesis using a form in the listing page
@thesislists_bp.route('/edit/<int:thesis_id>', methods=['POST'])
def edit_thesis(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)
    # Update fields from form data
    thesis.title = request.form.get('title')
    thesis.last_name = request.form.get('last_name')
    thesis.first_name = request.form.get('first_name')
    thesis.course = request.form.get('course')
    thesis.thesis_status = request.form.get('status', 0)
    db.session.commit()
    flash("Thesis details updated successfully!", "success")
    return redirect(url_for('listofthesis.list_theses'))

# Route to change thesis status to 'hold'
@thesislists_bp.route('/hold/<int:thesis_id>', methods=['POST'])
def hold_thesis(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)
    thesis.thesis_status = 0
    db.session.commit()
    flash("Thesis status set to Hold.", "warning")
    return redirect(url_for('listofthesis.list_theses'))

# Route to change thesis status to 'publish'
@thesislists_bp.route('/publish/<int:thesis_id>', methods=['POST'])
def publish_thesis(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)
    thesis.thesis_status = 1
    db.session.commit()
    flash("Thesis status set to Published.", "success")
    return redirect(url_for('listofthesis.list_theses'))

# Route to filter theses by status
@thesislists_bp.route('/filter/<string:status>', methods=['GET'])
def filter_theses(status):
    if status not in ['all', 'hold', 'published']:
        return jsonify({'error': 'Invalid status parameter'}), 400

    theses = Thesis.query.all() if status == 'all' else Thesis.query.filter_by(
        thesis_status=0 if status == 'hold' else 1).all()

    thesis_data = [
        {
            'id': thesis.id,
            'title': thesis.title,
            'first_name': thesis.first_name,
            'last_name': thesis.last_name,
            'course': thesis.course,
            'status': 'Hold' if thesis.thesis_status == 0 else 'Published',
        }
        for thesis in theses
    ]
    return jsonify(thesis_data)  

# addSubject 
@thesislists_bp.route('/addSubject', methods=['POST'])
def addSubject():
   
    user_id = session.get('user_id')
    print(f"User ID from session: {user_id}")
    if not user_id:
        flash("You must be logged in to add a subject.", "error")
        return redirect(url_for('auth.login'))

    try:
        subject_code = request.form.get('subjectcode')
        description = request.form.get('description')
        acad_year = request.form.get('academicYear') 
        
        print(f"Form Data: Subject Code: {subject_code}, Description: {description}")

        if not subject_code or not description:
            flash("All fields are required.", "error")
            return redirect(url_for('auth.facultyPortal'))

        new_subject = Subject(
            subjectID=subject_code,
            courseDescription=description,
            user_ID=user_id,  
            acad_year=acad_year
        )

        db.session.add(new_subject)
        db.session.commit()

        flash("Subject added successfully!", "success")
        return redirect(url_for('auth.facultyPortal'))

    except Exception as e:
        db.session.rollback()
        # This will print the exact database error to your console
        print(f"Database Error: {e}")
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for('auth.facultyPortal'))
        


@thesislists_bp.route('/loadStudentSubject')
def loadStudentSubject():
    """
    This route fetches all subjects and renders the profile page with the list.
    """
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to view subjects.", "error")
        return redirect(url_for('auth.login'))
    try:
       
        listofThesisSubject = Subject.query.all()
        print(f"Subjects fetched from DB: {listofThesisSubject}")
       
        return render_template('auth/profile.html', subjects=listofThesisSubject)
        
    except Exception as e:
        # It's good practice to log the full error for debugging
        print(f"Error fetching subjects: {e}")
        flash("An error occurred while fetching the list of subjects.", "error")
        # Redirect to a safe page on error
        return redirect(url_for('auth.profile'))

@thesislists_bp.route('/submitThesisTitle', methods=['POST'])
def submitThesisTitle():
    """
    Handles the submission of a new thesis title.
    """
    # Check if the user is logged in
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to submit a thesis title.", "error")
        return redirect(url_for('auth.login'))
    
    try:
        selected_subject_id = request.form.get('selectSubject')
        thesisTitle = request.form.get('title')
       
        if not thesisTitle or not selected_subject_id:
            flash("Please input your Thesis Title and select a subject.", "warning")
            return redirect(url_for('auth.profile'))
   
        new_thesisTitle = student_thesisTitle(
            subjectID=selected_subject_id,
            userID=user_id,
            title=thesisTitle,           
            teacherStatus=0, 
            researchStatus=0,
            researchNumber=None,
            research_approval_date=None # Explicitly set to None, matching the nullable column
        )        
        
        print("Title of the thesis:", new_thesisTitle)
        
        db.session.add(new_thesisTitle)
        db.session.commit()

        flash("Thesis Title Successfully added.", "success")
        return redirect(url_for('auth.profile'))

    except Exception as e:
        # Rollback the session in case of any error to prevent inconsistent data
        db.session.rollback()
        
        print(f"Database Error: {e}")
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for('auth.profile'))
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}



@thesislists_bp.route('/submitThesisFile', methods=['POST'])
def submitThesisFile():
    
    user_id = session.get('user_id')

    if not user_id:
        flash("Please Login", "warning")
        return redirect(url_for('auth.login'))

    try:
        # Get data from the form. researchNumber is retrieved here.
        lastname = request.form.get('lastName')
        firstname = request.form.get('firstName')
        abstract = request.form.get('abstract')
        
        title = request.form.get('title') 
        researchNumber = request.form.get('researchNumber') # This is the crucial line to get the research number from the form.
        
        college = request.form.get('selectCollege')
        course = request.form.get('selectCourse')
        copyright = request.form.get('CopyYY')
        pdf_file_object = request.files.get('file')

        print(f"Form Data: Last Name: {lastname}, First Name: {firstname}, Title: {title}, Research Number: {researchNumber}, College: {college}, Course: {course}, Copyright: {copyright}, File: {pdf_file_object}")
        
        
        missing_fields = [k for k, v in {
                "Last Name": lastname,
                "First Name": firstname,
                "Abstract": abstract,
                "Title": title,
                "Research Number": researchNumber,
                "College": college,
                "Course": course,
                "Copyright": copyright,
                "File": pdf_file_object
            }.items() if not v]

        if missing_fields:
                flash(f"Please fill in all required fields: {', '.join(missing_fields)}", "warning")
                return redirect(url_for('auth.profile'))

        
        # # ADDED researchNumber to the validation check
        # if not all([lastname, firstname, abstract, title, researchNumber, college, course, copyright, pdf_file_object]):
        #     flash("Please do not leave any fields blank.", "warning")
        #     return redirect(url_for('auth.profile'))
        
        # File handling logic (unchanged, but placed before object creation)
        if pdf_file_object and allowed_file(pdf_file_object.filename):
            filename = secure_filename(pdf_file_object.filename)
            upload_path = os.path.join(current_app.root_path, 'uploads', filename)
            
            pdf_file_object.save(upload_path)
            db_filename = filename 
            
            # ✅ Generate preview immediately after upload
            preview_folder = os.path.join(current_app.root_path, 'uploads', 'previews')
            os.makedirs(preview_folder, exist_ok=True)
            preview_path = os.path.join(preview_folder, f"preview_{filename}")

            try:
                generate_preview(upload_path, preview_path)
            except Exception as e:
                print(f"Preview generation failed: {e}")
        else:
            flash("Invalid file type. Only PDF files are allowed.", "warning")
            return redirect(url_for('auth.profile'))

        # CRITICAL FIX: Passing researchNumber to the Thesis constructor
        submittedFile = Thesis(
            last_name=lastname,
            first_name=firstname,
            title=title,
            abstract=abstract,
            copyright_yy=copyright,
            stud_college=college,
            course=course,
            user_id=user_id,
            thesis_status=1,
            pdf_file=db_filename,
            researchNumber=researchNumber, 
            upload_date= date.today()

        )
        
        print("THESIS NGA GI SUBMIT:", submittedFile)
        
        # Database commit logic
        db.session.add(submittedFile)

        db.session.commit()
        
                 

        flash("Thesis File Has Been Successfully Sent", "success")
        return redirect(url_for('auth.profile'))

    except Exception as e:
        print(f"Database Error:{e}")
        flash(f"Error occurred during process: {e}", "error")
        # Ensure rollback happens only if db is available
        try:
            db.session.rollback()
        except:
            pass
        return redirect(url_for('auth.profile'))
    
    
    
    

def scholar_scrape(query, page=1, per_page=25):
    """
    Uses OpenAlex API to fetch scholarly results reliably and for free.
    """
    try:
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "page": page,
            "per-page": per_page,
            "sort": "publication_year:desc"
        }
        # Adding a polite email header is recommended by OpenAlex
        headers = {"User-Agent": "ThesisSearchApp/1.0 (mailto:your-email@example.com)"}
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("results", []):
            authors_list = [a.get("author", {}).get("display_name", "Unknown") 
                           for a in item.get("authorships", [])]
            authors_str = ", ".join(authors_list) if authors_list else "Unknown Author"
            link = item.get("primary_location", {}).get("landing_page_url") or item.get("doi") or "#"

            results.append({
                "title": item.get("title", "No Title"),
                "authors": authors_str,
                "year": item.get("publication_year"),
                "link": link,
                "abstract": f"External Source: {item.get('type', 'Work')}",
                "source": "scholar"
            })
        
        # Meta info for pagination
        total_count = data.get("meta", {}).get("count", 0)
        return results, total_count
    except Exception as e:
        print(f"[ERROR] OpenAlex search failed: {e}")
        return [], 0


@thesislists_bp.route('/perform_search', methods=['POST'])
def perform_search():
    query = request.form.get('query', '').strip()
    source = request.form.get('search_source', 'combined')
    
    # Handle pagination inputs
    try:
        page = int(request.form.get('page', 1))
        per_page = int(request.form.get('per_page', 25))
    except ValueError:
        page = 1
        per_page = 25

    if not query:
        return jsonify({'error': 'Please enter a search term'}), 400

    results_list = []
    total_found = 0
    has_next = False

    try:
        # OFFSET for local DB pagination
        offset = (page - 1) * per_page

        # 1. LOCAL REPOSITORY SEARCH (Source is 'combined' or 'theses')
        if source in ['combined', 'theses']:
            # Use .limit and .offset to prevent loading entire DB
            thesis_query = Thesis.query.filter(
                or_(
                    Thesis.title.like(f"%{query}%"),
                    Thesis.first_name.like(f"%{query}%"),
                    Thesis.last_name.like(f"%{query}%"),
                    Thesis.abstract.like(f"%{query}%")
                )
            )
            
            # Get total for local search
            local_total = thesis_query.count()
            local_theses = thesis_query.offset(offset).limit(per_page).all()

            for t in local_theses:
                results_list.append({
                    'title': t.title,
                    'authors': f"{t.first_name} {t.last_name}",
                    'year': t.copyright_yy,
                    'link': f"/preview_thesis/{t.id}",
                    'abstract': (t.abstract[:200] + '...') if t.abstract else '',
                    'source': 'thesis'
                })
            
            total_found += local_total
            if local_total > (offset + per_page):
                has_next = True

        # 2. EXTERNAL SCHOLAR SEARCH (Source is 'combined' or 'scholar')
        if source in ['combined', 'scholar']:
            # Adjust per_page if combined to keep total manageable, 
            # or keep at 25 as requested
            scholar_res, scholar_total = scholar_scrape(query, page=page, per_page=per_page)
            results_list.extend(scholar_res)
            
            total_found += scholar_total
            if scholar_total > (page * per_page):
                has_next = True

        # 3. SORTING (Theses first in combined view)
        if source == 'combined':
            results_list = sorted(results_list, key=lambda x: x['source'] != 'thesis')
            # Truncate to per_page if both sources returned items to keep UI consistent
            results_list = results_list[:per_page]

    except Exception as e:
        print(f"[ERROR] perform_search: {e}")
        return jsonify({'error': "An error occurred while processing your search."}), 500

    return jsonify({
        'query': query,
        'count': total_found,
        'results': results_list,
        'page': page,
        'has_next': has_next
    })



@thesislists_bp.route('/delete_thesis/<int:thesis_id>', methods=['POST'])
def delete_thesis(thesis_id):
    
    thesis_record = student_thesisTitle.query.get_or_404(thesis_id)

    try:
        db.session.delete(thesis_record)
        db.session.commit()
        print("Thesis Title DELETED successfully!")
        flash("Thesis Title DELETED successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting thesis: {e}")
        flash("An error occurred while deleting the thesis.", "error")

    return redirect(url_for('auth.profile'))

@thesislists_bp.route('edit_thesis-title/<int:thesis_id>',methods=['POST'])
def edit_thesis_title(thesis_id):
    thesis = student_thesisTitle.query.get_or_404(thesis_id)
    new_title = request.form.get('new_title')

    if new_title and new_title.strip():
        thesis.title = new_title
        try:
            db.session.commit()
            flash('Thesis title updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the title: {e}', 'danger')
    else:
        flash('Thesis title cannot be empty.', 'warning')

    return redirect(url_for('auth.profile'))



def generate_preview(file_path, preview_path):
    reader = PdfReader(file_path)
    writer = PdfWriter()

    total_pages = len(reader.pages)
    preview_limit = max(1, int(total_pages * 0.2))

    for i in range(preview_limit):
        writer.add_page(reader.pages[i])

    with open(preview_path, "wb") as f:
        writer.write(f)


# this will be the route for preview of the thesis file before downloading or viewing online of 20% of pdf file
@thesislists_bp.route('/preview_thesis/<int:thesis_id>')
def preview_thesis(thesis_id):
    """Renders the preview page which will contain the PDF viewer."""
    thesis = Thesis.query.get_or_404(thesis_id)
    return render_template('theses/preview.html', thesis=thesis)



@thesislists_bp.route('/get_preview_pdf/<int:thesis_id>')
def get_preview_pdf(thesis_id):
      
    thesis = Thesis.query.get_or_404(thesis_id)

    filename = thesis.pdf_file.replace('uploads/', '').replace('uploads\\', '')
    file_path = os.path.join(current_app.root_path, 'uploads', filename)

    preview_folder = os.path.join(current_app.root_path, 'uploads', 'previews')
    os.makedirs(preview_folder, exist_ok=True)

    preview_path = os.path.join(preview_folder, f"preview_{filename}")

    # ✅ Generate preview ONLY once
    if not os.path.exists(preview_path):
        reader = PdfReader(file_path)
        writer = PdfWriter()

        total_pages = len(reader.pages)
        preview_limit = max(1, int(total_pages * 0.2))

        for i in range(preview_limit):
            writer.add_page(reader.pages[i])

        with open(preview_path, "wb") as f:
            writer.write(f)

    return send_file(preview_path, mimetype='application/pdf')

# watermarking function (not currently used, but can be integrated later if needed)
def add_watermark(input_pdf_path, output_pdf_path, watermark_text):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica", 40)
        can.setFillColorRGB(0.5, 0.5, 0.5, alpha=0.3)  # Light gray with transparency
        can.saveState()
        can.translate(300, 400)  # Position the watermark
        can.rotate(45)  # Rotate the watermark
        can.drawCentredString(0, 0, watermark_text)
        can.restoreState()
        can.save()

        packet.seek(0)
        watermark_pdf = PdfReader(packet)
        page.merge_page(watermark_pdf.pages[0])
        writer.add_page(page)

    with open(output_pdf_path, "wb") as f:
        writer.write(f)
    
    
#instead of modal I used the separate page for adding thesis title and file submission for better user experience and to avoid the issues with modal form submission.
@thesislists_bp.route('/addThesis', methods=['GET'])
def addThesis():
    colleges = College.query.all()
    # Get pre-fill data from query parameters
    pre_title = request.args.get('title', '')
    pre_research_number = request.args.get('research_number', '')
    
    return render_template('theses/addthesis.html', colleges=colleges, pre_title=pre_title, pre_research_number=pre_research_number)

@thesislists_bp.route('/get_courses')
def get_courses():
    college_id = request.args.get('college_id', type=int)
    
    if not college_id:
            return jsonify({'error': 'College  is Required'}), 400    
    courses = Course.query.filter_by(collegeID=college_id).all()
    courses_id = [{
        'id': course.id, 
        'courseName': course.courseName}
                  for course in courses]
    
    return jsonify(courses_id)


#this route is for unaproved thesis title of the student
@thesislists_bp.route('/unapproved_thesis')
def unapproved_thesis():
    unapproved_thesis_list= student_thesisTitle.query.filter_by(teacherStatus=2).all()
    return render_template('theses/unapproved_thesis.html', unapproved_thesis_list=unapproved_thesis_list)
    
