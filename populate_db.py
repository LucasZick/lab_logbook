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

# --- Dados de Perfil para Teste ---
courses = [
    "Engenharia Mecatrônica - 7º Semestre",
    "Ciência da Computação - 5º Semestre",
    "Engenharia Elétrica - 9º Semestre",
    "Mestrado em Robótica"
]
skills_list = [
    "Python,ROS,C++",
    "SolidWorks,Impressão 3D,Matlab",
    "Visão Computacional,OpenCV,Deep Learning",
    "Microcontroladores,PCB Design,Soldagem"
]
bios = [
    "Apaixonado por robótica móvel e sistemas autônomos.",
    "Focado em visão computacional e inteligência artificial aplicada a drones.",
    "Interessado em design mecânico e prototipagem rápida.",
    "Pesquisando sobre manipulação robótica e controle de força."
]

def populate():
    """
    Limpa o banco de dados e o popula com um professor, bolsistas ativos,
    inativos e pendentes para um teste completo, INCLUINDO PERFIS.
    """
    print("Limpando dados antigos do banco de dados...")
    LogEntry.query.delete()
    User.query.delete()
    db.session.commit()
    print("Dados antigos removidos.")

    # --- Criação dos Usuários com Diferentes Status e Perfis ---
    print("Criando usuários de teste...")

    # 1. Professor (Aprovado e Ativo)
    professor = User(
        username='professor', 
        email='prof@example.com', 
        role='professor', 
        is_approved=True, 
        is_active=True,
        bio="Coordenador do Laboratório de Robótica Avançada.",
        course="Doutor em Engenharia",
        skills="Gestão,Robótica,IA"
    )
    professor.set_password('professor')
    db.session.add(professor)
    print("- Professor 'professor' criado.")

    # 2. Bolsistas Aprovados e ATIVOS
    active_students_data = [
        ('ana', 'ana@example.com', 'ana'), 
        ('bruno', 'bruno@example.com', 'bruno')
    ]
    students_with_logs = []
    
    for username, email, password in active_students_data:
        user = User(
            username=username, 
            email=email, 
            is_approved=True, 
            is_active=True,
            # Dados de perfil aleatórios
            course=random.choice(courses),
            bio=random.choice(bios),
            skills=random.choice(skills_list),
            github_link="https://github.com/exemplo",
            linkedin_link="https://linkedin.com/in/exemplo",
            lattes_link="http://lattes.cnpq.br/123456789"
        )
        user.set_password(password)
        db.session.add(user)
        students_with_logs.append(user)
        print(f"- Bolsista ATIVO '{username}' criado com perfil.")

    # 3. Bolsista Aprovado mas INATIVO
    inactive_student = User(
        username='cesar', 
        email='cesar@example.com', 
        is_approved=True, 
        is_active=False,
        course="Engenharia Civil - 2º Semestre",
        bio="Bolsista anterior, atualmente em intercâmbio.",
        skills="AutoCAD,Excel"
    )
    inactive_student.set_password('cesar')
    db.session.add(inactive_student)
    students_with_logs.append(inactive_student)
    print("- Bolsista INATIVO 'cesar' criado.")

    # 4. Bolsistas com Aprovação PENDENTE
    pending_students_data = [('davi', 'davi@example.com', 'davi'), ('elisa', 'elisa@example.com', 'elisa')]
    for username, email, password in pending_students_data:
        user = User(
            username=username, 
            email=email
            # Pendentes começam sem perfil preenchido (padrão)
        ) 
        user.set_password(password)
        db.session.add(user)
        print(f"- Bolsista PENDENTE '{username}' criado.")
        
    # Salva os usuários no banco para que recebam IDs
    db.session.commit()
    print("Usuários salvos no banco de dados.")

    # --- Geração de Registros de Diário (Apenas para bolsistas com histórico) ---
    print("\nGerando registros de diário para bolsistas ativos e inativos...")
    
    # Ajuste as datas conforme necessário para testar os relatórios
    periods_to_populate = [(2025, 10), (2025, 9), (2024, 12)]
    total_logs_created = 0

    for student in students_with_logs:
        print(f"  - Gerando logs para '{student.username}'...")
        for year, month in periods_to_populate:
            # Garante que não tenta criar datas inválidas (ex: 31 de Setembro)
            _, num_days = calendar.monthrange(year, month)
            num_entries = random.randint(3, 7)
            used_dates = set()
            
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