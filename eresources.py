import os
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, session, url_for, redirect, jsonify, request, flash,send_file,current_app
from models import User, Thesis, student_thesisTitle, College, Course,EResourceActivity, EResource# Assuming these are your ORM models
from werkzeug.utils import secure_filename # Recommended for secure file handling
from extension import db
from models import EResource, EResourceActivity, ThesisActivity
from sqlalchemy import func # Import func for database functions like count


# Define the allowed file extensions for security
ALLOWED_EXTENSIONS = {'pdf', 'epub', 'doc', 'docx', 'ppt', 'pptx'}

eresources_bp = Blueprint('eresources', __name__, template_folder="templates")

def get_college_resources_with_stats(college_id):
    """
    Helper function to fetch theses for a specific college with view and download counts.
    """
    # Subqueries to count views and downloads per thesis
    view_counts = db.session.query(
        ThesisActivity.thesis_id,
        func.count(ThesisActivity.id).label('view_count')
    ).filter(ThesisActivity.activity_type == 'view').group_by(ThesisActivity.thesis_id).subquery()

    download_counts = db.session.query(
        ThesisActivity.thesis_id,
        func.count(ThesisActivity.id).label('download_count')
    ).filter(ThesisActivity.activity_type == 'download').group_by(ThesisActivity.thesis_id).subquery()

    # Join Thesis with College and the count subqueries
    results = db.session.query(Thesis, view_counts.c.view_count, download_counts.c.download_count)\
       .join(College, Thesis.stud_college == College.id)\
       .outerjoin(view_counts, Thesis.id == view_counts.c.thesis_id)\
       .outerjoin(download_counts, Thesis.id == download_counts.c.thesis_id)\
       .filter(College.id == college_id).all()
    
    # Attach counts to thesis objects
    resources_list = []
    for t, v, d in results:
        t.view_count = v if v else 0
        t.download_count = d if d else 0
        resources_list.append(t)
        
    return resources_list

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@eresources_bp.route('/uploadResources')
def uploadResources():
   
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    # You can pass user or other data to the template if needed
    #return render_template('eresources/uploadEresources.html')
    # return redirect(url_for('auth.eresourcesPortal'))
    eresourcesDashboard = EResource.query.all()
    return render_template('eresources/add-Eresources.html', user=user, eresourcesDashboard=eresourcesDashboard)


# list of ejournals to be shown in the home page diri ni gikan ang sa home.html na E-Journal Articles
@eresources_bp.route('/eresources-EJournalList')
def eresources_EJournalList():
   
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    myEjournals = EResource.query.filter_by(resource_type='Ejournal').all()
    print(myEjournals)
    
    return render_template('eresources/e-journalList.html', user=user, myEjournals=myEjournals)


# list of ebooks to be shown in the home page diri ni gikan ang sa home.html na E-Book collections
@eresources_bp.route('/eresources-EBookList')
def eresources_EBookList():
   
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    myEbooks = EResource.query.filter_by(resource_type='Ebook').all()
    print(myEbooks)
    
    return render_template('eresources/e-booksList.html', user=user, myEbooks=myEbooks)  


#stats for thesis views and downloads
@eresources_bp.route('/thesis/<int:id>/stats')
def thesis_stats(id):
    views = ThesisActivity.query.filter_by(
        thesis_id=id,
        activity_type='view'
    ).count()

    downloads = ThesisActivity.query.filter_by(
        thesis_id=id,
        activity_type='download'
    ).count()

    return jsonify({
        'views': views,
        'downloads': downloads
    })


#list of all e-resources to be shown in the e-resources page thesis ug Disertation 
@eresources_bp.route('/eresources-List')
def eresources_List():
    
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    myResourcesList = Thesis.query.all()
    
    
    return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList) 



#views and download logging for e-journals and e-boks --------------------------------------------------- logging views for ebooks and ejournals

