from flask import Blueprint, session, redirect,render_template, flash, url_for
from extension import db
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# import matplotlib.pyplot as plt 
from models import student_thesisTitle, User, Subject, Thesis
from flask import current_app
from datetime import datetime
from sqlalchemy.orm import aliased, joinedload
from flask import request, jsonify

research_bp= Blueprint("research",__name__, template_folder="templates")

@research_bp.route('/researchPortal')
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
        .filter(student_thesisTitle.teacherStatus == 2) 
        .all()
    ) 

    countPendingThesis = db.session.query(student_thesisTitle).filter(
        student_thesisTitle.teacherStatus==2,
        student_thesisTitle.researchStatus==1).count()
  
    approved_count = db.session.query(student_thesisTitle).filter_by(teacherStatus=1).count()

    # Now, pass the user object to the template
    return render_template('research/researchAdmin.html',approved_count=approved_count, user=user, research_list=research_list, countPendingThesis=countPendingThesis)


@research_bp.route('/loadData')
def loadData():
    
    if 'user_id' not in session:
        flash("You need to log in to access this page. ", "error")
        return redirect(url_for('auth.login'))
    
    user_id= session.get('user_id')
    user= User.query.get(user_id)

    
@research_bp.route('/approved_thesis')
def approved_thesis():
    if 'user_id' not in session:
        flash("You need to log in to access this page.", "error")
        return redirect(url_for('auth.login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user or user.level != 2:
        flash("You do not have permission to view this page.", "error")
        return redirect(url_for('home'))

    # Get date range from request arguments
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Base query
    query = db.session.query(student_thesisTitle).options(
        joinedload(student_thesisTitle.student).joinedload(User.course_relation)
    ).filter(student_thesisTitle.researchStatus == 2)

    # Apply date filters if provided
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            # To include the whole day, filter from the start of the day
            query = query.filter(student_thesisTitle.research_approval_date >= start_date)
        except ValueError:
            flash("Invalid start date format. Please use YYYY-MM-DD.", "warning")
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # To include the whole day, filter until the end of the day
            end_of_day = end_date.replace(hour=23, minute=59, second=59)
            query = query.filter(student_thesisTitle.research_approval_date <= end_of_day)
        except ValueError:
            flash("Invalid end date format. Please use YYYY-MM-DD.", "warning")

    return render_template(
        'research/approved_thesis.html', 
        approved_thesis_list=query.all(),
        start_date=start_date_str,
        end_date=end_date_str
    )

def generate_unique_research_number():
    """
    Generates a unique, sequential research number as a string in the format YYYY-NNNN.
    Example: 2024-0001
    """
    current_year = datetime.now().year
    # Define the search pattern for the current year, e.g., "2024-"
    year_prefix = f"{current_year}-"

    # Find the highest research number within the current year's range
    last_thesis = student_thesisTitle.query.filter(
        student_thesisTitle.researchNumber.startswith(year_prefix)
    ).order_by(student_thesisTitle.researchNumber.desc()).first()

    if last_thesis and last_thesis.researchNumber:
        # Extract the numeric part, increment it, and format it back
        last_num_str = last_thesis.researchNumber.split('-')[-1]
        next_num = int(last_num_str) + 1
        return f"{year_prefix}{next_num:04d}" # Formats to 4 digits, e.g., 0002
    else:
        # Otherwise, this is the first one of the year
        return f"{year_prefix}0001"


@research_bp.route('/approve_deny_thesis/<int:thesis_id>/<action>', methods=['POST'])
def approve_deny_thesis(thesis_id, action):
    """
    Approves or denies a thesis submission based on the 'action' provided in the URL.
    Requires user to be authenticated and have a permission level of 2 (Teacher/Admin).
    """
    # Check for user authentication and authorization (level 2)
    user_id = session.get('user_id')    
    user = User.query.get(user_id)    
    
    if not user or user.level != 2:
        flash("You do not have permission to perform this action.", "error")
        # Ensure 'research' is the correct blueprint name for researchPortal
        return redirect(url_for('auth.login'))

    thesis = student_thesisTitle.query.get_or_404(thesis_id)    
    
    try:
        message = ""
        category = "success"
        if action == 'approve':
            # Generate and assign the unique research number
            thesis.researchNumber = generate_unique_research_number()
            thesis.research_approval_date = datetime.utcnow()
            thesis.researchStatus = 2 # Approved
            db.session.add(thesis)
            db.session.commit()

            # Ensure thesis.researchNumber is not None before trying to display it
            research_num_display = thesis.researchNumber if thesis.researchNumber else "N/A"
            message = f"Thesis '{thesis.title}' has been successfully approved. Research number: {research_num_display}"

        elif action == 'deny':
            thesis.research_approval_date = None # Ensure date is cleared on denial
            thesis.researchStatus = 0 # Denied
            db.session.add(thesis)
            db.session.commit()
            message = f"Thesis '{thesis.title}' has been denied."
            category = "warning"
        
        else:
            message = "Invalid action specified."
            category = "error"

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': category, 'message': message})
        
        flash(message, category)

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        error_msg = f"An error occurred while processing the thesis: {str(e)}"
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': error_msg}), 500
        flash(error_msg, "error")

    # return redirect(url_for('research.researchPortal'))
    
    return redirect(request.referrer)

@research_bp.route('/check_title', methods=['POST'])
def check_title():
   
    if 'user_id' not in session or User.query.get(session['user_id']).level != 2:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    title_to_check = data.get('title')
    current_thesis_id = data.get('thesis_id')

    if not title_to_check or not current_thesis_id:
        return jsonify({'error': 'Missing title or thesis ID'}), 400

    # Perform a case-insensitive search for similar titles, excluding the current one
    similar_theses = student_thesisTitle.query.filter(
        student_thesisTitle.title.ilike(f"%{title_to_check}%"),
        student_thesisTitle.id != current_thesis_id
    ).all()

    results = [{'id': thesis.id, 'title': thesis.title} for thesis in similar_theses]

    return jsonify(results)

@research_bp.route('/view/<int:thesis_id>')
def view_details(thesis_id):
    
    # --- 1. Authentication & Authorization ---
    if 'user_id' not in session:
        flash("You need to log in to access this page.", "error")
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user or user.level != 2:
        flash("You do not have permission to view this page.", "error")
        return redirect(url_for('home'))

    # --- 2. Data Fetching Query ---
    # Use aliases to distinguish between the student user and the teacher user
    StudentUser = aliased(User, name='student_user')
    TeacherUser = aliased(User, name='teacher_user')

    # Query for the thesis and join all related tables
    details = db.session.query(
        student_thesisTitle,
        StudentUser,
        Subject,
        TeacherUser
    ).join(
        StudentUser, student_thesisTitle.userID == StudentUser.id
    ).join(
        Subject, student_thesisTitle.subjectID == Subject.id
    ).join(
        TeacherUser, Subject.user_ID == TeacherUser.id
    ).filter(
        student_thesisTitle.id == thesis_id
    ).first_or_404()

    # --- 3. Render Template ---
    return render_template('research/view_details.html', details=details)


@research_bp.route('/check_title_similarity', methods=['POST'])
def check_title_similarity():
    input_title = request.form.get('check_title', '').strip()
    
    if not input_title:
        return jsonify({'error': 'No title provided'}), 400

    # 1. Preprocess the input title: lowercase, remove punctuation, split into words
    def get_words(text):
        # Remove common "stop words" to make the comparison more meaningful
        stop_words = {'a', 'an', 'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'is'}
        words = re.findall(r'\w+', text.lower())
        return set(w for w in words if w not in stop_words)

    input_words = get_words(input_title)
    if not input_words:
        return jsonify({'results': [], 'message': 'Title contains only stop words.'})

    # 2. Fetch all existing titles from the repository
    all_theses = Thesis.query.all()
    results = []

    for thesis in all_theses:
        repo_words = get_words(thesis.title)
        
        # Calculate Intersection (words found in both)
        common_words = input_words.intersection(repo_words)
        
        # Calculate Jaccard Similarity Percentage
        # formula: (common words) / (total unique words in both)
        union_words = input_words.union(repo_words)
        
        if not union_words:
            continue
            
        similarity_percent = (len(common_words) / len(union_words)) * 100

        # Only show results with some similarity (e.g., > 10%)
        if similarity_percent > 10:
            results.append({
                'id': thesis.id,
                'title': thesis.title,
                'author': f"{thesis.first_name} {thesis.last_name}",
                'similarity': round(similarity_percent, 2),
                'matched_words': list(common_words)
            })

    # 3. Sort by highest similarity
    results = sorted(results, key=lambda x: x['similarity'], reverse=True)

    return jsonify({
        'original_title': input_title,
        'results': results
    })    