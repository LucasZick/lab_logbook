from datetime import date
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), index=True, default='bolsista')
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    
    # --- CAMPOS DE PERFIL ---
    image_file = db.Column(db.String(20), nullable=False, default='default.png')
    course = db.Column(db.String(140))
    lattes_link = db.Column(db.String(256))
    linkedin_link = db.Column(db.String(256))
    github_link = db.Column(db.String(256))
    bio = db.Column(db.Text)

    skills = db.Column(db.String(256))

    logs = db.relationship('LogEntry', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, index=True, nullable=False, default=date.today)
    project = db.Column(db.String(140))
    tasks_completed = db.Column(db.Text)
    observations = db.Column(db.Text, nullable=True)
    next_steps = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    __table_args__ = (db.UniqueConstraint('user_id', 'entry_date', name='_user_date_uc'),)