@eresources_bp.route('/eresource/<int:id>/view', methods=['POST'])
def log_eresource_view(id): 
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        
        if not user_id:
            # If this is an AJAX call, 401 Unauthorized is better than 500
            return jsonify({'status': 'error', 'message': "Please Login to view"}), 401

        # Correct way to instantiate the model
        activity = EResourceActivity(
            eresource_id=id, 
            user_id=user_id, 
            activity_type='view',
            activity_date=datetime.now(timezone.utc) # Using modern UTC method
        )
        
        db.session.add(activity)
        db.session.commit()
        
        print(f"Activity logged: {activity}")
        return '', 200
        
    except Exception as e:
        db.session.rollback() # Good practice: roll back on error
        print(f"An error occurred: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    
#views and download logging for e-journals and e-boks --------------------------------------------------- logging Download for ebooks and ejournals

@eresources_bp.route('/eresource/<int:id>/download', methods=['POST'])
def log_eresource_download(id): 
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        
        eresoucesMaterials= EResource.query.get(id)

        if not user_id:
            # If this is an AJAX call, 401 Unauthorized is better than 500
            return jsonify({'status': 'error', 'message': "Please Login to download"}), 401

        # Correct way to instantiate the model
        activity = EResourceActivity(
            eresource_id=id, 
            user_id=user_id, 
            activity_type='download',
            activity_date=datetime.now(timezone.utc) # Using modern UTC method
        )
        
        db.session.add(activity)
        db.session.commit()
        
        print(f"Activity logged: {activity}")
        # return '', 200
        
        file_path = os.path.join(current_app.root_path, 'uploads', eresoucesMaterials.file_path)
        if not os.path.exists(file_path):
         return "File not found", 404
        return send_file(file_path, as_attachment=True, download_name=eresoucesMaterials.title + ".pdf")
        
    except Exception as e:
        db.session.rollback() # Good practice: roll back on error
        print(f"An error occurred: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    
    

#view and download logging for theses
@eresources_bp.route('/thesis/<int:id>/view', methods=['POST'])
def log_view(id):
    db.session.add(
        ThesisActivity(thesis_id=id, activity_type='view')
    )
    db.session.commit()
    return '', 204


@eresources_bp.route('/thesis/<int:id>/download', methods=['POST'])
def log_download(id):
    db.session.add(
        ThesisActivity(thesis_id=id, activity_type='download')
    )
    db.session.commit()
    return '', 204


#agriculture e-resources list
@eresources_bp.route('/eresources-AgriList')
def eresources_AgriList():
   
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
     
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    myResourcesList= get_college_resources_with_stats(2)
     
    return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)


# engineering e-resources list
@eresources_bp.route('/eresources-EngineeringList')
def eresources_EngineeringList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(14)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #information technology e-resources list 
@eresources_bp.route('/eresources-ITList')
def eresources_ITList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(3)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #nursing list health sciences of e-resources
@eresources_bp.route('/eresources-NursingList')
def eresources_NursingList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(1)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #arts and sciences e-resources list
@eresources_bp.route('/eresources-ArtsAndSciencesList')
def eresources_ArtsAndSciencesList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(15)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #business management e-resources list
@eresources_bp.route('/eresources-BusinessManagementList')
def eresources_BusinessManagementList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(9)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #hospitality management e-resources list
@eresources_bp.route('/eresources-HospitalityManagementList')
def eresources_HospitalityManagementList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(7)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #education e-resources list
@eresources_bp.route('/eresources-EducationList')
def eresources_EducationList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(17)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #social work and sciences e-resources list
@eresources_bp.route('/eresources-SocialWorkList')
def eresources_SocialWorkList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(18)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #veterinarian e-resources list
@eresources_bp.route('/eresources-VeterinarianList')
def eresources_VeterinarianList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(16)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
 #forestry e-resources list
@eresources_bp.route('/eresources-ForestryList')
def eresources_ForestryList():
    
     if 'user_id' not in session:
          flash("You need to log in to access this page", "error")
          return redirect(url_for('auth.login'))
      
     user_id = session.get('user_id')
     user = User.query.get(user_id)
     
     myResourcesList= get_college_resources_with_stats(8)
     
     return render_template('eresources/e-thesisList.html', user=user, myResourcesList=myResourcesList)
 
 
@eresources_bp.route('/submit-resource', methods=['POST'])
def submit_resource():
    
    if 'user_id' not in session:
        flash("You need to be logged in to upload resources.", "error")
        return redirect(url_for('auth.login'))

    if 'resourceFile' not in request.files:
        flash('No file part in the request', 'error')
        return redirect(request.url)

    file = request.files['resourceFile']

    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        # Secure the filename to prevent directory traversal attacks
        filename = secure_filename(file.filename)

        # Define the relative path for the database (e.g., 'uploads/e-resources/filename.pdf')
        relative_path = os.path.join('uploads', 'e-resources', filename).replace('\\', '/')

        # Construct the full, absolute path for saving the file on the server
        # This joins the project root, 'static', and the relative path
        absolute_save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', relative_path)

        os.makedirs(os.path.dirname(absolute_save_path), exist_ok=True)
        file.save(absolute_save_path)

        # Retrieve all the other form data
        resource_type = request.form.get('resourceType')
        title = request.form.get('title')
        author = request.form.get('author')
        year = request.form.get('year')
        publisher = request.form.get('publisher')
        doi = request.form.get('doi')
        issn_isbn = request.form.get('issn_isbn')
        subject = request.form.get('subject')
        staff_notes = request.form.get('staffNotes')
        user_id = session.get('user_id')

        # E-Journal specific fields
        volume = request.form.get('volume')
        issue = request.form.get('issue')
        pages = request.form.get('pages')

        # Create a new EResource object with all the data new_resource = EResource(
        new_resource = EResource(
            resource_type=resource_type,
            title=title,
            author=author, # The form uses 'authors', but the model might use 'author'. Let's assume model has 'authors'
            year=int(year) if year else None,
            publisher=publisher,
            doi=doi,
            issn_isbn=issn_isbn,
            subject=subject,
            staff_notes=staff_notes,
            volume=int(volume) if volume else None,
            issue=int(issue) if issue else None,
            pages=pages,
            file_path=relative_path, # Store the clean, relative path in the database
            uploaded_by_id=user_id
        )

        print(new_resource)
        db.session.add(new_resource)
        db.session.commit()
        flash("E-Resource uploaded successfully!", "success")
        return jsonify({"status": "success", "message": "Uploaded successfully"})

        # return redirect(url_for('auth.EresourcesPortal')) # Redirect back to the main e-resources page
    else:
        flash('File type not allowed.', 'error')
        # return redirect(url_for('auth.EresourcesPortal'))
    return jsonify({"status": "error", "message": "Upload Unsuccessfully - Invalid file type"})


@eresources_bp.route('/get-resource-details/<int:resource_id>')
def get_resource_details(resource_id):
   
    if 'user_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    resource = EResource.query.get_or_404(resource_id)

    return jsonify({
        'id': resource.id,
        'resource_type': resource.resource_type,
        'title': resource.title,
        'author': resource.author,
        'year': resource.year,
        'publisher': resource.publisher,
        'doi': resource.doi,
        'issn_isbn': resource.issn_isbn,
        'subject': resource.subject,
        'staff_notes': resource.staff_notes,
        'volume': resource.volume,
        'issue': resource.issue,
        'pages': resource.pages,
    })

@eresources_bp.route('/edit-resource/<int:resource_id>', methods=['POST'])
def edit_resource(resource_id):
    if 'user_id' not in session:
        flash("You need to be logged in to edit resources.", "error")
        return redirect(url_for('auth.login'))

    resource = EResource.query.get_or_404(resource_id)

    # Update fields from the form
    resource.title = request.form.get('title')
    resource.author = request.form.get('authors') # Corrected from 'author' to 'authors' to match the form
    resource.year = int(request.form.get('year')) if request.form.get('year') else None
    resource.publisher = request.form.get('publisher')
    resource.doi = request.form.get('doi')
    resource.issn_isbn = request.form.get('issn_isbn')
    resource.subject = request.form.get('subject')
    resource.staff_notes = request.form.get('staffNotes')
    resource.volume = int(request.form.get('volume')) if request.form.get('volume') else None
    resource.issue = int(request.form.get('issue')) if request.form.get('issue') else None
    resource.pages = request.form.get('pages')

    db.session.commit()
    flash("E-Resource updated successfully!", "success")
    return redirect(url_for('auth.EresourcesPortal'))

@eresources_bp.route('/delete-resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    if 'user_id' not in session:
        flash("You need to be logged in to delete resources.", "error")
        return redirect(url_for('auth.login'))

    resource = EResource.query.get_or_404(resource_id)
    db.session.delete(resource)
    db.session.commit()
    flash("E-Resource deleted successfully!", "success")
    return redirect(url_for('auth.EresourcesPortal'))


@eresources_bp.route('/get_details/<resource_type>/<int:resource_id>')
def get_details(resource_type, resource_id):
    """
    API endpoint to get details for a resource (Thesis or EResource).
    Returns JSON with title, abstract/subject, and view count.
    """
    user_id = session.get('user_id')

    if resource_type == 'thesis':
        resource = Thesis.query.get_or_404(resource_id)
        view_count = ThesisActivity.query.filter_by(thesis_id=resource_id, activity_type='view').count()
        download_count = ThesisActivity.query.filter_by(thesis_id=resource_id, activity_type='download').count()
        # Log the view activity
        view_activity = ThesisActivity(thesis_id=resource_id, user_id=user_id, activity_type='view')
        db.session.add(view_activity)
        db.session.commit()

        # Fetch related names for the modal
        college = College.query.get(resource.stud_college)
        course = Course.query.get(resource.course)

        return jsonify({
            'title': resource.title,
            'abstract': resource.abstract or "No abstract available.",
            'view_count': view_count + 1,
            'download_count': download_count,
            'first_name': resource.first_name,
            'last_name': resource.last_name,
            'copyright_year': resource.copyright_yy,
            'course_name': course.courseName if course else "N/A",
            'college_name': college.name if college else "N/A"
        })
    elif resource_type in ['Ebook', 'Ejournal']:
        resource = EResource.query.get_or_404(resource_id)
        view_count = EResourceActivity.query.filter_by(eresource_id=resource_id, activity_type='view').count()
        download_count = EResourceActivity.query.filter_by(eresource_id=resource_id, activity_type='download').count()
        # Log the view activity
        view_activity = EResourceActivity(eresource_id=resource_id, user_id=user_id, activity_type='view')
        db.session.add(view_activity)
        db.session.commit()
        return jsonify({
            'title': resource.title,
            'description': resource.subject or "No description available.",
            'view_count': view_count + 1, # Include the new view
            'download_count': download_count
        })
    else:
        return jsonify({'error': 'Invalid resource type'}), 400


@eresources_bp.route('/record_download/<resource_type>/<int:resource_id>', methods=['POST'])
def record_download(resource_type, resource_id):
    """
    API endpoint to record a download activity for a resource.
    """
    user_id = session.get('user_id')

    try:
        if resource_type == 'thesis':
            download_activity = ThesisActivity(thesis_id=resource_id, user_id=user_id, activity_type='download')
            db.session.add(download_activity)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Thesis download recorded.'})
        elif resource_type in ['Ebook', 'Ejournal']:
            download_activity = EResourceActivity(eresource_id=resource_id, user_id=user_id, activity_type='download')
            db.session.add(download_activity)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'EResource download recorded.'})
        else:
            return jsonify({'error': 'Invalid resource type'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@eresources_bp.route('/list_of_eresources')
def list_of_eresources():
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    list_of_eresourcesDashboard = EResource.query.all()
    

    # You can pass user or other data to the template if needed
    return render_template('eresources/list_of_eresources.html', user=user,  
    list_of_eresourcesDashboard=list_of_eresourcesDashboard)
    
    
# analytics data for e-resources
@eresources_bp.route('/eresources_analytics_data')
def eresources_analytics_data():
    data = {
        'total_eresources': EResource.query.count(),
        'total_views': db.session.query(func.count(EResourceActivity.id)).filter(EResourceActivity.activity_type == 'view').scalar(),
        'total_downloads': db.session.query(func.count(EResourceActivity.id)).filter(EResourceActivity.activity_type == 'download').scalar()
    }
    return jsonify(data)

@eresources_bp.route('/post_thesis<int:thesis_id>', methods=['POST'])
def post_thesis(thesis_id):
    if 'user_id' not in session:
        flash ("You need to login to access this page.", "error")   
        return redirect(url_for('auth.login'))
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    thesis = Thesis.query.get(thesis_id)

    if not user or user.level != 4:
        flash ("You do not have Permission to perform this action", "error")
        return redirect(url_for('auth.login')) 

    if not thesis:
        flash("Thesis not found.", "error")
        return redirect(url_for('informationDesk.frontdeskPortal'))

    if thesis.thesis_status != 1: 
        flash("Only approved theses can be posted.", "error")
        return redirect(url_for('informationDesk.frontdeskPortal'))

    thesis.thesis_status = 0 
    thesis.posted_by = user.id  
    thesis.posted_at = func.now()

    try:
        from app import db
        db.session.commit()
        flash("Thesis posted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while posting the thesis.", "error")

    return redirect(url_for('informationDesk.frontdeskPortal')) 

@eresources_bp.route('/report_eresource')
def report_eresource():
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    query = EResource.query

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)

            query = query.filter(
                EResource.uploaded_date >= start_date,
                EResource.uploaded_date < end_date
            )
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'error')

    total_eresources = query.count()
    myResourcesList = query.order_by(EResource.uploaded_date.desc()).all()

    return render_template(
        'eresources/eresources_report.html',
        user=user,
        myResourcesList=myResourcesList,
        total_eresources=total_eresources,
        start_date=start_date_str,
        end_date=end_date_str
    )
    
    
    #search functionality for e-resources
