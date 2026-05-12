from flask import Blueprint, render_template, redirect, url_for, session,request,jsonify
from models import ThesisActivity,EResourceActivity, User,Thesis,EResource, Course, College
from sqlalchemy import func, case, literal_column,literal
from sqlalchemy.sql import func # Import func for database functions like count
from datetime import datetime, timezone,date,timedelta
from extension import db

import os
import webbrowser
import threading

# Define the Blueprint

analytics_bp = Blueprint('analytics', __name__, template_folder='templates')

@analytics_bp.route('/view_analytics')
def viewsAnalytics():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
      
        
    topviews = ThesisActivity.query.with_entities(
        ThesisActivity.thesis_id,
        func.count(ThesisActivity.id).label('view_count')
    ).filter(ThesisActivity.activity_type == 'view').group_by(ThesisActivity.thesis_id).order_by(func.count(ThesisActivity.id).desc()).all()
    
    top_viewed = (
        db.session.query(
            Thesis.id,
            Thesis.title,
            func.count(ThesisActivity.id).label('views')
        )
        .join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id)
        .filter(ThesisActivity.activity_type == 'view')
        .group_by(Thesis.id)
        .order_by(func.count(ThesisActivity.id).desc())
        .all()
    )
    
    top_downloads = (
        db.session.query(
            Thesis.id,
            Thesis.title,
            func.count(ThesisActivity.id).label('downloads')
        )
        .join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id)
        .filter(ThesisActivity.activity_type == 'download')
        .group_by(Thesis.id)
        .order_by(func.count(ThesisActivity.id).desc())
        .all()
    )
         
    return render_template('analytics/viewsAnalytic.html', user=user, 
                           topviews=topviews,                            
                           top_viewed=top_viewed,
                           top_downloads=top_downloads
                            )    



#diri sugod and user activity sa analytics mag sugod sa pag list sa ilang name hangtod moabot sa user-activity
@analytics_bp.route('/user_list')
def user_list():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_list= (db.session.query(User).all())
    
    return render_template('analytics/userlist.html', user_list=user_list)




#kini na side ang mag tan-aw sa ilang activity sa thesis ug e-resource, mag sugod sa pag list sa ilang name hangtod moabot sa user-activity

@analytics_bp.route('/user_analyticReport/<int:user_id>')
def user_analyticReport(user_id):

    # 🔐 Auth check
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # 👤 Target user
    target_user = User.query.get_or_404(user_id)

    # 🎛 Filters
    time_filter = request.args.get('resourceFilter', 'Monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    date_formats = {
        'Daily': '%Y-%m-%d',
        'Monthly': '%Y-%m',
        'Yearly': '%Y'
    }
    fmt = date_formats.get(time_filter, '%Y-%m')

   
    t_query = db.session.query(
        func.date_format(
            ThesisActivity.activity_date, fmt).label('period'),
        func.sum(
            case((ThesisActivity.activity_type == 'view', 1), else_=0)
        ).label('t_views'),

        func.sum(
            case((ThesisActivity.activity_type == 'download', 1), else_=0)
        ).label('t_downloads'),

        literal_column("0").label('e_views'),
        literal_column("0").label('e_downloads')
    ).filter(
        ThesisActivity.user_id == user_id
    )

    if start_date:
        t_query = t_query.filter(ThesisActivity.activity_date >= start_date)
    if end_date:
        t_query = t_query.filter(ThesisActivity.activity_date <= end_date)

    t_query = t_query.group_by(func.date_format(ThesisActivity.activity_date, fmt))

    
    e_query = db.session.query(
        func.date_format(
            EResourceActivity.activity_date, fmt
        ).label('period'),

        literal_column("0").label('t_views'),
        literal_column("0").label('t_downloads'),

        func.sum(
            case((EResourceActivity.activity_type == 'view', 1), else_=0)
        ).label('e_views'),

        func.sum(
            case((EResourceActivity.activity_type == 'download', 1), else_=0)
        ).label('e_downloads')
    ).filter(
        EResourceActivity.user_id == user_id
    )

    if start_date:
        e_query = e_query.filter(EResourceActivity.activity_date >= start_date)
    if end_date:
        e_query = e_query.filter(EResourceActivity.activity_date <= end_date)

    e_query = e_query.group_by(func.date_format(EResourceActivity.activity_date, fmt))

    
    combined = t_query.union_all(e_query).subquery()

    analytics_data = (
        db.session.query(
            combined.c.period,

            func.sum(combined.c.t_views).label('thesis_views'),
            func.sum(combined.c.t_downloads).label('thesis_downloads'),
            func.sum(combined.c.e_views).label('eresource_views'),
            func.sum(combined.c.e_downloads).label('eresource_downloads')
        )
        .group_by(combined.c.period)
        .order_by(combined.c.period.desc())
        .all()
    )

    return render_template(
        'analytics/userAnalyticReport.html',
        analytics_data=analytics_data,
        target_user=target_user,
        current_filter=time_filter,
        start_date=start_date,
        end_date=end_date
    )




