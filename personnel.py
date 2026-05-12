from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from sqlalchemy import desc, literal
from models import db, Personnel, User, College, Course, Thesis, EResource, ThesisActivity, EResourceActivity
import os
import csv
import io
from werkzeug.utils import secure_filename
import pandas as pd


# Initialize the Blueprint
personnel_bp = Blueprint('personnel', __name__)

# Route for the personnel page

@personnel_bp.route('/personnel', methods=['GET', 'POST'])
def personnel():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if not user_id:
            flash('Please select a user.', 'danger')
            return redirect(url_for('personnel.personnel'))
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('personnel.personnel'))
        
        full_name = request.form['full_name']
        position = request.form.get('position', 'Staff')
        
        # Get the access_level and convert it to an integer
        access_level_str = request.form['access_level']
        try:
            access_level = int(access_level_str)
        except (ValueError, KeyError):
            flash('Invalid access level provided.', 'danger')
            return redirect(url_for('personnel.personnel'))

        # Update user level
        user.level = access_level

        file = request.files.get('profile_picture') # Use .get() to avoid KeyError

        profile_picture_path = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            profile_picture_path = os.path.join('static/uploads', filename)

        new_personnel = Personnel(
            userID=user.id,
            full_name=full_name, 
            position=position,
            access_level=access_level, # Use the integer value
            profile_picture=profile_picture_path
        )
        db.session.add(new_personnel)
        db.session.commit()

        flash('Personnel added successfully!', 'success')
        return redirect(url_for('auth.dashboard'))

    personnel_list = User.query.filter(User.level > 0).all()    
    
    return render_template('personnel/personnel.html', personnel_list=personnel_list)



# Route for editing personnel
@personnel_bp.route('/personnel/edit/<int:id>', methods=['POST'])
def edit_personnel(id):
    personnel = Personnel.query.get_or_404(id)
    
    personnel.full_name = request.form['full_name']
    personnel.position = request.form['position']
    
    # Get the access_level and convert it to an integer
    access_level_str = request.form.get('access_level')
    if access_level_str:
        try:
            personnel.access_level = int(access_level_str)
        except ValueError:
            flash('Invalid access level provided.', 'danger')
            return redirect(url_for('personnel.personnel'))
    
    file = request.files.get('profile_picture')
    if file and file.filename:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        personnel.profile_picture = os.path.join('static/uploads', filename)

    db.session.commit()
    success_message = 'Personnel updated successfully!'

    # CORRECTED LINE: Use the blueprint name ('auth') and the function name ('dashboard')
    return redirect(url_for('auth.dashboard', success_message=success_message))
    

# Route for deleting personnel
@personnel_bp.route('/personnel/delete/<int:id>', methods=['POST'])
def delete_personnel(id):
    personnel = Personnel.query.get_or_404(id)
    if personnel.profile_picture and os.path.exists(personnel.profile_picture):
        os.remove(personnel.profile_picture)
    db.session.delete(personnel)
    db.session.commit()
    flash('Personnel deleted successfully!', 'success')
    return redirect(url_for('auth.dashboard'))

@personnel_bp.route('listofusers', methods=['GET'])
def listofusers():
    # personnel_list = User.query.filter(User.level == 0).all()    
    personnel_list = User.query.filter(User.level == 0).all()
    return render_template('personnel/patronUsers.html', personnel_list=personnel_list)


def normalize_username(base_name, attempt=0):
    candidate = ''.join(base_name.lower().split())
    if attempt > 0:
        candidate = f"{candidate}{attempt}"
    if User.query.filter_by(user_userName=candidate).first():
        return normalize_username(base_name, attempt + 1)
    return candidate


def get_course_id(course_field):
    if not course_field:
        return None
    found = Course.query.filter(Course.courseName.ilike(f"%{course_field}%")).first()
    return found.id if found else None


def get_default_college_id():
    college = College.query.first()
    return college.id if college else 1

