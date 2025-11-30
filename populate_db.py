import random
import calendar
from datetime import date
import secrets

# Importa as ferramentas necessárias da nossa aplicação
from app import create_app, db
from app.models import User, LogEntry, Project

# --- Configuração ---
app = create_app()
app.app_context().push()

# --- 1. DADOS PARA CRIAÇÃO DE PROJETOS (Com CATEGORIAS) ---
projects_data = [
    {
        "name": "Robô Manipulador Kuka",
        "desc": "Desenvolvimento de algoritmos de cinemática inversa e controlo de força para manipulação delicada.",
        "cat": "Robotica"
    },
    {
        "name": "Veículo Autônomo (AGV)",
        "desc": "Navegação autônoma em ambientes internos usando ROS2, LiDAR e SLAM.",
        "cat": "Robotica"
    },
    {
        "name": "Firmware do Braço Delta",
        "desc": "Otimização do código de baixo nível para controladores de motores de passo em alta velocidade.",
        "cat": "Embedded"
    },
    {
        "name": "Sistema de Visão Estéreo",
        "desc": "Implementação de visão computacional para deteção de profundidade e objetos em tempo real.",
        "cat": "IA"
    },
    {
        "name": "Drone de Mapeamento",
        "desc": "Fotogrametria aérea e reconstrução 3D de terrenos acidentados.",
        "cat": "Robotica"
    },
    {
        "name": "Hexápode Explorador",
        "desc": "Robô aranha para terrenos irregulares com aprendizagem por reforço.",
        "cat": "IA"
    },
    {
        "name": "Interface Homem-Máquina",
        "desc": "Dashboard em React para controlo e telemetria dos robôs do laboratório.",
        "cat": "Software"
    },
    {
        "name": "Prótese Impressa em 3D",
        "desc": "Modelagem e impressão de prótese mioelétrica de baixo custo.",
        "cat": "3D"
    }
]

# --- 2. DADOS PARA OS LOGS ---
tasks_list = [
    "Desenvolvi e testei o nó ROS para controle de trajetória.",
    "Realizei a calibração cinemática do manipulador com novos parâmetros.",
    "Modelei e imprimi em 3D um novo suporte para os motores.",
    "Implementei um filtro de partículas para localização (AMCL).",
    "Fiz a fusão de sensores do IMU e encoders de roda com um filtro de Kalman.",
    "Refatorei o código de comunicação serial para reduzir latência.",
    "Realizei testes de bateria e consumo energético em carga máxima.",
    "Atualizei a documentação técnica no Wiki do laboratório.",
    "Corrigi bugs na leitura da câmera térmica.",
    "Participei na reunião de planeamento semanal e defini novas metas."
]

observations_list = [
    "O motor do eixo 2 está superaquecendo após 20 minutos.",
    "A precisão do GPS melhorou 15% com o novo filtro.",
    "A simulação no Gazebo foi bem sucedida, pronto para testes reais.",
    "Perda de pacotes na comunicação Wi-Fi ao afastar mais de 10m.",
    "O novo gripper funciona perfeitamente com objetos cilíndricos.",
    "Dificuldade em compilar a biblioteca PCL no Raspberry Pi.",
    "Necessário comprar mais filamento PLA para as próximas peças.",
    None, # Às vezes não há obs
    None
]

next_steps_list = [
    "Analisar o log de dados do motor 2.",
    "Otimizar o código de processamento de imagem.",
    "Corrigir o arquivo URDF com as medidas precisas do robô.",
    "Integrar o módulo de voz.",
    "Preparar apresentação para a banca.",
    "Testar o algoritmo em ambiente externo."
]

# --- 3. DADOS DE PERFIL ---
courses = [
    "Engenharia Mecatrônica - 7º Semestre", "Ciência da Computação - 5º Semestre",
    "Engenharia Elétrica - 9º Semestre", "Mestrado em Robótica",
    "Engenharia de Controle e Automação", "Doutoramento em IA"
]
skills_pool = [
    "Python", "C++", "ROS", "Linux", "SolidWorks", "PCB Design", "Soldagem",
    "Visão Computacional", "Deep Learning", "Docker", "Git", "Arduino", "Raspberry Pi"
]
bios = [
    "Apaixonado por robótica móvel e sistemas autônomos.",
    "Focado em visão computacional e inteligência artificial aplicada a drones.",
    "Interessado em design mecânico e prototipagem rápida.",
    "Pesquisando sobre manipulação robótica e controle de força.",
    "Entusiasta de automação residencial e IoT."
]

