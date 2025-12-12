from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_apscheduler import APScheduler
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'main.login'
mail = Mail()
scheduler = APScheduler()

# --- MUDANÇA PRINCIPAL AQUI ---
# Adicionamos o parâmetro 'start_scheduler'
def create_app(config_class=Config, start_scheduler=True):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    
    # Apenas inicializa e registra as tarefas se for a aplicação principal
    if start_scheduler:
        if not scheduler.running:
            scheduler.init_app(app)
            scheduler.start()
        
        with app.app_context():
            from .tasks import send_weekly_report_job
            
            if not scheduler.get_job('send_weekly_report'):
                scheduler.add_job(
                    id='send_weekly_report',
                    func=send_weekly_report_job,
                    trigger='cron',
                    day_of_week='fri',
                    hour=21,
                    minute=00
                )

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app import commands
    commands.register_commands(app)

    from app import models

    return app