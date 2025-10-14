import random
import calendar
from datetime import date

# Importa as ferramentas necessárias da nossa aplicação
from app import create_app, db
from app.models import User, LogEntry

# --- Configuração ---
app = create_app()
app.app_context().push()

# --- Dados de Exemplo para Robótica ---
projects = [
    "Robô Manipulador Kuka", "Veículo Autônomo (AGV)", "Firmware do Braço Delta",
    "Sistema de Visão Estéreo", "Drone de Mapeamento"
]
tasks = [
    "Desenvolvi e testei o nó ROS para controle de trajetória.",
    "Realizei a calibração cinemática do manipulador.",
    "Modelei e imprimi em 3D um novo gripper para o robô.",
    "Implementei um filtro de partículas para localização (AMCL).",
    "Fiz a fusão de sensores do IMU e encoders de roda com um filtro de Kalman."
]
observations_samples = [
    "O motor do eixo 2 está superaquecendo.", "A precisão do GPS melhorou 15% com o filtro de Kalman.",
    "A simulação no Gazebo foi bem sucedida.", "Perda de pacotes na comunicação Wi-Fi.", "O novo gripper funciona perfeitamente."
]
next_steps_samples = [
    "Analisar o log de dados do motor 2.", "Otimizar o código de processamento de imagem.",
    "Corrigir o arquivo URDF com as medidas precisas do robô."
]

def populate():
    """
    Limpa o banco de dados e o popula com um professor, bolsistas ativos,
    inativos e pendentes para um teste completo.
    """
    print("Limpando dados antigos do banco de dados...")
    LogEntry.query.delete()
    User.query.delete()
    db.session.commit()
    print("Dados antigos removidos.")

    # --- Criação dos Usuários com Diferentes Status ---
    print("Criando usuários de teste...")

    # 1. Professor (Aprovado e Ativo)
    professor = User(username='professor', email='prof@example.com', role='professor', is_approved=True, is_active=True)
    professor.set_password('professor')
    db.session.add(professor)
    print("- Professor 'professor' criado.")

    # 2. Bolsistas Aprovados e ATIVOS
    active_students_data = [('ana', 'ana@example.com', 'ana'), ('bruno', 'bruno@example.com', 'bruno')]
    students_with_logs = []
    for username, email, password in active_students_data:
        user = User(username=username, email=email, is_approved=True, is_active=True)
        user.set_password(password)
        db.session.add(user)
        students_with_logs.append(user)
        print(f"- Bolsista ATIVO '{username}' criado.")

    # 3. Bolsista Aprovado mas INATIVO
    inactive_student = User(username='cesar', email='cesar@example.com', is_approved=True, is_active=False)
    inactive_student.set_password('cesar')
    db.session.add(inactive_student)
    students_with_logs.append(inactive_student) # Ele tem logs, mas está inativo
    print("- Bolsista INATIVO 'cesar' criado.")

    # 4. Bolsistas com Aprovação PENDENTE
    pending_students_data = [('davi', 'davi@example.com', 'davi'), ('elisa', 'elisa@example.com', 'elisa')]
    for username, email, password in pending_students_data:
        user = User(username=username, email=email) # Defaults: is_approved=False, is_active=False
        user.set_password(password)
        db.session.add(user)
        print(f"- Bolsista PENDENTE '{username}' criado.")
        
    # Salva os usuários no banco para que recebam IDs
    db.session.commit()
    print("Usuários salvos no banco de dados.")

    # --- Geração de Registros de Diário (Apenas para bolsistas com histórico) ---
    print("\nGerando registros de diário para bolsistas ativos e inativos...")
    
    periods_to_populate = [(2025, 10), (2025, 9), (2024, 12)]
    total_logs_created = 0

    for student in students_with_logs:
        print(f"  - Gerando logs para '{student.username}'...")
        for year, month in periods_to_populate:
            num_entries = random.randint(3, 7)
            used_dates = set()
            _, num_days = calendar.monthrange(year, month)
            
            while len(used_dates) < num_entries:
                random_day = random.randint(1, num_days)
                entry_date = date(year, month, random_day)
                
                if entry_date not in used_dates:
                    log = LogEntry(
                        entry_date=entry_date,
                        project=random.choice(projects),
                        tasks_completed=random.choice(tasks),
                        observations=random.choice(observations_samples),
                        next_steps=random.choice(next_steps_samples),
                        author=student
                    )
                    db.session.add(log)
                    used_dates.add(entry_date)
                    total_logs_created += 1
    
    db.session.commit()
    print(f"\nBanco de dados populado com sucesso!")
    print(f"Total de registros de diário criados: {total_logs_created}")

if __name__ == '__main__':
    populate()
