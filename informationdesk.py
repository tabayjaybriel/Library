from unittest import result

from models import User, student_thesisTitle,subjectandStudent,Thesis
from flask import Blueprint, render_template, url_for,flash, redirect, session,request,jsonify
from sqlalchemy import sql, text, func, case
from extension import db



informationDesk_bp= Blueprint('informationDesk',__name__, template_folder='informationDesk')

@informationDesk_bp.route('/frontdeskPortal')
def frontdeskPortal():
    if 'user_id' not in session:
        flash ("You need to login to access this page.", "error")
        return redirect(url_for('auth.login'))
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
   
    if not user or user.level != 4:
        flash ("You do not have Permission to view this page", "error")
        return redirect(url_for('auth.login')) # Or to a safer page like 'home'

    forPostingThesis= Thesis.query.order_by(Thesis.upload_date.desc()).all()
    countnewThesis= Thesis.query.filter(Thesis.thesis_status==1).count()
    countArchievedThesis= Thesis.query.filter(Thesis.thesis_status==2).count()
    countPublishedThesis= Thesis.query.filter(Thesis.thesis_status==0).count()
    
    
    monthly_stats = db.session.query(
    func.date_format(Thesis.posted_at, '%Y-%m').label('month'),

    func.sum(
        case((Thesis.thesis_status == 0, 1), else_=0)
    ).label('approved'),

    func.sum(
        case((Thesis.thesis_status == 2, 1), else_=0)
    ).label('archived')

).group_by('month').order_by('month').all()


    return render_template('informationDesk/informatationDeskPortal.html',forPostingThesis=forPostingThesis, 
                           user=user,countnewThesis=countnewThesis,
                           countArchievedThesis=countArchievedThesis,countPublishedThesis=countPublishedThesis, monthly_stats=monthly_stats)
    
@informationDesk_bp.route('/frontdeskInformation')
def frontdeskInformation():
    # if 'user_id' not in session:
    #     flash ("You need to login to access this page.", "error")
    #     return redirect(url_for('auth.login'))
    # user_id = session.get('user_id')
    # user = User.query.get(user_id)
    
   
    # if not user or user.level != 4:
    #     flash ("You do not have Permission to view this page", "error")
    #     return redirect(url_for('auth.login')) # Or to a safer page like 'home'
    
    forPostingThesis= Thesis.query.order_by(Thesis.upload_date.desc()).all()
    

    return render_template('informationDesk/frontdeskInformation.html',  forPostingThesis=forPostingThesis)


@informationDesk_bp.route('/post_thesis/<int:thesis_id>', methods=['POST'])
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
    thesis.posted_at = sql.func.now()  

    try:
        from app import db
        db.session.commit()
        flash("Thesis posted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while posting the thesis.", "error")

    return redirect(url_for('informationDesk.frontdeskPortal'))


@informationDesk_bp.route('/archiveThesis/<int:thesis_id>', methods=['POST'])
def archiveThesis(thesis_id):
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
        flash("Only approved theses can be archived.", "error")
        return redirect(url_for('informationDesk.frontdeskPortal'))

    thesis.thesis_status = 2 
    thesis.archived_by = user.id  
    thesis.archived_at = sql.func.now()  
    try:
        from app import db
        db.session.commit()
        flash("Thesis archived successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while archiving the thesis.", "error")

    return redirect(url_for('informationDesk.frontdeskPortal'))



@informationDesk_bp.route('/analytics_data')
def analytics_data():
    data = {
        'new_thesis': Thesis.query.filter(Thesis.thesis_status == 1).count(),
        'archived_thesis': Thesis.query.filter(Thesis.thesis_status == 2).count(),
        'published_thesis': Thesis.query.filter(Thesis.thesis_status == 0).count()
    }
    return jsonify(data)


#======================================================================
# Search individual for posting search the thesis title and author name in the frontdesk information page
#
#
#==========================================================================

@informationDesk_bp.route('/search-items', methods=['GET'])
def search_items():
    if 'user_id' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Session expired'}), 401
        return redirect(url_for('auth.login'))

    user = User.query.get(session.get('user_id'))
    query = request.args.get('q', '').strip()
    
    if not query:
        # If search is cleared, redirect back to the full list
        return redirect(url_for('informationDesk.frontdeskInformation'))
        
    results = Thesis.query.filter(
        (Thesis.title.ilike(f'%{query}%')) | 
        (Thesis.last_name.ilike(f'%{query}%')) | 
        (Thesis.first_name.ilike(f'%{query}%'))
    ).all()
    
    print(f"Search query: {query}, Results found: {len(results)}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
         return render_template('informationDesk/search_tableResult.html', results=results, query=query, user=user)

    # Consistency: Pass 'forPostingThesis' and 'user' to match frontdeskInformation expectation
    return render_template('informationDesk/frontdeskInformation.html', 
                           forPostingThesis=results, 
                           user=user, 
                           query=query)


@informationDesk_bp.route('/filter-views', methods=['GET'])
def filter_views():
    query = request.args.get('btn','')

    # Map query parameter to thesis status
    status_map = {
        'archived': 2,
        'published': 0
    }

    status = status_map.get(query, 0)  # Default to published (0) if not found

    result = Thesis.query.filter_by(thesis_status=status).order_by(sql.asc(Thesis.posted_at)).all()

    return render_template('informationDesk/filterViews.html', filterViews=result, query=query)