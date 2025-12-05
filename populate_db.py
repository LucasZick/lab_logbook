import random
import calendar
from datetime import date, timedelta
import secrets

# Importa as ferramentas necessárias da nossa aplicação
from app import create_app, db
from app.models import User, LogEntry, Project, Laboratory, ProjectTag

# --- Configuração ---
app = create_app()
app.app_context().push()

# --- DADOS MESTRES POR LABORATÓRIO ---
# Aqui definimos a "personalidade" de cada lab
labs_config = [
    {
        "name": "Laboratório de Robótica e Automação", 
        "acronym": "LAR",
        "meta": {
            "affiliation": "UDESC - Centro de Ciências Tecnológicas",
            "address": "Rua Paulo Malschitzki, 200 - Zona Industrial Norte",
            "location": "Bloco F, Sala 204",
            "email": "contato@lar.udesc.br"
        },
        "tags": ["Robótica Móvel", "Visão Computacional", "Controle", "Manipuladores", "IA"],
        "prof": ("prof_robo", "prof.robo@udesc.br"),
        "students": ["ana", "bruno", "carlos", "diego", "elena"],
        "projects": [
            {"name": "Robô Kuka V2", "desc": "Manipulador industrial para tarefas de precisão.", "cat": "Manipuladores"},
            {"name": "Drone de Resgate", "desc": "Voo autônomo em ambientes de floresta.", "cat": "Robótica Móvel"},
            {"name": "AGV Logístico", "desc": "Robô de armazém com navegação SLAM.", "cat": "Robótica Móvel"},
            {"name": "Reconhecimento Facial", "desc": "Sistema de segurança baseado em Deep Learning.", "cat": "Visão Computacional"}
        ],
        "tasks": ["Calibrei o sensor IMU.", "Soldei a PCB do motor.", "Atualizei o ROS2.", "Treinei a rede YOLO.", "Imprimi peça em 3D."],
        "skills": "Python,C++,ROS,Soldagem,Impressão 3D"
    },
    {
        "name": "Laboratório de Química Orgânica", 
        "acronym": "LQO",
        "meta": {
            "affiliation": "UDESC - Departamento de Química",
            "address": "Rua Paulo Malschitzki, 200",
            "location": "Bloco Q, Laboratório 101",
            "email": "lab.quimica@udesc.br"
        },
        "tags": ["Síntese", "Análise", "Polímeros", "Bioquímica"],
        "prof": ("prof_quimica", "prof.quimica@udesc.br"),
        "students": ["fernanda", "gabriel", "hugo", "ines"],
        "projects": [
            {"name": "Novos Polímeros", "desc": "Plásticos biodegradáveis a partir de amido.", "cat": "Polímeros"},
            {"name": "Análise de Água do Rio", "desc": "Monitoramento de pH e metais pesados.", "cat": "Análise"},
            {"name": "Catálise Enzimática", "desc": "Aceleração de reações industriais.", "cat": "Bioquímica"}
        ],
        "tasks": ["Realizei a titulação.", "Preparei a solução tampão.", "Limpei a vidraria.", "Analisei espectro IR.", "Misturei reagentes."],
        "skills": "Química,Análise,Segurança,Vidraria,Excel"
    },
    {
        "name": "Núcleo de Redes e Segurança", 
        "acronym": "NRED",
        "meta": {
            "affiliation": "Cisco Networking Academy",
            "address": "Campus Universitário - Bloco I",
            "location": "Sala de Servidores 02",
            "email": "admin@nred.org"
        },
        "tags": ["Infraestrutura", "Cibersegurança", "Cloud", "IoT"],
        "prof": ("prof_redes", "prof.redes@udesc.br"),
        "students": ["joao", "kleber", "lucas", "maria"],
        "projects": [
            {"name": "Firewall Inteligente", "desc": "Bloqueio de intrusão via IA.", "cat": "Cibersegurança"},
            {"name": "Cluster Kubernetes", "desc": "Infraestrutura em nuvem privada.", "cat": "Cloud"},
            {"name": "Sensores IoT", "desc": "Monitoramento de temperatura do datacenter.", "cat": "IoT"}
        ],
        "tasks": ["Configurei a VLAN 20.", "Atualizei o firmware do switch.", "Analisei logs SSH.", "Configurei o Docker.", "Testei o ping."],
        "skills": "Linux,Redes,Cisco,Docker,Python,Shell"
    },
    {
        "name": "Lab de Física Experimental", 
        "acronym": "LAF",
        "meta": {
            "affiliation": "Instituto de Física",
            "address": "Bloco C - Térreo",
            "location": "Sala Escura de Óptica",
            "email": "fisica@udesc.br"
        },
        "tags": ["Óptica", "Mecânica", "Termodinâmica", "Astronomia"],
        "prof": ("prof_fisica", "prof.fisica@udesc.br"),
        "students": ["nelson", "olivia", "paulo"],
        "projects": [
            {"name": "Acelerador de Partículas", "desc": "Mini ciclotron didático.", "cat": "Mecânica"},
            {"name": "Laser de Alta Potência", "desc": "Estudo de refração em cristais.", "cat": "Óptica"},
            {"name": "Telescópio Digital", "desc": "Rastreamento automatizado de estrelas.", "cat": "Astronomia"}
        ],
        "tasks": ["Alinhei os espelhos.", "Calibrei o laser.", "Medi a radiação.", "Ajustei a lente.", "Registei dados do osciloscópio."],
        "skills": "Matemática,Física,Óptica,Excel,Python"
    }
]

