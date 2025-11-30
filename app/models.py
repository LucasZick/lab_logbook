from datetime import date, timedelta
import time

from flask import current_app
import jwt
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import holidays

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# --- NOVO: TABELA DE LABORATÓRIOS (O TEMA DO MULTI-TENANT) ---
class Laboratory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    acronym = db.Column(db.String(20))
    
    # NOVOS CAMPOS
    description = db.Column(db.Text)
    image_file = db.Column(db.String(100), nullable=False, default='default_lab.jpg')
    
    users = db.relationship('User', backref='laboratory', lazy='dynamic')
    projects = db.relationship('Project', backref='laboratory', lazy='dynamic')

    def __repr__(self):
        return f'<Lab {self.acronym}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_file = db.Column(db.String(100), nullable=False, default='default_project.jpg')
    created_at = db.Column(db.DateTime, default=db.func.now())
    category = db.Column(db.String(50), nullable=False, default='Geral')

    laboratory_id = db.Column(db.Integer, db.ForeignKey('laboratory.id'), nullable=True) # Nullable=True por enquanto para a migração
    
    # Relação com os logs
    logs = db.relationship('LogEntry', backref='parent_project', lazy='dynamic')

    def __repr__(self):
        return f'<Project {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), index=True, default='bolsista')
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False, server_default='0')
    
    # Campos de Perfil
    image_file = db.Column(db.String(100), nullable=False, default='default.png')
    cover_file = db.Column(db.String(100), nullable=False, default='default_cover.jpg')
    course = db.Column(db.String(140))
    lattes_link = db.Column(db.String(256))
    linkedin_link = db.Column(db.String(256))
    github_link = db.Column(db.String(256))
    bio = db.Column(db.Text)
    skills = db.Column(db.String(256))
    invite_status = db.Column(db.String(20), default='none')

    laboratory_id = db.Column(db.Integer, db.ForeignKey('laboratory.id'), nullable=True)

    logs = db.relationship('LogEntry', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_token(self, expires_in=1800):
        """Gera um token válido por 30 minutos (1800 segundos)."""
        return jwt.encode(
            {'reset_password': self.id, 'exp': time.time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_reset_token(token):
        """Verifica o token e retorna o usuário se for válido."""
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

    # --- SISTEMA DE NÍVEIS AVANÇADO ---
    def get_level_info(self):
        """
        Calcula o nível baseado na quantidade de logs.
        Suporta progressão até 1000+ registros.
        """
        count = self.logs.count()
        
        # Tabela de Níveis (Configuração)
        # Threshold: Quantos logs precisa para atingir este nível
        levels_config = [
            {'threshold': 0,    'title': 'Novato Observador',     'icon': 'fas fa-eye',           'color': 'text-muted'},
            {'threshold': 10,   'title': 'Aprendiz de Bancada',   'icon': 'fas fa-tools',         'color': 'text-secondary'},
            {'threshold': 30,   'title': 'Estagiário Dedicado',   'icon': 'fas fa-clipboard-check', 'color': 'text-info'},
            {'threshold': 60,   'title': 'Técnico Júnior',        'icon': 'fas fa-cogs',          'color': 'text-info'},
            {'threshold': 100,  'title': 'Desenvolvedor Robótico','icon': 'fas fa-robot',         'color': 'text-primary'},
            {'threshold': 150,  'title': 'Analista de Dados',     'icon': 'fas fa-chart-network', 'color': 'text-primary'},
            {'threshold': 220,  'title': 'Pesquisador Pleno',     'icon': 'fas fa-flask',         'color': 'text-success'},
            {'threshold': 300,  'title': 'Engenheiro de Projetos','icon': 'fas fa-drafting-compass','color': 'text-success'},
            {'threshold': 400,  'title': 'Líder Técnico',         'icon': 'fas fa-users-cog',     'color': 'text-warning'},
            {'threshold': 550,  'title': 'Cientista Sênior',      'icon': 'fas fa-atom',          'color': 'text-warning'},
            {'threshold': 750,  'title': 'Visionário',            'icon': 'fas fa-lightbulb',     'color': 'text-danger'},
            {'threshold': 1000, 'title': 'Lenda do Laboratório',  'icon': 'fas fa-crown',         'color': 'text-danger'},
        ]

        current_level_data = levels_config[0]
        next_level_data = None
        level_number = 1

        # Itera para encontrar o nível atual e o próximo
        for i, level in enumerate(levels_config):
            if count >= level['threshold']:
                current_level_data = level
                level_number = i + 1
            else:
                next_level_data = level
                break
        
        # Cálculo de progresso para a próxima barra (0 a 100%)
        progress_percent = 100
        next_target = "Max"
        
        if next_level_data:
            prev_threshold = current_level_data['threshold']
            target_threshold = next_level_data['threshold']
            
            # Quantos logs faltam para o próximo nível
            logs_needed = target_threshold - prev_threshold
            logs_done = count - prev_threshold
            
            if logs_needed > 0:
                progress_percent = int((logs_done / logs_needed) * 100)
            
            next_target = target_threshold

        return {
            'level': level_number,
            'title': current_level_data['title'],
            'icon': current_level_data['icon'],
            'color': current_level_data['color'],
            'count': count,
            'progress': progress_percent,
            'next_target': next_target
        }

    def calculate_streak(self):
        logs = self.logs.order_by(LogEntry.entry_date.desc()).all()
        if not logs: return 0
        log_dates = {log.entry_date for log in logs}
        br_holidays = holidays.BR() 
        streak = 0
        check_date = date.today()
        if check_date not in log_dates: check_date -= timedelta(days=1)
        while True:
            if check_date in log_dates: streak += 1; check_date -= timedelta(days=1)
            elif check_date.weekday() >= 5: check_date -= timedelta(days=1)
            elif check_date in br_holidays: check_date -= timedelta(days=1)
            else: break
        return streak

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_date = db.Column(db.Date, index=True, nullable=False, default=date.today)
    
    # Mantemos 'project' como string para histórico, mas vamos tentar usar o ID
    project = db.Column(db.String(140)) 
    
    # NOVO CAMPO: Ligação ao Projeto Real (pode ser nulo para "Geral")
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)

    tasks_completed = db.Column(db.Text)
    observations = db.Column(db.Text, nullable=True)
    next_steps = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'entry_date', name='_user_date_uc'),)