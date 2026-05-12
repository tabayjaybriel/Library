from  flask import Blueprint, render_template, redirect, url_for, session,request,jsonify
from models import ThesisActivity,EResourceActivity, User,Thesis,EResource
from sqlalchemy import func, case, literal_column,literal,asc
from sqlalchemy.sql import func # Import func for database functions like count
from datetime import datetime, timezone,date,timedelta  
from extension import db

import os
import webbrowser
import threading

analytics_api_bp = Blueprint("analytics_api", __name__)

@analytics_api_bp.route("/api/eresource-monthly-stats")
def eresource_monthly_stats():

     # Get query params
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Default: last 6 months
    if not start_date or not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
    else:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=180)

    monthly_stats = (
        db.session.query(
            func.date_format(EResourceActivity.activity_date, "%Y-%m").label("month"),
            func.sum(case((EResourceActivity.activity_type == "view", 1), else_=0)).label("views"),
            func.sum(case((EResourceActivity.activity_type == "download", 1), else_=0)).label("downloads")
        )
        .filter(EResourceActivity.activity_date.between(start_date, end_date))
        .group_by(func.date_format(EResourceActivity.activity_date, "%Y-%m"))
        .order_by(asc("month"))
        .all()
    )

    data = [
        {
            "month": row.month,
            "views": int(row.views or 0),
            "downloads": int(row.downloads or 0)
        }
        for row in monthly_stats
    ]

    return jsonify(data)



@analytics_api_bp.route("/analytics/monthly")
def monthly_stats():

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    resource = request.args.get("resource")  # thesis | journal | ebook

    # Default last 6 months
    if not start_date or not end_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    query = (
        db.session.query(
            func.date_format(EResourceActivity.activity_date, "%Y-%m").label("month"),
            func.sum(case((EResourceActivity.activity_type == "view", 1), else_=0)).label("views"),
            func.sum(case((EResourceActivity.activity_type == "download", 1), else_=0)).label("downloads")
        )
        .filter(EResourceActivity.activity_date.between(start_date, end_date))
    )

    # 👉 Resource filter
    if resource:
        query = query.filter(EResourceActivity.resource_type == resource)

    monthly_stats = (
        query.group_by(func.date_format(EResourceActivity.activity_date, "%Y-%m"))
        .order_by(asc("month"))
        .all()
    )

    data = [
        {"month": r.month, "views": int(r.views or 0), "downloads": int(r.downloads or 0)}
        for r in monthly_stats
    ]

    return jsonify(data)



@analytics_api_bp.route("/daily")
def daily_stats_api():  
    return jsonify([])
