from base import db, login_manager
from base import bcrypt
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(length=30), nullable=False, unique=True)
    email_address = db.Column(db.String(length=50), nullable=False, unique=True)
    password_hash = db.Column(db.String(length=60), nullable=False)       
    mails_file = db.relationship('Mails', backref='owned_user', lazy=True)
  

    @property
    def password(self):
        return self.password

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)


class Mails(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    file_name = db.Column(db.String(length=512), nullable=False, unique=True)
    file = db.Column(db.VARBINARY(25123))
    processing_status = db.Column(db.String(20), nullable=False, default='pending')
    viewable_status = db.Column(db.Boolean, nullable=False, default=False)
    owner = db.Column(db.Integer(), db.ForeignKey('user.id'))
    mail_analysis_results = db.relationship('MailAnalysisResult', cascade='all, delete-orphan', backref='mail')


class MailAnalysisResult(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
    file_id = db.Column(db.Integer(), db.ForeignKey('mails.id'), nullable=False)    
    analyzed_mail = db.Column(db.Text(), nullable=False)
    top_10_words = db.Column(db.Text(), nullable=True)
    mail_topic = db.Column(db.Text(), nullable=True)
    mail_NER = db.Column(db.Text(), nullable=True)
    mail_from = db.Column(db.Text(), nullable=True)
    subject=db.Column(db.Text(), nullable=True)
    mail_Sum=  db.Column(db.Text(), nullable=True)
    mail_Sent= db.Column(db.Text(), nullable=True)
    owner = db.relationship('User', backref=db.backref('mail_analysis_results', lazy=True))

    def __repr__(self):
        return f'MailAnalysisResult for user {self.user_id}'