#++=======================================================================================
# upload of file excel goes here then save into tbl_users this will be use in the creation of account. if the user will create an account 
# it will search the barcode or the district_id of the student this will only work for the student of the CMU
# for visitor it will have a different route but will not go here 
# ===============================================================================================================================


@personnel_bp.route('/upload-students', methods=['POST'])
def upload_students():
    file = request.files.get('file')
    if not file:
        flash('No file uploaded', 'danger')
        return redirect(url_for('personnel.listofusers'))

    try:
        df = pd.read_excel(file)

        # Expected headers based on user's description
        expected_headers = ['Barcode - Patron', 'District ID', 'Name - First', 'Name - Last', 'Course']

        # Check if all expected headers are present
        missing_headers = [h for h in expected_headers if h not in df.columns]
        if missing_headers:
            flash(f'Missing required columns: {", ".join(missing_headers)}', 'danger')
            return redirect(url_for('personnel.listofusers'))

        inserted = 0
        skipped = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Extract data from Excel
                barcode = str(row['Barcode - Patron']).strip() if pd.notna(row['Barcode - Patron']) else None
                district_id_raw = row['District ID'] if pd.notna(row['District ID']) else None
                district_id = int(district_id_raw) if district_id_raw is not None and str(district_id_raw) != 'nan' else None
                first_name = str(row['Name - First']).strip() if pd.notna(row['Name - First']) else ''
                last_name = str(row['Name - Last']).strip() if pd.notna(row['Name - Last']) else ''
                course_name = str(row['Course']).strip() if pd.notna(row['Course']) else None

                full_name = f"{first_name} {last_name}".strip()

                if not full_name:
                    errors.append(f"Row {index + 2}: Missing name")
                    continue

                # Check for duplicates using barcode or district_id
                exists = None
                if barcode and barcode != 'nan':
                    exists = User.query.filter_by(barcode=barcode).first()
                if not exists and district_id is not None:
                    exists = User.query.filter_by(district_id=district_id).first()

                if not exists:
                    try:
                        # Now that columns exist, we can store the actual values
                        new_student = User(
                            user_fullName=full_name,
                            district_id=district_id,
                            barcode=barcode,
                            user_course=None
                        )
                        db.session.add(new_student)
                        db.session.commit()  # Commit each record individually
                        inserted += 1
                    except Exception as insert_error:
                        db.session.rollback()
                        errors.append(f"Row {index + 2}: Failed to insert {full_name} - {str(insert_error)}")
                        continue
                        skipped += 1

            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue

        # Final summary (no need for final commit since we commit each record)
        message = f"Upload completed! Students imported: {inserted}, Duplicates skipped: {skipped}"
        if errors:
            message += f", Errors: {len(errors)}"
        flash(message, 'success')

        if errors:
            # You might want to log these errors or show them to the user
            print("Upload errors:", errors)

    except Exception as e:
        db.session.rollback()
        flash(f'Error processing file: {str(e)}', 'danger')

    # return redirect(url_for('personnel.listofusers'))
    return jsonify({
        'inserted': inserted,
        'skipped': skipped,
        'errors': errors
    })
    
