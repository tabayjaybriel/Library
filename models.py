from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from extension import db  # Import db from extension.py instead of app.py



class Thesis(db.Model):
    __tablename__ = 'thesis'

    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    abstract = db.Column(db.String(1500), nullable=False)
    copyright_yy = db.Column(db.Integer, nullable=False)
    stud_college= db.Column(db.String(11), nullable=False)
    course = db.Column(db.Integer, nullable=False)
    thesis_status = db.Column(db.Integer, default=0)
    
    pdf_file = db.Column(db.String(350), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    researchNumber = db.Column(db.String(20), unique=True, nullable=False)
    type= db.Column(db.Integer, nullable=True)
    isbn= db.Column(db.Integer, nullable=True)
    publisher= db.Column(db.Integer, nullable=True)
    subject= db.Column(db.String(350),nullable=True)
    volume= db.Column(db.String(15),nullable=True)
    pages= db.Column(db.String(10), nullable=True)
    issue= db.Column(db.String(3),nullable=True)
    posted_at = db.Column(db.DateTime, nullable=False)

    # Define the relationship to User
    user = relationship('User', back_populates='theses_submitted')
    activities = db.relationship('ThesisActivity', back_populates='thesis')


    def __init__(self, upload_date, last_name, first_name, title, abstract, copyright_yy, course, thesis_status, 
                 pdf_file,stud_college, researchNumber=None, user_id=None):
        self.last_name = last_name
        self.first_name = first_name
        self.title = title
        self.abstract = abstract
        self.copyright_yy = copyright_yy
        self.course = course
        self.thesis_status = thesis_status
        self.pdf_file = pdf_file
        self.user_id = user_id
        self.stud_college= stud_college
        self.researchNumber = researchNumber
        self.upload_date = upload_date  

    def __repr__(self):
        return f"<Thesis {self.title}>"


# theses tracking 
class ThesisActivity(db.Model):
    __tablename__ = 'thesis_activity'

    id = db.Column(db.Integer, primary_key=True)
    thesis_id = db.Column(db.Integer, db.ForeignKey('thesis.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=True)
    activity_type = db.Column(db.Enum('view', 'download', name='activity_type_enum'), nullable=False)
    activity_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Thesis
    thesis = db.relationship('Thesis', back_populates='activities')

    def __repr__(self):
        return f'<ThesisActivity {self.activity_type} for Thesis {self.thesis_id}>'


# college
class College(db.Model):
    __tablename__='college'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    courses = db.relationship('Course', backref='college', lazy=True)

    def __repr__(self):
        return f"College('{self.name}')"


#course
class Course(db.Model):
    __tablename__ = 'tbl_course'
    id = db.Column(db.Integer, primary_key=True)
    courseName = db.Column(db.String(100), nullable=False)
    major = db.Column(db.String(100), nullable=False) 
    collegeID = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=False)

    def __repr__(self):
        return f"Course('{self.courseName}', College ID: {self.collegeID})"



class Linkages(db.Model):
    __tablename__='tbl_linkages'
    id= db.Column(db.Integer, primary_key=True)
    linkages= db.Column(db.String(250), nullable=False)
    address= db.Column(db.String(250), nullable=False)
    coverage = db.Column(db.Integer, nullable=False)  # Ensure coverage field is defined

    def __init__(self, name, address, coverage):
        self.name = name
        self.address = address
        self.coverage = coverage


class User(db.Model):
    __tablename__ = 'tbl_user'
    id = db.Column(db.Integer, primary_key=True)
    user_fullName = db.Column(db.String(150), nullable=False)
    user_lastName = db.Column(db.String(50), nullable=True)
    user_firstName = db.Column(db.String(150), nullable=True)
    user_middleName = db.Column(db.String(550), nullable=True)
    user_college = db.Column(db.Integer, db.ForeignKey('college.id'), nullable=True)
    user_course = db.Column(db.Integer, db.ForeignKey('tbl_course.id'), nullable=True) # Assuming a user can have a course
    user_userName = db.Column(db.String(150), nullable=True, unique=True)
    user_password = db.Column(db.String(150), nullable=True)
    user_email = db.Column(db.String(350), nullable=True, unique=True)
    level = db.Column(db.Integer, default=0)
    is_online = db.Column(db.Boolean, nullable=False, default=False)  # Use Boolean type
    barcode = db.Column(db.String(20), unique=False, nullable=True)
    district_id = db.Column(db.BigInteger, nullable=True)
    user_address = db.Column(db.String(255), nullable=True)
    phoneNumber = db.Column(db.String(20), nullable=True)
     


    # Define the relationship to College model
    college = relationship("College", backref="users")
    course_relation = relationship("Course", foreign_keys=[user_course])
    subjects = db.relationship('Subject', backref='user', lazy=True)
    personnel = db.relationship('Personnel', backref='user', uselist=False)

    subjects = db.relationship('Subject', backref='user', lazy=True)


    # Relationship to Thesis model with a unique backref name
    theses_submitted = relationship("Thesis", back_populates="user")

    def __init__(self, user_fullName , user_lastName=None,user_address=None, user_firstName=None, user_middleName=None, district_id=None, phoneNumber=None, barcode=None, user_course=None, user_email=None, user_college=None, user_userName=None, user_password=None , level=0):
        self.user_fullName = user_fullName
        self.user_lastName = user_lastName
        self.user_firstName = user_firstName
        self.user_middleName = user_middleName
        self.user_email = user_email
        self.user_college = user_college
        self.user_userName = user_userName
        self.user_password = user_password
        self.level = level
        self.user_course = user_course
        self.district_id = district_id
        self.barcode = barcode
        self.phoneNumber = phoneNumber
        self.user_address = user_address 
        


    def __repr__(self):
        return f"<User {self.user_userName}>"



class Subject(db.Model):
    __tablename__ = 'tbl_subject'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_ID = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=False)
    acad_year= db.Column(db.String(25),nullable=False)
    subjectID = db.Column(db.String(75), nullable=False)
    courseDescription = db.Column(db.String(150), nullable=False)

    def __repr__(self):
        return f'<Subject {self.subjectID}>'

    
    
class Personnel (db.Model):
    __tablename__='personnel'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    userID = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    access_level = db.Column(db.Integer, default=3)
    profile_picture = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Personnel {self.full_name}>'
    
class student_thesisTitle(db.Model):
    __tablename__='tbl_studentthesistitle'
    id= db.Column(db.Integer, primary_key=True, autoincrement=True)
    subjectID= db.Column(db.Integer, db.ForeignKey('tbl_subject.id'),nullable=False)
    userID= db.Column(db.Integer, db.ForeignKey('tbl_user.id'),nullable=False)
    title= db.Column(db.String(1500),nullable=False)
    teacherStatus=db.Column(db.Integer,nullable=False)
    researchStatus= db.Column(db.Integer,nullable=False)
    researchNumber= db.Column(db.String(20),nullable=True)
    research_approval_date = db.Column(db.DateTime, nullable=False)

    # Define the relationship to the User model, linking userID to User.id
    student = relationship('User', foreign_keys=[userID], backref='student_theses')

    def __repr__(self):
        return f'<student_thesisTitle {self.id} - {self.title}>'
    
class subjectandStudent (db.Model):
    __tablename__='tbl_subjectandstudent'
    id= db.Column(db.Integer, primary_key= True, autoincrement= True)
    userID= db.Column(db.Integer, db.ForeignKey('tbl_user.id'),nullable=False)
    subjectID= db.Column (db.Integer, db.ForeignKey('tbl_subject.id'),nullable= False)

    def __repr__(self):
        return f'<subjectandStudent{self.id}>'

class EResource(db.Model):
    __tablename__ = 'tbl_eresource'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    resource_type = db.Column(db.String(50), nullable=False)  # e.g., 'Ebook', 'Ejournal'
    title = db.Column(db.String(500), nullable=False)
    author = db.Column(db.String(500), nullable=True)
    year = db.Column(db.Integer, nullable=True)
    publisher = db.Column(db.String(255), nullable=True)
    doi = db.Column(db.String(255), nullable=True)
    issn_isbn = db.Column(db.String(100), nullable=True)
    subject = db.Column(db.Text, nullable=True)  # For keywords
    staff_notes = db.Column(db.Text, nullable=True)

    # E-Journal specific fields
    volume = db.Column(db.Integer, nullable=True)
    issue = db.Column(db.Integer, nullable=True)
    pages = db.Column(db.String(50), nullable=True)

    # File and user tracking
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=False)
    uploaded_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Integer, default=1, nullable=False)
    # Define the relationship to the User model
    uploader = relationship('User', backref='uploaded_resources')

    def __repr__(self):
        return f'<EResource {self.id} - {self.title}>'

class EResourceActivity(db.Model):
    __tablename__ = 'tbl_eresource_activity'
    id = db.Column(db.Integer, primary_key=True)
    eresource_id = db.Column(db.Integer, db.ForeignKey('tbl_eresource.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=True) # Nullable for guest users
    activity_type = db.Column(db.Enum('view', 'download', name='eresource_activity_type_enum'), nullable=False)
    activity_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to EResource
    eresource = db.relationship('EResource', backref='activities')

    def __repr__(self):
        return f'<EResourceActivity {self.activity_type} for EResource {self.eresource_id}>'