def populate():
    print("\n=== INICIANDO POPULAÇÃO DO BANCO DE DADOS ===\n")

    print("1. Limpando dados antigos...")
    LogEntry.query.delete()
    Project.query.delete()
    User.query.delete()
    db.session.commit()
    print("   -> Dados antigos removidos.")

    # --- CRIAÇÃO DOS PROJETOS ---
    print("2. Criando Projetos...")
    db_projects = []
    for p_data in projects_data:
        proj = Project(
            name=p_data["name"], 
            description=p_data["desc"],
            category=p_data["cat"], # <--- CATEGORIA ADICIONADA AQUI
            image_file='default_project.jpg' 
        )
        db.session.add(proj)
        db_projects.append(proj)
    
    db.session.commit()
    print(f"   -> {len(db_projects)} projetos criados.")

    # --- CRIAÇÃO DOS USUÁRIOS ---
    print("3. Criando Usuários...")
    
    # Professor
    professor = User(
        username='professor', email='prof@example.com', role='professor', 
        is_approved=True, is_active=True,
        bio="Coordenador do Laboratório. Doutor em Robótica pela USP.",
        course="Professor Titular", skills="Gestão,Robótica,IA,Educação"
    )
    professor.set_password('professor')
    db.session.add(professor)

    # Lista de Bolsistas Ativos
    active_names = ['ana', 'bruno', 'carlos', 'daniela', 'eduardo', 'fernanda']
    students_objs = []
    
    for name in active_names:
        user_skills = ",".join(random.sample(skills_pool, k=random.randint(3, 5)))
        
        user = User(
            username=name, 
            email=f'{name}@example.com', 
            is_approved=True, 
            is_active=True,
            course=random.choice(courses),
            bio=random.choice(bios),
            skills=user_skills,
            github_link=f"https://github.com/{name}",
            linkedin_link=f"https://linkedin.com/in/{name}"
        )
        user.set_password(name)
        db.session.add(user)
        students_objs.append(user)
        print(f"   -> Bolsista ativo '{name}' criado.")

    # Bolsista Inativo
    inactive = User(username='gabriel', email='gabriel@example.com', is_approved=True, is_active=False, bio="Ex-bolsista.")
    inactive.set_password('gabriel')
    db.session.add(inactive)
    
    # Pendentes
    db.session.add(User(username='hugo', email='hugo@example.com'))
    db.session.add(User(username='isabela', email='isabela@example.com'))
    
    db.session.commit()
    print("   -> Usuários criados com sucesso.")

    # --- GERAÇÃO DE LOGS ---
    print("4. Gerando Histórico de Registros...")
    
    months_to_populate = range(1, 13) 
    current_year = 2025
    total_logs = 0

    for student in students_objs:
        for month in months_to_populate:
            _, num_days = calendar.monthrange(current_year, month)
            num_logs = random.randint(5, 12)
            used_days = set()
            
            while len(used_days) < num_logs:
                day = random.randint(1, num_days)
                entry_date = date(current_year, month, day)
                
                if day not in used_days and entry_date.weekday() < 5:
                    
                    if random.random() > 0.3:
                        proj = db_projects[hash(student.username) % len(db_projects)]
                    else:
                        proj = random.choice(db_projects)
                    
                    log = LogEntry(
                        entry_date=entry_date,
                        project=proj.name,
                        project_id=proj.id,
                        tasks_completed=random.choice(tasks_list),
                        observations=random.choice(observations_list),
                        next_steps=random.choice(next_steps_list),
                        author=student
                    )
                    db.session.add(log)
                    used_days.add(day)
                    total_logs += 1
    
    db.session.commit()
    print(f"\n=== SUCESSO! ===")
    print(f"Banco de dados populado com {total_logs} registros de diário.")

if __name__ == '__main__':
    populate()