@personnel_bp.route('/user-history', methods=['GET'])
def user_history():
    user_id = session.get('user_id') or request.args.get('user_id')
    if not user_id:
        flash('Please login to view history.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))
    
    thesis_activities = db.session.query(
        ThesisActivity.activity_date.label('activity_date'),
        ThesisActivity.activity_type.label('activity_type'),
        Thesis.title.label('resource_title'),
        literal('thesis').label('source'),
        Thesis.id.label('resource_id')
    ).join(Thesis, Thesis.id == ThesisActivity.thesis_id).filter(ThesisActivity.user_id == user_id)

    eresource_activities = db.session.query(
        EResourceActivity.activity_date.label('activity_date'),
        EResourceActivity.activity_type.label('activity_type'),
        EResource.title.label('resource_title'),
        literal('eresource').label('source'),
        EResource.id.label('resource_id')
    ).join(EResource, EResource.id == EResourceActivity.eresource_id).filter(EResourceActivity.user_id == user_id)

    combined_activities = thesis_activities.union_all(eresource_activities).order_by(desc('activity_date'))

    try:
        activities = combined_activities.all()
    except Exception as e:
        current_app.logger.error('Error loading user history: %s', e)
        flash('Could not load activity history.', 'danger')
        activities = []
    

    return render_template('personnel/user_History.html', activities=activities, user=user)


@personnel_bp.route('/api/search_users', methods=['GET'])
def search_users():
    term = request.args.get('term', '')
    if not term:
        return jsonify([])
    users = User.query.filter(
        db.or_(
            User.user_fullName.contains(term),
            User.user_userName.contains(term)
        )
    ).limit(10).all()
    result = [
        {
            'id': user.id,
            'full_name': user.user_fullName,
            'username': user.user_userName or ''
        }
        for user in users
    ]
    return jsonify(result)


@personnel_bp.route('/api/search_patrons', methods=['GET'])
def search_patrons():
    term = request.args.get('term', '')
    if not term:
        return jsonify([])
    patrons = User.query.filter(
        User.level == 0,
        db.or_(
            User.user_fullName.contains(term),
            User.user_userName.contains(term),
            User.user_email.contains(term)
        )
    ).limit(20).all()
    result = [
        {
            'id': patron.id,
            'full_name': patron.user_fullName,
            'username': patron.user_userName or '',
            'email': patron.user_email or '',
            'college': patron.college.name if patron.college else 'N/A',
            'course': patron.course_relation.courseName if patron.course_relation else 'N/A'
        }
        for patron in patrons
    ]
    return jsonify(result)


@personnel_bp.route('/api/patron_stats', methods=['GET'])
def patron_stats():
    from sqlalchemy import func
    stats = db.session.query(
        College.name.label('college'),
        func.count(User.id).label('count')
    ).join(User, User.user_college == College.id).filter(User.level == 0).group_by(College.id).all()
    
    labels = [stat.college for stat in stats]
    data = [stat.count for stat in stats]
    return jsonify({'labels': labels, 'data': data})

# This route will be used to load the data of the user in the profile settings page
@personnel_bp.route('/api/get_user_profile', methods=['GET'])
def get_user_profile():
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'full_name': user.user_fullName,
        'username': user.user_userName,
        'email': user.user_email
    })


#this route will be used to load the page of the profile_settigs page
@personnel_bp.route('/profile_settings', methods=['POST', 'GET'])
def profile_settings():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        
        return redirect(url_for('auth.login'))

    colleges = College.query.all()
    return render_template('personnel/profile_settings.html', user=user, colleges=colleges)


@personnel_bp.route('/api/update_user_profile', methods=['POST'])
def update_user_profile():
    user_id = session.get('user_id')

    # 1. Check Authentication
    if not user_id:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized access.'
        }), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404

    # 2. Extract Data
    # Fallback to form data if JSON isn't present (handles native submissions)
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided.'
        }), 400

    print("DATA RECEIVED:", data)

    try:
        # 3. Check Email Uniqueness (Optional but Recommended)
        new_email = data.get('email', user.user_email)
        if new_email != user.user_email:
            existing_user = User.query.filter_by(user_email=new_email).first()
            if existing_user:
                return jsonify({
                    'status': 'error',
                    'message': 'This email is already in use by another account.'
                }), 400
            user.user_email = new_email

        # 4. Update Fields
        user.user_firstName = data.get('first_name', user.user_firstName)
        user.user_lastName = data.get('last_name', user.user_lastName)
        user.user_middleName = data.get('middle_name', user.user_middleName)
        user.user_address = data.get('address', user.user_address)
        user.barcode = data.get('barcode', user.barcode)
        user.phoneNumber = data.get('contact', user.phoneNumber)
        
        # Update user_fullName to keep it in sync with first and last names
        user.user_fullName = f"{user.user_firstName} {user.user_lastName}".strip()

        # Safely handle district_id numeric conversion
        dist_id = data.get('district_id')
        if dist_id and str(dist_id).isdigit():
            user.district_id = int(dist_id)

        # Handle Numeric conversions safely
        # Handle both AJAX (course/college) and Native Form (selectCourse/selectCollege) keys
        course_val = data.get('course') or data.get('selectCourse')
        college_id = data.get('college') or data.get('selectCollege')

        if college_id and str(college_id).isdigit():
            user.user_college = int(college_id)

        if course_val:
            # Check if course_val is an ID (digit) or a Name
            if str(course_val).isdigit():
                user.user_course = int(course_val)
            else:
                course_obj = Course.query.filter_by(courseName=course_val).first()
                if course_obj:
                    user.user_course = course_obj.id
        

        # 5. Commit Changes
        db.session.commit()
        
        # Flash message for the next page load
        flash('Profile updated successfully!', 'success')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'message': 'Profile updated successfully.',
                'redirect': url_for('auth.profile')
            })
        
        return redirect(url_for('auth.profile'))

    except Exception as e:
        db.session.rollback()
        print("UPDATE ERROR:", str(e))
        return jsonify({
            'status': 'error',
            'message': 'An internal error occurred. Please try again later.'
        }), 500