@eresources_bp.route('/search_eresources')
def search_eresources():
    query = request.args.get('query')
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if query:
        search_pattern = f"%{query}%"
        results = EResource.query.filter(
            (EResource.title.ilike(search_pattern)) |
            (EResource.author.ilike(search_pattern)) |
            (EResource.subject.ilike(search_pattern))
        ).all()
    else:
        results = []
        
    return render_template('eresources/search_eresources.html', user=user, results=results, query=query)



    # Route for e-resources individual analytics page
@eresources_bp.route('/eresources-analytics/<int:id>')
def eresources_analytics(id):
    if 'user_id' not in session:
        flash("You need to log in to access this page", "error")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get the e-resource
    eresource = EResource.query.get(id)
    if not eresource:
        flash("E-Resource not found", "error")
        return redirect(url_for('eresources.report_eresource'))
    
    # Get statistics for this e-resource
    total_views = db.session.query(func.count(EResourceActivity.id)).filter(
        EResourceActivity.eresource_id == id,
        EResourceActivity.activity_type == 'view'
    ).scalar()
    
    total_downloads = db.session.query(func.count(EResourceActivity.id)).filter(
        EResourceActivity.eresource_id == id,
        EResourceActivity.activity_type == 'download'
    ).scalar()
    
    return render_template('eresources/e-resources_individual_report.html', 
                         user=user, 
                         eresource=eresource,
                         total_views=total_views or 0,
                         total_downloads=total_downloads or 0)

