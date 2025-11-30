import random
import calendar
from datetime import date, timedelta
from app import create_app, db
from app.models import User, LogEntry, Project, Laboratory

app = create_app()
app.app_context().push()

# --- DADOS TEMÁTICOS PARA GERAR REALISMO ---

# 1. Configuração dos Laboratórios
labs_config = [
    {
        "name": "Laboratório de Robótica (LAR)", "acronym": "LAR", "cat": "Robotica",
        "prof": ("prof_robo", "prof.robo@udesc.br"),
        "students": ["ana", "bruno", "carlos", "diego", "elena"],
        "projects": [
            {"name": "Robô Kuka V2", "desc": "Manipulador industrial."},
            {"name": "Drone de Resgate", "desc": "Voo autônomo em florestas."},
            {"name": "AGV Logístico", "desc": "Robô de armazém."},
            {"name": "Visão Computacional", "desc": "Reconhecimento de faces."}
        ],
        "tasks": ["Calibrei o sensor IMU.", "Soldei a PCB do motor.", "Atualizei o ROS2.", "Treinei a rede neural YOLO.", "Imprimi peça em 3D."],
        "skills": "Python,C++,ROS,Soldagem,Impressão 3D"
    },
    {
        "name": "Laboratório de Química Orgânica (LQO)", "acronym": "LQO", "cat": "Ciencia",
        "prof": ("prof_quimica", "prof.quimica@udesc.br"),
        "students": ["fernanda", "gabriel", "hugo", "ines"],
        "projects": [
            {"name": "Síntese de Polímeros", "desc": "Plásticos biodegradáveis."},
            {"name": "Análise de Água", "desc": "Monitoramento do Rio."},
            {"name": "Catálise Enzimática", "desc": "Aceleração de reações."}
        ],
        "tasks": ["Realizei a titulação.", "Preparei a solução tampão.", "Limpei a vidraria.", "Analisei espectro IR.", "Misturei reagentes."],
        "skills": "Química,Análise,Segurança,Vidraria"
    },
    {
        "name": "Núcleo de Redes e Segurança (NRED)", "acronym": "NRED", "cat": "TI",
        "prof": ("prof_redes", "prof.redes@udesc.br"),
        "students": ["joao", "kleber", "lucas", "maria"],
        "projects": [
            {"name": "Firewall Inteligente", "desc": "Bloqueio via IA."},
            {"name": "Cluster Kubernetes", "desc": "Infraestrutura em nuvem."},
            {"name": "Monitoramento IoT", "desc": "Sensores de temperatura."}
        ],
        "tasks": ["Configurei a VLAN 20.", "Atualizei o switch.", "Analisei logs SSH.", "Configurei o Docker.", "Testei o ping."],
        "skills": "Linux,Redes,Cisco,Docker,Python"
    },
    {
        "name": "Lab de Física Experimental (LAF)", "acronym": "LAF", "cat": "Fisica",
        "prof": ("prof_fisica", "prof.fisica@udesc.br"),
        "students": ["nelson", "olivia", "paulo"],
        "projects": [
            {"name": "Acelerador de Partículas", "desc": "Mini ciclotron."},
            {"name": "Laser de Alta Potência", "desc": "Corte a laser."},
            {"name": "Telescópio Digital", "desc": "Rastreamento de estrelas."}
        ],
        "tasks": ["Alinhei os espelhos.", "Calibrei o laser.", "Medi a radiação.", "Ajustei a lente.", "Registei dados do osciloscópio."],
        "skills": "Matemática,Física,Óptica,Excel"
    }
]

# Observações genéricas
generic_obs = [
    "Tudo funcionou como esperado.",
    "Tive dificuldades com a documentação.",
    "Preciso de ajuda do professor na próxima etapa.",
    "Equipamento estava ocupado hoje.",
    None, None, None # Muitos dias sem obs
]

def populate():
    print("\n=== POPULAÇÃO MASSIVA MULTI-TENANT ===\n")

    try:
        print("1. Limpando base de dados...")
        LogEntry.query.delete()
        Project.query.delete()
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
    print("   -> Super Admin criado.")

    total_logs = 0
    
    # --- LOOP POR LABORATÓRIO ---
    for lab_conf in labs_config:
        print(f"\n--- Configurando {lab_conf['name']} ---")
        
        # 1. Criar Lab
        lab = Laboratory(name=lab_conf['name'], acronym=lab_conf['acronym'])
        db.session.add(lab)
        db.session.commit()

        # 2. Criar Professor
        p_user, p_email = lab_conf['prof']
        prof = User(
            username=p_user, email=p_email, role='professor',
            is_approved=True, is_active=True, laboratory=lab,
            image_file='default.jpg', invite_status='accepted'
        )
        prof.set_password(p_user) # Senha fácil para testes
        db.session.add(prof)

        # 3. Criar Projetos
        lab_projects_objs = []
        for p_data in lab_conf['projects']:
            proj = Project(
                name=p_data['name'], 
                description=p_data['desc'],
                category=lab_conf['cat'],
                image_file='default_project.jpg',
                laboratory=lab
            )
            db.session.add(proj)
            lab_projects_objs.append(proj)
        
        db.session.commit() # Commit para ter IDs dos projetos

        # 4. Criar Alunos e Logs
        # Vamos simular um ano inteiro (2025)
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
            
            # Gerar Logs para este aluno
            student_log_count = 0
            
            for month in months:
                _, num_days = calendar.monthrange(current_year, month)
                
                # Frequência: Alunos dedicados fazem 15 logs/mês, outros 5
                logs_this_month = random.randint(5, 18)
                days_worked = set()
                
                # Tenta criar um streak (semana cheia)
                streak_start = random.randint(1, 20)
                for k in range(5): 
                    if streak_start + k <= num_days: days_worked.add(streak_start + k)

                # Preenche o resto dos dias aleatoriamente
                while len(days_worked) < logs_this_month:
                    days_worked.add(random.randint(1, num_days))
                
                for day in days_worked:
                    d = date(current_year, month, day)
                    if d.weekday() < 5: # Apenas dias de semana
                        # Escolhe projeto e tarefa do contexto do lab
                        proj = random.choice(lab_projects_objs)
                        task = random.choice(lab_conf['tasks'])
                        
                        log = LogEntry(
                            entry_date=d,
                            project=proj.name,
                            project_id=proj.id,
                            tasks_completed=task,
                            observations=random.choice(generic_obs),
                            next_steps="Continuar amanhã.",
                            author=student
                        )
                        db.session.add(log)
                        student_log_count += 1
                        total_logs += 1
            
            print(f"   -> Aluno '{s_name}' criado ({student_log_count} logs).")

    db.session.commit()
    print(f"\n=== CONCLUÍDO ===")
    print(f"Total de Laboratórios: {len(labs_config)}")
    print(f"Total de Registos Gerados: {total_logs}")
    print("------------------------------------------------")
    print("USUÁRIOS PARA TESTE (Senha igual ao usuário):")
    print("1. Admin Geral: 'admin'")
    print("2. Prof. Robótica: 'prof_robo' (Vê alunos Ana, Bruno...)")
    print("3. Prof. Química: 'prof_quimica' (Vê alunos Fernanda, Gabriel...)")
    print("4. Aluno: 'ana' (Do Lab de Robótica)")

if __name__ == '__main__':
    populate()