@personnel_bp.route('/api/change_password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized access.'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided.'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not all([current_password, new_password, confirm_password]):
        return jsonify({'status': 'error', 'message': 'All password fields are required.'}), 400

    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': 'New passwords do not match.'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'User not found.'}), 404

    # Note: Storing passwords in plain text is insecure; consider using Werkzeug's 
    # generate_password_hash and check_password_hash for better security.
    if user.user_password != current_password:
        return jsonify({'status': 'error', 'message': 'The current password you entered is incorrect.'}), 400

    try:
        user.user_password = new_password
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Password changed successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f'Failed to change password: {str(e)}'}), 500


@personnel_bp.route('/api/change_username', methods=['POST'])
def change_username():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Unauthorized access.'}), 401

    data = request.get_json()
    new_username = data.get('new_username')
    current_password = data.get('current_password')

    if not new_username or not current_password:
        return jsonify({'status': 'error', 'message': 'Username and password are required.'}), 400

    user = User.query.get(user_id)
    
    # Check if password is correct
    if user.user_password != current_password:
        return jsonify({'status': 'error', 'message': 'Incorrect password.'}), 400

    # Check if username is taken
    existing_user = User.query.filter_by(user_userName=new_username).first()
    if existing_user and existing_user.id != user.id:
        return jsonify({'status': 'error', 'message': 'Username is already taken.'}), 400

    try:
        user.user_userName = new_username
        db.session.commit()
        
        # Update session
        session['user_username'] = new_username
        
        return jsonify({'status': 'success', 'message': 'Username updated successfully!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500



# This route will be used to check if the title of the thesis is already exist in the database or not
@personnel_bp.route('/api/check_thesis_title', methods=['POST'])
def check_thesis_title():
    data = request.get_json()
    title = data.get('title')
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    thesis = Thesis.query.filter_by(title=title).first()
    return jsonify({'exists': thesis is not None})


#  this route will be used to manage the patron account by the admin or the staff this will be used to update the information of the patron and also to delete the account of the patron if needed
@personnel_bp.route('/manage_patron/<int:user_id>', methods=['POST'])
def manage_patron(user_id):
    user = User.query.get_or_404(user_id)
    action = request.form.get('action')

    if action == 'update':
        user.user_fullName = request.form.get('full_name', user.user_fullName)
        user.user_email = request.form.get('email', user.user_email)
        user.district_id = request.form.get('district_id', user.district_id)
        user.barcode = request.form.get('barcode', user.barcode)
        db.session.commit()
        flash('Patron updated successfully!', 'success')
    elif action == 'delete':
        db.session.delete(user)
        db.session.commit()
        flash('Patron deleted successfully!', 'success')
    else:
        flash('Invalid action.', 'danger')

    return redirect(url_for('personnel.manage_patron', user_id=user_id))