# Kini na route ang mag handle sa pag tan-aw sa daily analytics sa user, mag sugod sa pag list sa ilang name hangtod moabot sa user-activity
@analytics_bp.route('/analytics_userDailyAnalytics/<int:user_id>')
def analytics_userDailyAnalytics(user_id):

    
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get_or_404(user_id)

    # 📅 Handle Daily, Monthly, or Yearly date strings
    date_param = request.args.get('date')
    
    if not date_param:
        # Default to today if no date provided
        date_param = date.today().isoformat()
        filter_format = '%Y-%m-%d'
    else:
        # Determine format based on string length
        if len(date_param) == 4:    # YYYY
            filter_format = '%Y'
        elif len(date_param) == 7:  # YYYY-MM
            filter_format = '%Y-%m'
        else:                       # YYYY-MM-DD
            filter_format = '%Y-%m-%d'

    # ===== THESIS LOGS =====
    thesis_logs = db.session.query(
        ThesisActivity.activity_date.label('activity_time'),
        literal('Thesis').label('resource_type'),
        ThesisActivity.activity_type.label('action'),
        Thesis.title.label('title')
    ).join(
        Thesis, Thesis.id == ThesisActivity.thesis_id
    ).filter(
        ThesisActivity.user_id == user_id,
        func.date_format(ThesisActivity.activity_date, filter_format) == date_param
    )

    # ===== E-RESOURCE LOGS =====
    eresource_logs = db.session.query(
        EResourceActivity.activity_date.label('activity_time'),
        literal('E-Resource').label('resource_type'),
        EResourceActivity.activity_type.label('action'),
        EResource.title.label('title')
    ).join(
        EResource, EResource.id == EResourceActivity.eresource_id
    ).filter(
        EResourceActivity.user_id == user_id,
        func.date_format(EResourceActivity.activity_date, filter_format) == date_param
    )

    # ===== UNION =====
    daily_logs = (
        thesis_logs
        .union_all(eresource_logs)
        .order_by(db.text('activity_time DESC'))
        .all()
    )

    return render_template(
        'analytics/user_dailyAnalytics.html',
        user=user,
        daily_logs=daily_logs,
        selected_date=date_param
    )


