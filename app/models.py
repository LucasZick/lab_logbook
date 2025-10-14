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
    logs = db.relationship('LogEntry', backref='author', lazy='dynamic')
    role = db.Column(db.String(20), index=True, default='bolsista')
    is_approved = db.Column(db.Boolean, default=False)
    
    # --- CORREÇÃO APLICADA AQUI ---
    # Usamos server_default para definir o padrão a nível de banco de dados.
    # '0' é a forma mais compatível de representar FALSE para o SQLite.
    is_active = db.Column(db.Boolean, nullable=False, server_default='0')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ... (A classe LogEntry permanece a mesma) ...
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