# API endpoint to get activity data for individual e-resource with date filtering
@eresources_bp.route('/api/eresource-activities/<int:id>')
def get_eresource_activities(id):
    """
    Returns activity data for a specific e-resource, filtered by date range
    Query parameters: start_date, end_date (format: YYYY-MM-DD)
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Validate e-resource exists
    eresource = EResource.query.get(id)
    if not eresource:
        return jsonify({'error': 'E-Resource not found'}), 404
    
    # Build query
    query = EResourceActivity.query.filter(EResourceActivity.eresource_id == id)
    
    # Apply date filters if provided
    if start_date:
        from datetime import datetime as dt
        try:
            start = dt.strptime(start_date, '%Y-%m-%d')
            query = query.filter(EResourceActivity.activity_date >= start)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
    
    if end_date:
        from datetime import datetime as dt
        try:
            end = dt.strptime(end_date, '%Y-%m-%d')
            # Add 1 day to include the entire end date
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(EResourceActivity.activity_date <= end)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
    
    # Get activities with user info
    activities = query.order_by(EResourceActivity.activity_date.desc()).all()
    
    # Format data for DataTable
    data = []
    for idx, activity in enumerate(activities, 1):
        user = User.query.get(activity.user_id) if activity.user_id else None
        data.append({
            'index': idx,
            'user': user.first_name + ' ' + user.last_name if user else 'Guest',
            'activity_type': activity.activity_type.upper(),
            'activity_date': activity.activity_date.strftime('%Y-%m-%d %I:%M %p'),
            'activity_date_sort': activity.activity_date.isoformat()  # For sorting
        })
    
    return jsonify(data)

@eresources_bp.route('/eresources_individual_report.<int:id>')
def ererouces_individual_report(id):
    if 'user_id' not in session:
        flash("You need to login")
        return redirect(url_for('auth.login'))
    
    #query to get the information of the eresources and the eresources_Activity