@analytics_bp.route('/user-activity')
def user_activity():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # 1. Get Filters
    time_filter = request.args.get('resourceFilter', 'Monthly')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    date_formats = {'Daily': '%Y-%m-%d', 'Monthly': '%Y-%m', 'Yearly': '%Y'}
    fmt = date_formats.get(time_filter, '%Y-%m')

    # 2. Query Thesis Activity by User
    t_query = db.session.query(
        func.date_format(ThesisActivity.activity_date, fmt).label('period'),
        User.user_userName.label('user_name'),
        func.sum(case((ThesisActivity.activity_type == 'view', 1), else_=0)).label('t_views'),
        func.sum(case((ThesisActivity.activity_type == 'download', 1), else_=0)).label('t_downloads'),
        literal_column("0").label('e_views'),
        literal_column("0").label('e_downloads')
    ).join(User, User.id == ThesisActivity.user_id)
    
    if start_date: t_query = t_query.filter(ThesisActivity.activity_date >= start_date)
    if end_date: t_query = t_query.filter(ThesisActivity.activity_date <= end_date)
    t_query = t_query.group_by('period', 'user_name')

    # 3. Query E-Resource Activity by User
    e_query = db.session.query(
        func.date_format(EResourceActivity.activity_date, fmt).label('period'),
        User.user_userName.label('user_name'),
        literal_column("0").label('t_views'),
        literal_column("0").label('t_downloads'),
        func.sum(case((EResourceActivity.activity_type == 'view', 1), else_=0)).label('e_views'),
        func.sum(case((EResourceActivity.activity_type == 'download', 1), else_=0)).label('e_downloads')
    ).join(User, User.id == EResourceActivity.user_id)
    
    if start_date: e_query = e_query.filter(EResourceActivity.activity_date >= start_date)
    if end_date: e_query = e_query.filter(EResourceActivity.activity_date <= end_date)
    e_query = e_query.group_by('period', 'user_name')

    # 4. Final Aggregation
    combined = t_query.union_all(e_query).subquery()
    query_results = db.session.query(
        combined.c.period,
        combined.c.user_name,
        func.sum(combined.c.t_views).label('thesis_views'),
        func.sum(combined.c.t_downloads).label('thesis_downloads'),
        func.sum(combined.c.e_views).label('eresource_views'),
        func.sum(combined.c.e_downloads).label('eresource_downloads')
    ).group_by(combined.c.period, combined.c.user_name)\
     .order_by(combined.c.period.desc(), combined.c.user_name.asc()).all()

    return render_template('analytics/userAnalytic.html', 
                           query=query_results, 
                           current_filter=time_filter,
                           start_date=start_date,
                           end_date=end_date)
    
        

@analytics_bp.route('/date_analytics')
def date_analytics():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    userId= session.get('user_id')
    user = User.query.get(userId)
    
     # 1. Get dates from form (Ensure names match the HTML 'name' attribute)
    str_date = request.args.get('start_date')  # Changed from str_date to match HTML
    end_date_str = request.args.get('end_date')
    time_filter = request.args.get('resourceFilter', 'Monthly')

    # Map filter to SQL date format
    date_formats = {
        'Daily': '%Y-%m-%d',
        'Monthly': '%Y-%m',
        'Yearly': '%Y'
    }
    fmt = date_formats.get(time_filter, '%Y-%m')

    # 2. Build the Monthly Query
    # We use DATE_FORMAT to group by the selected frequency
    query = db.session.query(
        func.date_format(ThesisActivity.activity_date, fmt).label('period'),
        func.sum(case((ThesisActivity.activity_type == 'view', 1), else_=0)).label('view_count'),
        func.sum(case((ThesisActivity.activity_type == 'download', 1), else_=0)).label('download_count')
    )

    # 3. Apply Filters
    if str_date:
        start = datetime.strptime(str_date, '%Y-%m-%d')
        query = query.filter(ThesisActivity.activity_date >= start)
    
    if end_date_str:
        end = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(ThesisActivity.activity_date <= end)

    # 4. Group by the formatted period string and sort by date
    analytics_data = query.group_by('period').order_by('period').all()

    return render_template(
        'analytics/dateAnalytic.html', 
        analytics_data=analytics_data, 
        start_date=str_date, 
        end_date=end_date_str,
        time_filter=time_filter
    )


@analytics_bp.route('/eresource_analytics')
def view_eresource_analytics():
    
    return render_template('analytics/eresourceAnalytic.html')