# Observações genéricas para variar os logs
generic_obs = [
    "Tudo funcionou como esperado.",
    "Tive dificuldades com a documentação técnica.",
    "Preciso de ajuda do professor na próxima etapa.",
    "O equipamento estava ocupado hoje.",
    "Leitura instável nos sensores.",
    None, None, None, None # Muitos dias sem obs para realismo
]

def populate():
    print("\n=== POPULAÇÃO COMPLETA MULTI-LAB (V2) ===\n")

    try:
        print("1. Limpando base de dados...")
        LogEntry.query.delete()
        Project.query.delete()
        ProjectTag.query.delete() # Limpa tags antigas
        User.query.delete()
        Laboratory.query.delete()
        db.session.commit()
        print("   [OK] Base limpa.")
    except Exception as e:
        db.session.rollback()
        print(f"   [AVISO] Erro ao limpar (tabelas novas?): {e}")

    # --- SUPER ADMIN ---
    admin = User(username='admin', email='admin@udesc.br', role='admin', is_approved=True, is_active=True)
    admin.set_password('admin')
    db.session.add(admin)
    print("   -> Super Admin criado (Login: admin / Senha: admin).")

    total_logs = 0
    
    # --- LOOP DE CRIAÇÃO DOS LABS ---
    for lab_conf in labs_config:
        print(f"\n--- Configurando {lab_conf['name']} ---")
        
        # 1. Criar Lab com Detalhes
        lab = Laboratory(
            name=lab_conf['name'], 
            acronym=lab_conf['acronym'],
            affiliation_name=lab_conf['meta']['affiliation'],
            address=lab_conf['meta']['address'],
            location=lab_conf['meta']['location'],
            contact_email=lab_conf['meta']['email'],
            image_file='default_lab.jpg',
            cover_file='default_lab_cover.jpg'
        )
        db.session.add(lab)
        db.session.commit() # Commit para ter ID

        # 2. Criar Tags Personalizadas do Lab
        for tag_name in lab_conf['tags']:
            tag = ProjectTag(name=tag_name, laboratory=lab)
            db.session.add(tag)
        
        # 3. Criar Professor
        p_user, p_email = lab_conf['prof']
        prof = User(
            username=p_user, email=p_email, role='professor',
            is_approved=True, is_active=True, laboratory=lab,
            image_file='default.jpg', invite_status='accepted',
            bio=f"Coordenador do {lab.acronym}. Focado em {lab_conf['tags'][0]}."
        )
        prof.set_password(p_user)
        db.session.add(prof)

        # 4. Criar Projetos
        lab_projects_objs = []
        for p_data in lab_conf['projects']:
            proj = Project(
                name=p_data['name'], 
                description=p_data['desc'],
                category=p_data['cat'], # Usa uma das tags criadas
                image_file='default_project.jpg',
                laboratory=lab
            )
            db.session.add(proj)
            lab_projects_objs.append(proj)
        
        db.session.commit()

        # 5. Criar Alunos e Logs (Histórico 2025)
        months = range(1, 12) # Jan a Nov
        current_year = 2025

        for s_name in lab_conf['students']:
            student = User(
                username=s_name, email=f"{s_name}@udesc.br", role='bolsista',
                is_approved=True, is_active=True, laboratory=lab,
                image_file='default.jpg', skills=lab_conf['skills'],
                bio=f"Estudante pesquisador do {lab.acronym}."
            )
            student.set_password(s_name)
            db.session.add(student)
            
            # Gerar Logs
            for month in months:
                _, num_days = calendar.monthrange(current_year, month)
                
                # Variabilidade de produtividade
                logs_this_month = random.randint(4, 12)
                used_days = set()
                
                while len(used_days) < logs_this_month:
                    day = random.randint(1, num_days)
                    entry_date = date(current_year, month, day)
                    
                    if day not in used_days and entry_date.weekday() < 5:
                        
                        proj = random.choice(lab_projects_objs)
                        
                        log = LogEntry(
                            entry_date=entry_date,
                            project=proj.name,
                            project_id=proj.id,
                            tasks_completed=random.choice(lab_conf['tasks']),
                            observations=random.choice(generic_obs),
                            next_steps="Continuar amanhã.",
                            author=student
                        )
                        db.session.add(log)
                        used_days.add(day)
                        total_logs += 1
            
            print(f"   -> Aluno '{s_name}' criado.")

    db.session.commit()
    print(f"\n=== CONCLUÍDO ===")
    print(f"Total de Registros Gerados: {total_logs}")
    print("------------------------------------------------")
    print("USUÁRIOS PARA TESTE:")
    print("1. Admin: 'admin'")
    print("2. Robótica: 'prof_robo'")
    print("3. Química: 'prof_quimica'")
    print("4. Redes: 'prof_redes'")

if __name__ == '__main__':
    populate()