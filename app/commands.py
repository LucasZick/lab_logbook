import click
from flask.cli import with_appcontext
from app import db
from app.models import User

@click.command("create-super-admin")
@click.argument("email")
@click.argument("password")
@with_appcontext
def create_super_admin(email, password):
    """Cria um Super Admin. Uso: flask create-super-admin email senha"""
    
    # Verifica se já existe
    user = User.query.filter_by(email=email).first()
    
    if user:
        user.role = 'admin'
        user.is_approved = True
        user.is_active = True
        user.set_password(password)
        print(f"Usuário {email} atualizado para Admin.")
    else:
        # Cria novo
        user = User(
            username="SuperAdmin",
            email=email,
            role='admin',
            is_approved=True,
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        print(f"Novo Super Admin {email} criado com sucesso.")
    
    db.session.commit()

# Função para registrar no app/__init__.py
def register_commands(app):
    app.cli.add_command(create_super_admin)