@analytics_bp.route('/downloadAnalytics')
def downloadAnalytics():
    top_downloads =(
        db.session.query(
            Thesis.title,
            func.count(ThesisActivity.id).label('downloads')
        )
        .join(ThesisActivity, Thesis.id == ThesisActivity.thesis_id)
        .filter(ThesisActivity.activity_type == 'download')
        .group_by(Thesis.id)
        .order_by(func.count(ThesisActivity.id).desc())
        .all()
    )
    
    return render_template('analytics/downloadAnalytics.html', top_downloads=top_downloads)

#==== uses API folder in template to load all the analytics ====#

@analytics_bp.route('/api/eresource-monthly-stats')
def monthly_stats():
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    results = (
        db.session.query(
            func.date_format(EResourceActivity.activity_date, "%Y-%m").label("month"),
            func.sum(case((EResourceActivity.activity_type == "view", 1), else_=0)).label("views"),
            func.sum(case((EResourceActivity.activity_type == "download", 1), else_=0)).label("downloads"),
        )
        .filter(EResourceActivity.activity_date.between(start_date, end_date))
        .group_by("month")
        .order_by("month")
        .all()
    )

    data = [
        {
            "month": r.month,
            "views": int(r.views or 0),
            "downloads": int(r.downloads or 0),
        }
        for r in results
    ]

    # return jsonify(data)
    return render_template('api/monthly_stats.html', data=data)






# top viewed and downloaded thesis view details of resource and thesis in analytics


@analytics_bp.route('/thesis_details/<int:thesis_id>')
def thesis_details(thesis_id):
    thesis = Thesis.query.get_or_404(thesis_id)
    course = Course.query.get(thesis.course) if thesis.course else None

    total_views = ThesisActivity.query.filter_by(thesis_id=thesis_id, activity_type='view').count()
    total_downloads = ThesisActivity.query.filter_by(thesis_id=thesis_id, activity_type='download').count()
    total_access = ThesisActivity.query.filter_by(thesis_id=thesis_id).count()

    def user_category_label(user):
        if not user:
            return 'GUEST'
        category_map = {
            0: 'STUDENT',
            1: 'ADMIN',
            2: 'RESEARCH',
            3: 'FACULTY',
            4: 'FRONTDESK',
            5: 'PATRON'
        }
        return category_map.get(user.level, 'USER')

    access_records = []
    history = (
        db.session.query(ThesisActivity, User, College)
        .outerjoin(User, ThesisActivity.user_id == User.id)
        .outerjoin(College, User.user_college == College.id)
        .filter(ThesisActivity.thesis_id == thesis_id)
        .order_by(ThesisActivity.activity_date.desc())
        
        .all()
    )

    for activity, user, college in history:
        access_records.append({
            'date': activity.activity_date.strftime('%b %d, %Y | %H:%M') if activity.activity_date else '',
            'patron_name': user.user_fullName if user else 'Guest',
            'user_category': user_category_label(user),
            'department': college.name if college else (user.user_college if user else 'N/A'),
            'action': 'Download' if activity.activity_type == 'download' else 'Full Read',
        })

    return render_template(
        'analytics/details_topViews.html',
        thesis=thesis,
        course=course,
        total_views=total_views,
        total_downloads=total_downloads,
        access_records=access_records,
        total_access=total_access,
    )


# top viewed and downloaded thesis report details of resource and thesis in analytics
@analytics_bp.route('/thesis_reportDetails/<int:thesis_id>')
def thesis_reportDetails(thesis_id):
    
    datefrom = request.args.get('datefrom')
    dateto = request.args.get('dateto')

    thesis = Thesis.query.get_or_404(thesis_id)
    course = Course.query.get(thesis.course) if thesis.course else None
    total_views = ThesisActivity.query.filter_by(thesis_id=thesis_id, activity_type='view').count()
    total_downloads = ThesisActivity.query.filter_by(thesis_id=thesis_id, activity_type='download').count()
    total_access = ThesisActivity.query.filter_by(thesis_id=thesis_id).count()

    return render_template('analytics/details_topReportViews.html', thesis=thesis, course=course, total_views=total_views, total_downloads=total_downloads, total_access=total_access)
