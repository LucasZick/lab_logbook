import click
from app import db
from app.models import User

@click.command("create-professor")
@click.argument("username")
@click.argument("email")
@click.argument("password")
def create_professor(username, email, password):
    """Cria um novo usuário com o papel de professor."""
    if User.query.filter_by(username=username).first():
        print(f"Erro: Usuário '{username}' já existe.")
        return
    if User.query.filter_by(email=email).first():
        print(f"Erro: Email '{email}' já está em uso.")
        return
        
    # --- CORREÇÃO APLICADA AQUI ---
    # Adicionamos is_active=True para garantir que o professor é criado ativo.
    user = User(username=username, email=email, role='professor', is_approved=True, is_active=True)
    
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Professor '{username}' criado com sucesso!")

def register_commands(app):
    """Registra os comandos CLI com a instância do app Flask."""
    app.cli.add_command(create_professor)