from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from extension import db
from models import Thesis, College, Course, User, ThesisActivity,EResource,EResourceActivity
from addthesis import add_thesis_bp
from auth import auth_bp
from personnel import personnel_bp
from listofthesis import thesislists_bp
from college import college_bp
from linkages import Linkages_bp
from listofpatron import listofUser_bp
from faculty import faculty_bp
from student import student_bp
from research import research_bp
from informationdesk import informationDesk_bp
from eresources import eresources_bp
from analytics import analytics_bp
from analytics_api import analytics_api_bp
from search_API import search_API

from dotenv import load_dotenv

import os
import webbrowser
import threading

from flask_migrate import Migrate
from datetime import datetime
from sqlalchemy import func,extract # Import func for database functions like count

# Initialize the Flask app
def create_app():
    app = Flask(__name__)
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/library2023'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your_secret_key_here' # IMPORTANT: Change this to a strong, random key!

    db.init_app(app)
    migrate = Migrate(app, db)

    app.register_blueprint(add_thesis_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(personnel_bp, url_prefix='/personnel')
    app.register_blueprint(thesislists_bp, url_prefix='/theses')
    app.register_blueprint(college_bp, url_prefix='/college')
    app.register_blueprint(Linkages_bp,url_prefix='/linkages')
    app.register_blueprint(listofUser_bp, url_prefix='/patron')
    app.register_blueprint(faculty_bp,url_prefix='/faculty')
    app.register_blueprint(student_bp,url_prefix='/student')
    app.register_blueprint(research_bp,url_prefix='/research')
    app.register_blueprint(informationDesk_bp,url_prefix='/informationDesk')
    app.register_blueprint(eresources_bp,url_prefix='/eresources')
    app.register_blueprint(analytics_bp,url_prefix='/analytics')
    app.register_blueprint(analytics_api_bp,url_prefix='/api')
    app.register_blueprint(search_API,url_prefix='/api/search')
    

    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    @app.route('/')
    def home(): 
        if 'user_id' in session: 
            carousel_items = Thesis.query.order_by(Thesis.upload_date.desc()).limit(3).all()
            theses = Thesis.query.filter(Thesis.thesis_status == 0).order_by(Thesis.upload_date.desc()).limit(20).all()
            
            countCoursess = db.session.query(func.count(Course.id)).scalar()

            
            
            countThesesViewed = db.session.query(func.count(ThesisActivity.id)).join(Thesis, ThesisActivity.thesis_id == Thesis.id).filter(
            Thesis.id == ThesisActivity.thesis_id,ThesisActivity.activity_type == 'view').scalar()

                                   

            countTheses = db.session.query(func.count(Thesis.id)).scalar()
            countEbooks = db.session.query(func.count(EResource.id)).filter(EResource.resource_type == 'Ebook').scalar()   
            countEjournals = db.session.query(func.count(EResource.id)).filter(EResource.resource_type == 'Ejournal').scalar()
           
            countNursings = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 1).scalar()                       
            countAgri = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 2) .scalar()
            countIT = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 3).scalar()
            
            countHospitalityMngt = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 7).scalar()
            countCfes = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 8).scalar()
            countCBM = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 9).scalar()
            countLaw= db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 10).scalar()

            countEngines = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 14).scalar()
            countArtaSciences = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 15).scalar()
            countEducation = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 17).scalar()
            countvetetirinarian = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 16).scalar()
            countsocialSciences = db.session.query(func.count(Thesis.id)).filter(Thesis.stud_college == 18).scalar()
            
            totalresources= countTheses+countEbooks+countEjournals          
            
                        
            
            # Count how many times each thesis was viewed
            count_viewed_theses = (
                db.session.query(
                    ThesisActivity.thesis_id,
                    func.count(ThesisActivity.id).label('view_count')
                )
                .filter(ThesisActivity.activity_type == 'view')
                .group_by(ThesisActivity.thesis_id)
                .subquery()
            )

            # Count how many times each thesis was downloaded
            count_downloaded_theses = (
                db.session.query(
                    ThesisActivity.thesis_id,
                    func.count(ThesisActivity.id).label('download_count')
                )
                .filter(ThesisActivity.activity_type == 'download')
                .group_by(ThesisActivity.thesis_id)
                .subquery()
            )

            # Join both subqueries with Thesis table
            counter = (
                db.session.query(
                    Thesis,
                    count_viewed_theses.c.view_count,
                    count_downloaded_theses.c.download_count
                )
                .outerjoin(count_viewed_theses, Thesis.id == count_viewed_theses.c.thesis_id)
                .outerjoin(count_downloaded_theses, Thesis.id == count_downloaded_theses.c.thesis_id)
                .all()
            )
            
            countViewsDownloadsJE = db.session.query(
                EResource,
                func.count(ThesisActivity.id).label('view_count'),
                func.count(ThesisActivity.id).label('download_count')
            ).join(ThesisActivity, EResource.id == ThesisActivity.thesis_id).filter(
                ThesisActivity.activity_type == 'view'
            ).group_by(EResource.id).all(
            )
            print(f"Count Views and Downloads JE':{countViewsDownloadsJE}")

            # print(f"Theses fetched for 'Recently Added': {theses}")
            # print(f"Carousel items fetched: {carousel_items}")


            # star for every thesis --------------------------------------------------------------------starsssss
            # stats = db.session.query(
            # EResourceActivity.eresource_id,
            # func.count(func.nullif(EResourceActivity.activity_type != 'view', False)).label('views'),
            # func.count(func.nullif(EResourceActivity.activity_type != 'download', False)).label('downloads')
            # ).group_by(EResourceActivity.eresource_id).all()

    # Convert to a dictionary for easy lookup: {id: {'views': X, 'downloads': Y}}
            # resource_stats = {s.eresource_id: {'views': s.views, 'downloads': s.downloads} for s in stats}
            
            return render_template(
                'home.html',countViewsDownloadsJE=countViewsDownloadsJE,
                # resource_stats=resource_stats,
                carousel_items=carousel_items,
                theses=theses,
                counter=counter,
                countTheses=countTheses,
                countEbooks=countEbooks,
                countEjournals=countEjournals,
                totalresources=totalresources,
                countAgri=countAgri,
                countNursings=countNursings,
                countCfes=countCfes,
                countEngines=countEngines,
                
                countHrs=countHospitalityMngt,
                
                countIT=countIT,
                countLaw=countLaw,
                countArtaSciences=countArtaSciences,
                countCBM=countCBM,
                countEducation=countEducation,
                countvetetirinarian=countvetetirinarian,
                countThesesViewed=countThesesViewed,
                countsocialSciences=countsocialSciences,
                countCoursess=countCoursess

            )

        else:
            return redirect(url_for('auth.login'))


    @app.route('/thesis/<int:id>/stats')
    def thesis_stats(id):
        views = ThesisActivity.query.filter_by(thesis_id=id, activity_type='view').count()

        downloads = ThesisActivity.query.filter_by( thesis_id=id, activity_type='download').count()

        return jsonify({'views': views,'downloads': downloads})


    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('search-query')
        search_results = search_thesis_by_title(query)
        return render_template('search_results.html', results=search_results, query=query) # CORRECTED TEMPLATE NAME
    
    
    @app.route('/search_results', methods=['GET'])
    def search_results():
        query = request.args.get('search-query')
        search_results = search_thesis_by_title(query)
        return render_template('search_results.html', results=search_results, query=query)


    with app.app_context():
        db.create_all()


    return app

def search_thesis_by_title(query):
    if not query:
        return []
    search_pattern = f"%{query}%"
    results = Thesis.query.filter(Thesis.title.ilike(search_pattern)).all()
    return results

def open_browser(port): # Added 'port' here to receive the value
    chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'
    webbrowser.register('chrome_custom', None, webbrowser.BackgroundBrowser(chrome_path))
    
    # Check for WERKZEUG_RUN_MAIN to prevent opening two tabs
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        # We use an f-string here to inject the actual port being used
        threading.Timer(1.5, lambda: webbrowser.get('chrome_custom').open_new_tab(f'http://127.0.0.1:{port}')).start()

if __name__ == '__main__':
    # Pulling from environment variables
    current_port = int(os.environ.get('PORT', 5500))
    is_debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    app = create_app()
    
    # Now this call and the function definition above match!
    open_browser(current_port)
    
    app.run(debug=is_debug, port=current_port)
    
    
   