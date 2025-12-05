import itertools
from datetime import date, timedelta
import calendar
from flask import json, render_template, flash, redirect, url_for, request, Blueprint, abort, current_app, jsonify, make_response
from app import db
from app.forms import ActivateAccountForm, EditLabForm, LabForm, LoginForm, RegistrationForm, LogEntryForm, EditProfileForm, ChangePasswordForm, ProjectForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import ProjectTag, User, LogEntry, Project, Laboratory
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from functools import wraps
import google.generativeai as genai
import markdown
import csv
import io
import secrets
from PIL import Image
import os
import qrcode
import base64
from io import BytesIO
from app.email import send_invite_email, send_password_reset_email

bp = Blueprint('main', __name__)

# Dicionário de meses global
meses = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Permite se for Professor OU Admin
        if current_user.role not in ['professor', 'admin']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Permite APENAS se for Admin
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- FUNÇÃO MESTRE (O MOTOR) ---
def save_image_file(form_picture, folder, output_size=None, max_width=None):
    """
    Função genérica para salvar, renomear e redimensionar imagens.
    :param folder: Nome da subpasta dentro de static (ex: 'profile_pics')
    :param output_size: Tupla (largura, altura) para thumbnail (corta/ajusta)
    :param max_width: Largura máxima para redimensionamento proporcional (para capas)
    """
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # Define o caminho completo
    full_directory = os.path.join(current_app.root_path, 'static', folder)
    
    # Cria a pasta se não existir (Segurança)
    if not os.path.exists(full_directory):
        os.makedirs(full_directory)
        
    picture_path = os.path.join(full_directory, picture_fn)

    # Abre a imagem
    i = Image.open(form_picture)

    # Lógica de Redimensionamento
    if max_width and i.width > max_width:
        # Redimensiona mantendo a proporção (para Capas)
        ratio = max_width / float(i.width)
        new_height = int((float(i.height) * float(ratio)))
        i = i.resize((max_width, new_height), Image.Resampling.LANCZOS)
    elif output_size:
        # Cria thumbnail quadrado (para Avatares/Logos)
        i.thumbnail(output_size)

    # Salva
    i.save(picture_path)
    return picture_fn

# --- FUNÇÕES ESPECÍFICAS (AGORA SÃO ATALHOS) ---

def save_picture(form_picture):
    # Avatar de Usuário: Pasta profile_pics, Tamanho 150x150
    return save_image_file(form_picture, 'profile_pics', output_size=(150, 150))

def save_cover(form_cover):
    # Capa de Perfil/Projeto: Pasta profile_pics, Largura Max 1080px
    return save_image_file(form_cover, 'profile_pics', max_width=1080)

def save_lab_logo(form_picture):
    # Logo do Lab: Pasta lab_logos, Tamanho 300x300
    return save_image_file(form_picture, 'lab_logos', output_size=(300, 300))

def save_affiliation_logo(form_picture):
    # Logo da Afiliação: Pasta lab_logos, Tamanho 150x150 (Pequeno)
    return save_image_file(form_picture, 'lab_logos', output_size=(150, 150))

def get_lab_categories():
    if not current_user.is_authenticated or not current_user.laboratory_id:
        return [('Geral', 'Geral')]
    
    tags = ProjectTag.query.filter_by(laboratory_id=current_user.laboratory_id).all()
    choices = [(t.name, t.name) for t in tags]
    
    if not choices:
        return [('Geral', 'Geral')]
    return choices

@bp.context_processor
def inject_lab_info():
    if current_user.is_authenticated and current_user.laboratory:
        return dict(current_lab=current_user.laboratory)
    return dict(current_lab=None)

@bp.context_processor
def inject_global_vars():
    return dict(admin_email=current_app.config['ADMIN_EMAIL'])

# --- ROTA DE ERROS ---
@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# --- LANDING PAGE (PÚBLICA) ---
@bp.route('/')
def landing():
    if current_user.is_authenticated:
        if current_user.role == 'professor': return redirect(url_for('main.dashboard'))
        return redirect(url_for('main.index'))

    # --- DADOS DO GRAFO (THE BRAIN V2) ---
    nodes = []
    edges = []
    added_nodes = set()
    
    # Cores mais vivas para o Dark Mode
    c_lab = "#22c55e"   # Verde Neon
    c_proj = "#3b82f6"  # Azul
    c_user = "#94a3b8"  # Cinza
    
    labs = Laboratory.query.all()
    
    for lab in labs:
        l_id = f"l_{lab.id}"
        if l_id not in added_nodes:
            nodes.append({
                'id': l_id, 
                'label': lab.acronym, 
                'color': c_lab, 
                'size': 90,           # Tamanho da bolinha
                'shape': 'circle',    # 'circle' tenta por o texto dentro
                # AQUI ESTÁ A MUDANÇA: Tamanho da fonte (size: 40)
                'font': {'color': 'black', 'size': 100, 'face': 'Inter', 'vadjust': 0, 'bold': True}
            })
            added_nodes.add(l_id)
        
        for proj in lab.projects:
            p_id = f"p_{proj.id}"
            if p_id not in added_nodes:
                nodes.append({
                    'id': p_id, 
                    # Se quiser mostrar o nome do projeto, mude label para proj.name
                    # Mas cuidado: nomes longos poluem o grafo.
                    # Vou aumentar a bolinha para ficar mais visível
                    'title': f"Projeto: {proj.name}", 
                    'color': c_proj, 
                    'size': 30, 
                    'shape': 'dot' 
                })
                added_nodes.add(p_id)
            
            edges.append({'from': l_id, 'to': p_id, 'color': {'color': 'rgba(255,255,255,0.15)'}, 'length': 350})
            
        # Bolsistas
        students = lab.users.filter_by(role='bolsista', is_active=True).limit(8).all()
        for user in students:
            u_id = f"u_{user.id}"
            if u_id not in added_nodes:
                nodes.append({
                    'id': u_id, 
                    'title': user.username,
                    'color': c_user, 
                    'size': 25, 
                    'shape': 'dot'
                })
                added_nodes.add(u_id)
            
            # length: 200 afasta os alunos
            edges.append({'from': l_id, 'to': u_id, 'color': {'color': 'rgba(255,255,255,0.08)'}, 'length': 200})

            # Conexões de Projeto (tracejadas)
            user_projects = db.session.query(LogEntry.project_id).filter(
                LogEntry.user_id == user.id, LogEntry.project_id.isnot(None)
            ).distinct().all()

            for (proj_id,) in user_projects:
                target_p_id = f"p_{proj_id}"
                if target_p_id in added_nodes:
                     edges.append({
                         'from': u_id, 'to': target_p_id, 
                         'color': {'color': 'rgba(74, 222, 128, 0.2)'}, 
                         'dashes': True,
                         'length': 100 # Conexão mais curta
                     })

    graph_data = json.dumps({'nodes': nodes, 'edges': edges})

    # Stats normais
    stats = {
        'users': User.query.filter_by(is_active=True).count(),
        'projects': Project.query.count(),
        'logs': LogEntry.query.count()
    }
    
    return render_template('landing.html', title='Bem-vindo', stats=stats, graph_data=graph_data, labs=labs)

# --- PAINEL GERAL (SUPER ADMIN) ---
@bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    labs = Laboratory.query.order_by(Laboratory.name).all()
    
    # Estatísticas Globais
    total_users = User.query.count()
    total_projects = Project.query.count()
    total_logs = LogEntry.query.count()
    
    return render_template('admin_dashboard.html', title='Administração Geral', 
                           labs=labs, total_users=total_users, 
                           total_projects=total_projects, total_logs=total_logs)

@bp.route('/admin/lab/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_lab():
    form = LabForm()
    if form.validate_on_submit():
        # Salvar Imagens (se enviadas)
        logo_file = 'default_lab.jpg'
        if form.logo.data: logo_file = save_lab_logo(form.logo.data)
        
        cover_file = 'default_lab_cover.jpg'
        if form.cover.data: cover_file = save_cover(form.cover.data)
        
        aff_logo = None
        if form.affiliation_logo.data: aff_logo = save_lab_logo(form.affiliation_logo.data)

        # Criar Objeto
        lab = Laboratory(
            name=form.name.data, acronym=form.acronym.data, description=form.description.data,
            image_file=logo_file, cover_file=cover_file,
            affiliation_name=form.affiliation_name.data, affiliation_logo=aff_logo,
            address=form.address.data, location=form.location.data, contact_email=form.contact_email.data,
            website_link=form.website_link.data, instagram_link=form.instagram_link.data, linkedin_link=form.linkedin_link.data
        )
        db.session.add(lab)
        db.session.commit()
        
        # Lógica do Professor (Mantida igual)
        existing_user = User.query.filter_by(email=form.prof_email.data).first()
        if existing_user:
            existing_user.laboratory = lab
            existing_user.role = 'professor'
            flash(f'Professor {existing_user.username} associado ao laboratório.', 'info')
        else:
            random_pass = secrets.token_urlsafe(16)
            prof = User(username=form.prof_name.data, email=form.prof_email.data, role='professor', is_approved=True, is_active=True, laboratory=lab, invite_status='pending')
            prof.set_password(random_pass)
            db.session.add(prof)
            db.session.commit()
            send_invite_email(prof, lab.name)
            flash('Laboratório criado e convite enviado!', 'success')
        
        db.session.commit()
        return redirect(url_for('main.admin_dashboard'))
        
    return render_template('create_lab.html', title='Novo Laboratório', form=form, is_edit=False)

@bp.route('/admin/lab/<int:lab_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_lab(lab_id):
    lab = Laboratory.query.get_or_404(lab_id)
    current_prof = lab.users.filter_by(role='professor').first()
    
    form = LabForm()

    if form.validate_on_submit():
        # Atualizar Dados Básicos
        lab.name = form.name.data
        lab.acronym = form.acronym.data
        lab.description = form.description.data
        lab.affiliation_name = form.affiliation_name.data
        lab.address = form.address.data
        lab.location = form.location.data
        lab.contact_email = form.contact_email.data
        lab.website_link = form.website_link.data
        lab.instagram_link = form.instagram_link.data
        lab.linkedin_link = form.linkedin_link.data

        # Atualizar Imagens (Só se enviou novas)
        if form.logo.data: lab.image_file = save_lab_logo(form.logo.data)
        if form.cover.data: lab.cover_file = save_cover(form.cover.data)
        if form.affiliation_logo.data: lab.affiliation_logo = save_lab_logo(form.affiliation_logo.data)
        
        # Lógica de Troca de Professor (Mantida)
        if current_prof and current_prof.email != form.prof_email.data:
             # (Lógica de transferir lab igual ao anterior...)
             pass 

        db.session.commit()
        flash('Laboratório atualizado!', 'success')
        return redirect(url_for('main.admin_dashboard'))

    elif request.method == 'GET':
        # --- AQUI ESTÁ A MÁGICA: PREENCHER O FORMULÁRIO ---
        form.name.data = lab.name
        form.acronym.data = lab.acronym
        form.description.data = lab.description
        
        form.affiliation_name.data = lab.affiliation_name
        form.address.data = lab.address
        form.location.data = lab.location
        form.contact_email.data = lab.contact_email
        
        form.website_link.data = lab.website_link
        form.instagram_link.data = lab.instagram_link
        form.linkedin_link.data = lab.linkedin_link
        
        if current_prof:
            form.prof_name.data = current_prof.username
            form.prof_email.data = current_prof.email

    # Passar URLs das imagens atuais para preview
    lab_logo = url_for('static', filename='lab_logos/' + lab.image_file)
    lab_cover = url_for('static', filename='profile_pics/' + lab.cover_file)
    
    return render_template('create_lab.html', title='Editar Laboratório', form=form, is_edit=True, 
                           lab_logo=lab_logo, lab_cover=lab_cover)

@bp.route('/team/invite', methods=['GET', 'POST'])
@login_required
@professor_required
def invite_member():
    # Reutilizamos um form simples ou criamos um InviteForm (email, role)
    # Vou simular o form aqui para brevidade
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role') # 'professor' ou 'bolsista'
        name_hint = email.split('@')[0] # Nome provisório

        # Verifica se já existe
        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado no sistema.', 'warning')
        else:
            # Cria o utilizador pré-aprovado vinculado ao MEU laboratório
            random_pass = secrets.token_urlsafe(16)
            new_user = User(
                username=name_hint,
                email=email,
                role=role,
                is_approved=True, # Já nasce aprovado pois foi convidado
                is_active=True,
                laboratory_id=current_user.laboratory_id, # <--- AQUI ESTÁ A MÁGICA
                invite_status='pending'
            )
            new_user.set_password(random_pass)
            db.session.add(new_user)
            db.session.commit()

            # Envia o e-mail (reutiliza a função de convite que já fizemos)
            # Pode adaptar o texto do email para diferenciar "Novo Admin" de "Novo Aluno" se quiser
            send_invite_email(new_user, current_user.laboratory.name)
            
            flash(f'Convite enviado para {email}.', 'success')
            return redirect(url_for('main.dashboard')) # Ou uma página de gestão de equipe

    return render_template('invite_member.html', title='Convidar Membro')

@bp.route('/admin/lab/<int:lab_id>/delete')
@login_required
@admin_required
def delete_lab(lab_id):
    lab = Laboratory.query.get_or_404(lab_id)
    
    # 1. Proteção: Não apagar o laboratório onde você está logado agora
    if current_user.laboratory_id == lab.id:
        flash('Segurança: Você não pode apagar o laboratório que está a usar no momento. Mude de laboratório ou crie outro admin.', 'danger')
        return redirect(url_for('main.admin_dashboard'))

    try:
        print(f"--- INICIANDO EXCLUSÃO DO LAB: {lab.name} ---")

        # A. Identificar todos os usuários deste laboratório
        # Usamos .all() para pegar a lista de objetos
        users = User.query.filter_by(laboratory_id=lab.id).all()
        user_ids = [u.id for u in users] # Lista de IDs: [1, 2, 5...]

        # B. Apagar TODOS os Logs desses usuários (Limpeza da base da pirâmide)
        # Usamos o operador IN para apagar em lote, que é muito mais rápido e seguro
        if user_ids:
            deleted_logs = LogEntry.query.filter(LogEntry.user_id.in_(user_ids)).delete(synchronize_session=False)
            print(f"   -> {deleted_logs} logs apagados.")
        
        # C. Apagar TODOS os Projetos deste laboratório
        deleted_projects = Project.query.filter_by(laboratory_id=lab.id).delete(synchronize_session=False)
        print(f"   -> {deleted_projects} projetos apagados.")

        # D. Apagar TODOS os Usuários deste laboratório
        # Agora podemos apagar, pois eles não têm mais logs presos a eles
        deleted_users = User.query.filter_by(laboratory_id=lab.id).delete(synchronize_session=False)
        print(f"   -> {deleted_users} usuários apagados.")

        # E. Finalmente, apagar o Laboratório
        db.session.delete(lab)
        
        # F. O Grande Commit (Aplica tudo de uma vez)
        db.session.commit()
        
        print("--- EXCLUSÃO CONCLUÍDA COM SUCESSO ---")
        flash(f'Laboratório "{lab.name}" e todos os seus dados foram removidos permanentemente.', 'success')

    except Exception as e:
        # Se der qualquer erro no meio, desfaz TUDO. Nada é apagado.
        db.session.rollback()
        print(f"!!! ERRO AO APAGAR LAB: {e}")
        flash('Erro crítico ao tentar apagar o laboratório. Operação cancelada e dados restaurados.', 'danger')

    return redirect(url_for('main.admin_dashboard'))

# --- EDITAR REGISTRO DE DIÁRIO ---
@bp.route('/log/<int:log_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    log = LogEntry.query.get_or_404(log_id)
    
    # 1. SEGURANÇA: Só o próprio autor pode editar
    if log.author != current_user:
        abort(403)
        
    # 2. SEGURANÇA: Bloqueio temporal (Ex: 7 dias)
    # Se o registro tiver mais de 7 dias, não pode ser editado
    delta = date.today() - log.entry_date
    if delta.days > 7:
        flash('Este registro é antigo demais para ser editado (limite de 7 dias).', 'warning')
        return redirect(url_for('main.index'))

    form = LogEntryForm()
    
    # Precisamos repopular o Select de Projetos (igual ao index)
    lab_id = current_user.laboratory_id
    projects = []
    if lab_id:
        projects = Project.query.filter_by(laboratory_id=lab_id).order_by(Project.name).all()
        
    project_choices = [(p.id, p.name) for p in projects]
    project_choices.insert(0, (0, 'Geral / Outros (Sem Projeto Específico)'))
    form.project_select.choices = project_choices

    if form.validate_on_submit():
        # Atualiza os campos
        log.entry_date = form.entry_date.data
        log.tasks_completed = form.tasks_completed.data
        log.observations = form.observations.data
        log.next_steps = form.next_steps.data
        
        # Atualiza o projeto
        selected_id = form.project_select.data
        if selected_id and selected_id > 0:
            proj = Project.query.get(selected_id)
            if proj:
                log.project = proj.name
                log.project_id = proj.id
        else:
            log.project = "Geral / Outros"
            log.project_id = None
            
        db.session.commit()
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('main.index'))
        
    elif request.method == 'GET':
        # Preenche o formulário com os dados existentes
        form.entry_date.data = log.entry_date
        form.tasks_completed.data = log.tasks_completed
        form.observations.data = log.observations
        form.next_steps.data = log.next_steps
        # Seleciona o projeto atual no dropdown
        form.project_select.data = log.project_id if log.project_id else 0

    return render_template('edit_log.html', title='Editar Registro', form=form, log=log)

@bp.route('/log/<int:log_id>/delete')
@login_required
def delete_log(log_id):
    log = LogEntry.query.get_or_404(log_id)
    
    # 1. SEGURANÇA: Só o próprio autor pode apagar
    if log.author != current_user:
        abort(403)
        
    # 2. SEGURANÇA: Bloqueio temporal (7 dias)
    delta = date.today() - log.entry_date
    if delta.days > 7:
        flash('Este registro é antigo demais para ser apagado.', 'warning')
        return redirect(url_for('main.index'))

    db.session.delete(log)
    db.session.commit()
    
    flash('Registro removido com sucesso.', 'success')
    return redirect(url_for('main.index'))

# --- ROTA INDEX (BOLSISTA) ---
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if current_user.role == 'professor':
        return redirect(url_for('main.dashboard'))

    form = LogEntryForm()
    
    # FILTRO: Mostrar apenas projetos do MEU laboratório
    lab_id = current_user.laboratory_id
    if lab_id:
        projects = Project.query.filter_by(laboratory_id=lab_id).order_by(Project.name).all()
    else:
        projects = []
    
    project_choices = [(p.id, p.name) for p in projects]
    project_choices.insert(0, (0, 'Geral / Outros (Sem Projeto Específico)'))
    form.project_select.choices = project_choices

    # Preenchimento automático via URL
    if request.method == 'GET' and request.args.get('fill_date'):
        try:
            fill_date = date.fromisoformat(request.args.get('fill_date'))
            form.entry_date.data = fill_date
            flash(f'Data selecionada: {fill_date.strftime("%d/%m/%Y")}', 'info')
        except ValueError: pass

    if form.validate_on_submit():
        selected_id = form.project_select.data
        project_name_str = "Geral / Outros"
        project_db_id = None 

        if selected_id and selected_id > 0:
            # SEGURANÇA: Verificar se o projeto pertence ao laboratório
            proj = Project.query.filter_by(id=selected_id, laboratory_id=current_user.laboratory_id).first()
            if proj:
                project_name_str = proj.name
                project_db_id = proj.id
            else:
                flash('Erro: Projeto inválido.', 'danger')
                return redirect(url_for('main.index'))

        log_entry = LogEntry(
            entry_date=form.entry_date.data,
            project=project_name_str,
            project_id=project_db_id,
            tasks_completed=form.tasks_completed.data,
            observations=form.observations.data,
            next_steps=form.next_steps.data,
            author=current_user
        )
        db.session.add(log_entry)
        try:
            db.session.commit()
            flash('Seu registro foi salvo com sucesso!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Você já possui um registro para esta data.', 'danger')
        return redirect(url_for('main.index'))

    # Visualização de Logs
    today = date.today()
    has_log_today = LogEntry.query.filter_by(author=current_user, entry_date=today).first() is not None
    year = request.args.get('ano', default=today.year, type=int)
    month = request.args.get('mes', default=today.month, type=int)
    current_date = date(year, month, 1)
    prev_month_date = current_date - timedelta(days=1)
    next_month_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    _, num_days_in_month = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days_in_month)
    
    logs_in_month = LogEntry.query.filter_by(author=current_user).filter(LogEntry.entry_date >= start_date, LogEntry.entry_date <= end_date).order_by(LogEntry.entry_date.desc()).all()
    logs_lookup = {log.entry_date.day for log in logs_in_month}
    
    days_status_list = []
    for day in range(1, num_days_in_month + 1):
        current_day_date = date(year, month, day)
        is_weekend_day = current_day_date.weekday() >= 5
        has_log = day in logs_lookup
        show_icon = True; icon_type = 'none'
        if has_log: icon_type = 'check'
        elif current_day_date > today: show_icon = False
        elif is_weekend_day: show_icon = False
        else: icon_type = 'times'
        days_status_list.append({'day': day, 'show_icon': show_icon, 'icon_type': icon_type, 'is_weekend': is_weekend_day})
    
    days_header_list = [{'day': d, 'is_weekend': date(year, month, d).weekday() >= 5} for d in range(1, num_days_in_month + 1)]

    return render_template('index.html', title='Página Inicial', form=form, logs_to_display=logs_in_month, current_month_name=f"{meses[month]} de {year}", has_log_today=has_log_today, days_status=days_status_list, days_header=days_header_list, prev_month={'ano': prev_month_date.year, 'mes': prev_month_date.month}, next_month={'ano': next_month_date.year, 'mes': next_month_date.month},today_date_obj=date.today())

# --- DASHBOARD (PROFESSOR) ---
@bp.route('/dashboard')
@login_required
@professor_required
def dashboard():
    lab_id = current_user.laboratory_id

    pending_users = User.query.filter_by(laboratory_id=lab_id, is_approved=False).all()
    active_bolsistas = User.query.filter_by(laboratory_id=lab_id, role='bolsista', is_approved=True, is_active=True).order_by(User.username).all()
    inactive_bolsistas = User.query.filter_by(laboratory_id=lab_id, role='bolsista', is_approved=True, is_active=False).order_by(User.username).all()
    
    today = date.today()
    
    # Gráficos filtrados por Lab
    dates_labels = []; dates_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = LogEntry.query.join(User).filter(User.laboratory_id == lab_id, func.date(LogEntry.entry_date) == day).count()
        dates_labels.append(day.strftime('%d/%m'))
        dates_counts.append(count)

    start_date_projects = today - timedelta(days=30)
    projects_data = db.session.query(LogEntry.project, func.count(LogEntry.id))\
        .join(User).filter(User.laboratory_id == lab_id, LogEntry.entry_date >= start_date_projects)\
        .group_by(LogEntry.project).order_by(func.count(LogEntry.id).desc()).limit(5).all()
    
    project_labels = [p[0] for p in projects_data]
    project_counts = [p[1] for p in projects_data]

    return render_template('dashboard.html', title='Painel do Professor', 
                           pending_users=pending_users, active_bolsistas=active_bolsistas, inactive_bolsistas=inactive_bolsistas,
                           today_date=today.strftime('%Y-%m-%d'), meses=meses, available_years=[today.year, today.year-1], 
                           current_year=today.year, current_month_num=today.month,
                           dates_labels=dates_labels, dates_counts=dates_counts, project_labels=project_labels, project_counts=project_counts)

# --- CALENDÁRIO ATUALIZADO ---
@bp.route('/calendar')
@login_required
@professor_required
def calendar_view():
    # 1. Busca apenas bolsistas do laboratório atual
    bolsistas = User.query.filter_by(
        role='bolsista', 
        is_approved=True, 
        is_active=True, 
        laboratory_id=current_user.laboratory_id
    ).order_by(User.username).all()
    
    # Lógica de Datas
    year = request.args.get('ano', default=date.today().year, type=int)
    month = request.args.get('mes', default=date.today().month, type=int)
    current_date = date(year, month, 1)
    prev_month_date = current_date - timedelta(days=1)
    next_month_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    _, num_days_in_month = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days_in_month)
    
    # 2. Busca logs apenas deste laboratório
    logs_in_month = LogEntry.query.join(User).filter(
        User.laboratory_id == current_user.laboratory_id,
        LogEntry.entry_date >= start_date, 
        LogEntry.entry_date <= end_date
    ).all()
    
    logs_lookup = {(log.user_id, log.entry_date.day) for log in logs_in_month}
    
    # Monta a Grade
    grid_data = []
    for bolsista in bolsistas:
        days_status = []
        for day in range(1, num_days_in_month + 1):
            is_weekend_day = date(year, month, day).weekday() >= 5
            has_log = (bolsista.id, day) in logs_lookup
            days_status.append({'day': day, 'has_log': has_log, 'is_weekend': is_weekend_day})
        grid_data.append({'student': bolsista, 'days': days_status})
        
    days_header = [{'day': d, 'is_weekend': date(year, month, d).weekday() >= 5} for d in range(1, num_days_in_month + 1)]
    
    # Variável 'meses' deve estar acessível (global ou definida aqui)
    current_month_name = f"{meses[month]} de {year}"
    
    return render_template('calendar_view.html', title="Calendário de Atividades", 
                           grid_data=grid_data, days_header=days_header, current_month_name=current_month_name, 
                           prev_month={'ano': prev_month_date.year, 'mes': prev_month_date.month}, 
                           next_month={'ano': next_month_date.year, 'mes': next_month_date.month})
# --- NOVA ROTA PARA A BUSCA GLOBAL ---
@bp.route('/search')
@login_required
@professor_required
def search():
    query = request.args.get('q', '', type=str)
    results = []
    if query:
        search_term = f"%{query}%"
        # Filtra logs onde o autor pertence ao mesmo laboratório do professor logado
        results = LogEntry.query.join(User).filter(
            User.laboratory_id == current_user.laboratory_id,
            User.role == 'bolsista',
            or_(
                LogEntry.project.ilike(search_term),
                LogEntry.tasks_completed.ilike(search_term),
                LogEntry.observations.ilike(search_term),
                LogEntry.next_steps.ilike(search_term)
            )
        ).order_by(LogEntry.entry_date.desc()).all()
    return render_template('search_results.html', title=f"Resultados para '{query}'", results=results, query=query)

@bp.route('/generate_report')
@login_required
@professor_required
def generate_report():
    api_key = current_app.config['GEMINI_API_KEY']
    if not api_key:
        flash('A chave de API do Gemini não está configurada no servidor.', 'danger')
        return redirect(url_for('main.dashboard'))

    # --- 1. DEFINIÇÃO DO PERÍODO ---
    if 'month_num' in request.args:
        report_type = 'month'
    else:
        report_type = 'week'

    start_period, end_period = None, None
    period_description, report_title = "", ""

    try:
        if report_type == 'month':
            month_num = request.args.get('month_num', type=int)
            year = request.args.get('year', type=int)
            if not month_num or not year: raise ValueError("Mês ou Ano em falta.")

            start_period = date(year, month_num, 1)
            _, last_day = calendar.monthrange(year, month_num)
            end_period = date(year, month_num, last_day)
            month_name = meses[month_num]
            period_description = f"o mês de {month_name} de {year}"
            report_title = f"Análise Mensal: {month_name} de {year}"
        else:
            selected_date_str = request.args.get('selected_date')
            selected_date = date.fromisoformat(selected_date_str) if selected_date_str else date.today()
            start_period = selected_date - timedelta(days=selected_date.weekday())
            end_period = start_period + timedelta(days=6)
            period_description = f"a semana de {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"
            report_title = f"Análise Semanal: {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"

    except Exception as e:
        flash(f'Período inválido: {e}', 'warning')
        return redirect(url_for('main.dashboard'))

    # --- 2. BUSCA DE DADOS (FILTRADO POR LAB) ---
    lab = current_user.laboratory
    
    logs_period = LogEntry.query.join(User).filter(
        User.laboratory_id == lab.id,
        User.role == 'bolsista',
        User.is_active == True,
        LogEntry.entry_date >= start_period,
        LogEntry.entry_date <= end_period
    ).order_by(User.username, LogEntry.entry_date).all()
    
    if not logs_period:
        flash(f"Não há registros n{period_description} para gerar análise.", 'info')
        return redirect(url_for('main.dashboard'))

    # --- 3. FORMATAÇÃO RICA (CONTEXTO PARA A IA) ---
    # Aqui está o segredo: Enviar mais do que apenas o log.
    
    formatted_logs = ""
    for log in logs_period:
        # Dados do Aluno
        student_info = f"{log.author.username}"
        if log.author.course:
            student_info += f" ({log.author.course})"
        student_skills = log.author.skills if log.author.skills else "N/A"

        # Dados do Projeto
        # Tenta pegar categoria do objeto Project, se existir vínculo
        proj_cat = "Geral"
        if log.parent_project:
            proj_cat = log.parent_project.category
        
        formatted_logs += f"""
        [REGISTRO]
        Aluno: {student_info} | Competências: {student_skills}
        Data: {log.entry_date.strftime('%d/%m/%Y')}
        Projeto: {log.project} (Área: {proj_cat})
        >> FEITO: {log.tasks_completed}
        >> OBSERVAÇÕES: {log.observations if log.observations else 'Nenhuma'}
        >> PRÓXIMOS PASSOS: {log.next_steps}
        --------------------------------------------------
        """
    
    # --- 4. CONSTRUÇÃO DO PROMPT ---
    
    # Contexto do Laboratório
    lab_context = f"""
    NOME DO LABORATÓRIO: {lab.name} ({lab.acronym})
    MISSÃO/DESCRIÇÃO: {lab.description if lab.description else 'Pesquisa e Desenvolvimento.'}
    """

    if report_type == 'month':
        prompt_focus = "análise de tendências, consistência dos alunos e progresso macro dos projetos"
        prompt_structure = "Estratégico e Resumido"
    else:
        prompt_focus = "ritmo semanal, bloqueios imediatos e alinhamento de tarefas"
        prompt_structure = "Tático e Orientado a Ação"

    master_prompt = f"""
    Atue como um Coordenador de Laboratório de Alta Performance (Sênior).
    Sua tarefa é analisar os diários de bordo dos bolsistas e gerar um relatório útil para o professor responsável.

    === CONTEXTO DO AMBIENTE ===
    {lab_context}

    === DADOS A ANALISAR ({period_description}) ===
    {formatted_logs}

    === INSTRUÇÕES DE ANÁLISE ===
    Foco da Análise: {prompt_focus}.
    
    1. Cruze as "Competências" do aluno com o "O que foi feito". Se um aluno está a realizar tarefas muito fora da sua área ou complexas, note isso (pode ser um talento ou uma dificuldade).
    2. Identifique gargalos: Se o mesmo problema (nas "Observações") aparece em dias seguidos ou em vários alunos.
    3. Identifique colaboração: Se alunos de projetos diferentes parecem estar a trabalhar em temas similares.

    === FORMATO DE SAÍDA (MARKDOWN) ===
    Não use saudações. Gere apenas o conteúdo abaixo:

    # {report_title}

    ## 1. Resumo Executivo
    (Um parágrafo denso sobre o estado geral do laboratório neste período. O ritmo está bom? Os projetos avançaram?)

    ## 2. Destaques e Avanços
    (Liste em tópicos as conquistas concretas. Cite nominalmente os alunos que tiveram entregas relevantes.)

    ## 3. Pontos de Atenção (Gargalos)
    (Liste problemas técnicos, bloqueios ou alunos que parecem estagnados/confusos. Seja direto e profissional.)

    ## 4. Sugestões de Gestão
    (Baseado na análise, sugira 3 ações para o professor: ex: "Reunir com aluno X sobre tema Y", "Comprar material Z", "Elogiar a equipa pelo avanço em W".)
    """

    # --- 5. CHAMADA À API ---
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro') 
        
        response = model.generate_content(master_prompt, request_options={'timeout': 120})
        report_text = response.text
        report_html = markdown.markdown(report_text)
        
    except Exception as e:
        print(f"Erro IA: {e}") 
        flash(f'Erro ao gerar relatório com IA. Verifique a chave de API ou tente novamente.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('report_view.html',
                           title=report_title,
                           report_html=report_html,
                           start_date=start_period,
                           end_date=end_period)

@bp.route('/report/print/<int:user_id>')
@login_required
def print_report(user_id):
    user = User.query.get_or_404(user_id)
    
    # Segurança básica
    if current_user.role != 'professor' and current_user.id != user.id: abort(403)
    if current_user.laboratory_id != user.laboratory_id: abort(403)

    # 1. Captura Data da URL (Se não vier, usa hoje)
    year = request.args.get('year', default=date.today().year, type=int)
    month = request.args.get('month', default=date.today().month, type=int)
    
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # 2. Busca Logs
    logs = LogEntry.query.filter_by(user_id=user.id).filter(
        LogEntry.entry_date >= start_date, 
        LogEntry.entry_date <= end_date
    ).order_by(LogEntry.entry_date).all()

    lab = user.laboratory
    month_name = meses[month]

    return render_template('print_report.html', 
                           user=user, 
                           lab=lab, 
                           logs=logs, 
                           report_date=start_date,
                           month_name=month_name,
                           generation_date=date.today())

@bp.route('/admin/test-report/<int:lab_id>')
@login_required
@professor_required # ou @admin_required
def test_report_specific(lab_id):
    lab = Laboratory.query.get_or_404(lab_id)
    try:
        # MUDANÇA AQUI: Pega do Config em vez de hardcoded
        my_email = current_app.config['ADMIN_EMAIL']
        
        from app.tasks import send_weekly_report_job
        # Envia o teste forçando o envio para o email do ADMIN_EMAIL
        send_weekly_report_job(test_mode=True, force_email=my_email, target_lab_id=lab.id)
        
        flash(f'Teste disparado! Verifique o e-mail de suporte: {my_email}', 'success')
    except Exception as e:
        flash(f'Erro ao executar: {e}', 'danger')
        print(f"Erro: {e}")
        
    return redirect(url_for('main.admin_dashboard'))

@bp.route('/view_logs/<int:student_id>')
@login_required
@professor_required
def view_logs(student_id):
    # --- SEGURANÇA: Busca estudante apenas se pertencer ao mesmo lab do professor ---
    student = User.query.filter_by(id=student_id, laboratory_id=current_user.laboratory_id).first_or_404()
    
    if student.role != 'bolsista': abort(404)
    
    target_year = request.args.get('ano', type=int)
    target_month = request.args.get('mes', type=int)
    
    all_logs = student.logs.order_by(LogEntry.entry_date.desc()).all()
    
    available_months = []
    for key, group in itertools.groupby(all_logs, key=lambda log: (log.entry_date.year, log.entry_date.month)):
        year, month = key
        month_name = f"{meses[month]} de {year}"
        available_months.append({'year': year, 'month': month, 'name': month_name})
        
    if target_year and target_month:
        display_logs = [log for log in all_logs if log.entry_date.year == target_year and log.entry_date.month == target_month]
        current_month_name = f"{meses[target_month]} de {target_year}"
    elif all_logs:
        most_recent = all_logs[0]
        mry, mrm = most_recent.entry_date.year, most_recent.entry_date.month
        display_logs = [log for log in all_logs if log.entry_date.year == mry and log.entry_date.month == mrm]
        current_month_name = f"{meses[mrm]} de {mry}"
    else:
        display_logs, current_month_name = [], "Nenhum registro encontrado"
        
    return render_template('view_logs.html', title=f"Diário de {student.username}", student=student, logs_to_display=display_logs, available_months=available_months, current_month_name=current_month_name)

# --- GESTÃO DE PROJETOS ---
@bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    form = ProjectForm()
    form.category.choices = get_lab_categories()
    if form.validate_on_submit():
        image_file = 'default_project.jpg'
        if form.image.data: image_file = save_cover(form.image.data)
        
        project = Project(
            name=form.name.data, description=form.description.data, category=form.category.data, image_file=image_file,
            laboratory_id=current_user.laboratory_id # Vincula ao lab atual
        )
        db.session.add(project)
        db.session.commit()
        flash('Projeto criado com sucesso!', 'success')
        return redirect(url_for('main.gallery'))
    return render_template('create_project.html', title='Novo Projeto', form=form)

@bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@professor_required
def edit_project(project_id):
    project = Project.query.filter_by(id=project_id, laboratory_id=current_user.laboratory_id).first_or_404()
    
    form = ProjectForm(original_name=project.name)
    form.category.choices = get_lab_categories()
    if form.validate_on_submit():
        project.name = form.name.data; project.description = form.description.data; project.category = form.category.data
        if form.image.data: project.image_file = save_cover(form.image.data)
        db.session.commit(); flash('Projeto atualizado!', 'success')
        return redirect(url_for('main.gallery'))
    elif request.method == 'GET':
        form.name.data = project.name; form.description.data = project.description; form.category.data = project.category
    image_file = url_for('static', filename='profile_pics/' + project.image_file)
    return render_template('create_project.html', title='Editar Projeto', form=form, legend='Editar Projeto', is_edit=True, image_file=image_file)

@bp.route('/project/<int:project_id>/delete')
@login_required
@professor_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, laboratory_id=current_user.laboratory_id).first_or_404()
    db.session.delete(project); db.session.commit()
    flash('Projeto removido.', 'success')
    return redirect(url_for('main.gallery'))

# --- GALERIA ---
@bp.route('/gallery')
@login_required
def gallery():
    projects = Project.query.filter_by(laboratory_id=current_user.laboratory_id).order_by(Project.name).all()
    return render_template('gallery.html', title='Galeria', projects=projects)

# --- COMUNIDADE ---
@bp.route('/community')
@login_required
def community():
    users = User.query.filter_by(laboratory_id=current_user.laboratory_id, is_active=True, is_approved=True).order_by(User.username).all()
    
    for user in users:
        last_log = user.logs.order_by(LogEntry.entry_date.desc()).first()
        if last_log:
            user.last_project_name = last_log.project; user.last_project_id = last_log.project_id; user.last_active_date = last_log.entry_date
        else:
            user.last_project_name = None; user.last_project_id = None; user.last_active_date = None
    return render_template('community.html', title='Comunidade', users=users, today=date.today(), timedelta=timedelta)

# --- DETALHES E QR CODE ---
@bp.route('/project/<int:project_id>')
@login_required
def project_details(project_id):
    project = Project.query.filter_by(id=project_id, laboratory_id=current_user.laboratory_id).first_or_404()
    logs = project.logs.order_by(LogEntry.entry_date.desc()).all()
    contributors = User.query.join(LogEntry).filter(LogEntry.project_id == project.id).distinct().all()
    return render_template('project_details.html', title=project.name, project=project, logs=logs, contributors=contributors)

@bp.route('/project/<int:project_id>/label')
@login_required
def project_label(project_id):
    project = Project.query.filter_by(id=project_id, laboratory_id=current_user.laboratory_id).first_or_404()
    project_url = url_for('main.public_project', project_id=project.id, _external=True)
    qr = qrcode.QRCode(version=1, box_size=10, border=4); qr.add_data(project_url); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO(); img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return render_template('project_label.html', title=f'Etiqueta - {project.name}', project=project, qr_code=img_str)

# --- ROTA PÚBLICA (QR CODE) ---
@bp.route('/p/<int:project_id>')
def public_project(project_id):
    project = Project.query.get_or_404(project_id)
    contributors = User.query.join(LogEntry).filter(LogEntry.project_id == project.id).distinct().all()
    recent_logs = project.logs.order_by(LogEntry.entry_date.desc()).limit(10).all()
    return render_template('project_public.html', title=project.name, project=project, contributors=contributors, recent_logs=recent_logs, now_date=date.today())

# --- MODO TV ---
@bp.route('/tv_mode')
@login_required
@professor_required
def tv_mode():
    # Filtrar pelo Laboratório do usuário
    lab_id = current_user.laboratory_id
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # Join com User para garantir que os logs são deste laboratório
    logs = LogEntry.query.join(User).filter(
        User.laboratory_id == lab_id,
        LogEntry.entry_date >= week_ago
    ).order_by(LogEntry.entry_date.desc()).limit(20).all()
    
    if not logs:
        logs = LogEntry.query.join(User).filter(User.laboratory_id == lab_id).order_by(LogEntry.entry_date.desc()).limit(5).all()

    return render_template('tv_mode.html', title='Modo TV', logs=logs)

# --- EXPORTAR CSV ---
@bp.route('/export_logs')
@login_required
@professor_required
def export_logs():
    # Exporta apenas logs do laboratório atual
    logs = LogEntry.query.join(User).filter(User.laboratory_id == current_user.laboratory_id).order_by(LogEntry.entry_date.desc()).all()
    si = io.StringIO(); cw = csv.writer(si, delimiter=';')
    cw.writerow(['Data', 'Bolsista', 'Projeto', 'Tarefas', 'Obs', 'Próximos'])
    for log in logs: cw.writerow([log.entry_date.strftime('%d/%m/%Y'), log.author.username, log.project, log.tasks_completed, log.observations or "", log.next_steps])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=relatorio.csv"; output.headers["Content-type"] = "text/csv"
    return output

# --- PENDÊNCIAS ---
@bp.route('/pending')
@login_required
def pending_logs():
    if current_user.role != 'bolsista': return redirect(url_for('main.dashboard'))
    missing = get_missing_dates(current_user) # Função usa filter_by(author=user), que já tem lab, seguro.
    return render_template('pending_logs.html', title='Pendências', missing_dates=missing)

# --- PERFIL E EDIÇÃO ---
@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username, current_user.email)
    if form.validate_on_submit():
        if form.picture.data: current_user.image_file = save_picture(form.picture.data)
        if form.cover.data: current_user.cover_file = save_cover(form.cover.data)
        current_user.username = form.username.data; current_user.email = form.email.data
        current_user.course = form.course.data; current_user.bio = form.bio.data
        current_user.skills = form.skills.data; current_user.lattes_link = form.lattes_link.data
        current_user.linkedin_link = form.linkedin_link.data; current_user.github_link = form.github_link.data
        db.session.commit(); flash('Perfil atualizado!', 'success')
        return redirect(url_for('main.user_profile', username=current_user.username))
    elif request.method == 'GET':
        form.username.data = current_user.username; form.email.data = current_user.email; form.confirm_email.data = current_user.email
        form.course.data = current_user.course; form.bio.data = current_user.bio; form.skills.data = current_user.skills
        form.lattes_link.data = current_user.lattes_link; form.linkedin_link.data = current_user.linkedin_link; form.github_link.data = current_user.github_link
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('edit_profile.html', title='Editar Perfil', form=form, image_file=image_file)

@bp.route('/user/<username>')
@login_required
def user_profile(username):
    # Filtro de segurança: só vejo perfis do meu laboratório
    user = User.query.filter_by(username=username, laboratory_id=current_user.laboratory_id).first_or_404()
    total_logs = user.logs.count()
    recent_logs = user.logs.order_by(LogEntry.entry_date.desc()).limit(5).all()
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('user_profile.html', user=user, total_logs=total_logs, image_file=image_file, recent_logs=recent_logs)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    # 1. Busca todos os laboratórios para o menu
    labs = Laboratory.query.order_by(Laboratory.name).all()
    
    # 2. Cria as opções: (ID, "Sigla - Nome")
    form.lab_select.choices = [(l.id, f"{l.acronym} - {l.name}") for l in labs]

    if form.validate_on_submit():
        # Busca o objeto do laboratório selecionado
        selected_lab = Laboratory.query.get(form.lab_select.data)
        
        user = User(
            username=form.username.data, 
            email=form.email.data,
            role='bolsista',       # Registro público é sempre bolsista
            is_active=False,       # Inativo até aprovação
            is_approved=False,
            laboratory=selected_lab # Vincula ao lab escolhido
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Solicitação enviada! Aguarde a aprovação do coordenador.', 'info')
        return redirect(url_for('main.login'))
        
    return render_template('register.html', title='Criar Conta', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'professor': return redirect(url_for('main.dashboard'))
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Inválido.', 'warning'); return redirect(url_for('main.login'))
        if not user.is_approved: flash('Não aprovado.', 'warning'); return redirect(url_for('main.login'))
        if not user.is_active: flash('Desativado.', 'warning'); return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        if current_user.role == 'professor': return redirect(url_for('main.dashboard'))
        return redirect(url_for('main.index'))
    return render_template('login.html', title='Entrar', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data): flash('Senha atual incorreta.', 'danger'); return redirect(url_for('main.change_password'))
        current_user.set_password(form.new_password.data); db.session.commit()
        flash('Senha alterada!', 'success'); return redirect(url_for('main.user_profile', username=current_user.username))
    return render_template('change_password.html', title='Alterar Senha', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user: send_password_reset_email(user)
        flash('Verifique o seu e-mail para as instruções.', 'info')
        return redirect(url_for('main.login'))
    return render_template('auth/reset_password_request.html', title='Recuperar Senha', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    user = User.verify_reset_token(token)
    if not user:
        flash('O link é inválido ou expirou.', 'danger')
        return redirect(url_for('main.index'))
    
    # --- LÓGICA DE DECISÃO ---
    if user.invite_status == 'pending':
        # FLUXO DE ATIVAÇÃO (Primeiro Acesso)
        form = ActivateAccountForm()
        
        # Preenche o username sugerido (baseado no email) na primeira vez
        if request.method == 'GET':
            form.username.data = user.username

        if form.validate_on_submit():
            # Verifica se o username mudou e se já existe
            if form.username.data != user.username:
                existing = User.query.filter_by(username=form.username.data).first()
                if existing:
                    flash('Este nome de usuário já está em uso. Escolha outro.', 'warning')
                    return render_template('auth/activate_account.html', title='Ativar Conta', form=form, user=user)
            
            user.username = form.username.data
            user.set_password(form.password.data)
            user.invite_status = 'accepted'
            
            db.session.commit()
            flash('Conta ativada com sucesso! Bem-vindo à equipe.', 'success')
            return redirect(url_for('main.login'))
            
        return render_template('auth/activate_account.html', title='Ativar Conta', form=form, user=user)

    else:
        # FLUXO DE RECUPERAÇÃO (Esqueceu a Senha)
        form = ResetPasswordForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            db.session.commit()
            flash('A sua senha foi redefinida com sucesso!', 'success')
            return redirect(url_for('main.login'))
            
        return render_template('auth/reset_password.html', title='Nova Senha', form=form, user=user)

# --- GESTÃO DE USUÁRIOS ---
@bp.route('/approve/<int:user_id>')
@login_required
@professor_required
def approve_user(user_id):
    # Segurança: Só aprovo usuários do meu lab
    user = User.query.filter_by(id=user_id, laboratory_id=current_user.laboratory_id).first_or_404()
    user.is_approved = True
    user.is_active = True
    db.session.commit()
    flash(f'O usuário {user.username} foi aprovado e ativado!', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/reject/<int:user_id>')
@login_required
@professor_required
def reject_user(user_id):
    user_to_reject = User.query.filter_by(id=user_id, is_approved=False, laboratory_id=current_user.laboratory_id).first_or_404()
    username = user_to_reject.username
    db.session.delete(user_to_reject)
    db.session.commit()
    flash(f'A solicitação do usuário {username} foi rejeitada.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/deactivate/<int:user_id>')
@login_required
@professor_required
def deactivate_user(user_id):
    user = User.query.filter_by(id=user_id, laboratory_id=current_user.laboratory_id).first_or_404()
    if user.role == 'bolsista':
        user.is_active = False; db.session.commit()
        flash(f'O bolsista {user.username} foi desativado.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/activate/<int:user_id>')
@login_required
@professor_required
def activate_user(user_id):
    user = User.query.filter_by(id=user_id, laboratory_id=current_user.laboratory_id).first_or_404()
    if user.role == 'bolsista':
        user.is_active = True; db.session.commit()
        flash(f'O bolsista {user.username} foi reativado.', 'success')
    return redirect(url_for('main.dashboard'))

def get_missing_dates(user, days_back=30):
    today = date.today()
    start_range = today - timedelta(days=days_back)
    # Garante que busca logs do lab certo
    logs = LogEntry.query.filter_by(author=user).filter(LogEntry.entry_date >= start_range, LogEntry.entry_date < today).all()
    logged_dates = {log.entry_date for log in logs}
    missing_dates = []
    for i in range(1, days_back + 1):
        check_date = today - timedelta(days=i)
        if check_date.weekday() < 5 and check_date not in logged_dates:
            missing_dates.append(check_date)
    return sorted(missing_dates, reverse=True)

@bp.route('/lab/settings', methods=['GET', 'POST'])
@login_required
@professor_required
def lab_settings():
    lab = current_user.laboratory
    form = EditLabForm()
    
    if form.validate_on_submit():
        # 1. Imagens (Só salva se houver upload novo)
        if form.logo.data: 
            lab.image_file = save_lab_logo(form.logo.data)
        if form.cover.data: 
            # Usa a função save_cover que já temos (ou crie save_lab_cover se preferir tamanho diferente)
            lab.cover_file = save_cover(form.cover.data) 
        if form.affiliation_logo.data: 
            lab.affiliation_logo = save_lab_logo(form.affiliation_logo.data)

        # 2. Dados de Texto
        lab.name = form.name.data
        lab.acronym = form.acronym.data
        lab.description = form.description.data
        lab.affiliation_name = form.affiliation_name.data
        lab.address = form.address.data
        lab.location = form.location.data
        lab.contact_email = form.contact_email.data
        lab.instagram_link = form.instagram_link.data
        lab.linkedin_link = form.linkedin_link.data
        lab.website_link = form.website_link.data
        
        # 3. Tags (Apaga as antigas e cria as novas)
        # Isso é uma estratégia simples. Para sistemas grandes, faríamos "diff".
        ProjectTag.query.filter_by(laboratory_id=lab.id).delete()
        
        if form.custom_tags.data:
            # Separa por vírgula e remove espaços
            tag_list = [t.strip() for t in form.custom_tags.data.split(',') if t.strip()]
            # Remove duplicatas usando set
            tag_list = list(set(tag_list))
            
            for tag_name in tag_list:
                new_tag = ProjectTag(name=tag_name, laboratory=lab)
                db.session.add(new_tag)
        
        db.session.commit()
        flash('Configurações do laboratório atualizadas com sucesso!', 'success')
        return redirect(url_for('main.lab_settings'))
    
    elif request.method == 'GET':
        # Preenche o formulário com os dados do banco
        form.name.data = lab.name
        form.acronym.data = lab.acronym
        form.description.data = lab.description
        form.affiliation_name.data = lab.affiliation_name
        form.address.data = lab.address
        form.location.data = lab.location
        form.contact_email.data = lab.contact_email
        form.instagram_link.data = lab.instagram_link
        form.linkedin_link.data = lab.linkedin_link
        form.website_link.data = lab.website_link
        
        # Carrega as tags para a string
        current_tags = ProjectTag.query.filter_by(laboratory_id=lab.id).all()
        form.custom_tags.data = ", ".join([t.name for t in current_tags])

    # Garante que as imagens têm fallback se forem None no banco
    logo_url = url_for('static', filename='lab_logos/' + (lab.image_file or 'default_lab.jpg'))
    cover_url = url_for('static', filename='profile_pics/' + (lab.cover_file or 'default_lab_cover.jpg'))
    aff_url = None
    if lab.affiliation_logo:
        aff_url = url_for('static', filename='lab_logos/' + lab.affiliation_logo)
    
    return render_template('lab_settings.html', title='Configurações', form=form, logo_url=logo_url, cover_url=cover_url, aff_url=aff_url)

@bp.route('/lab/<int:lab_id>')
def public_lab(lab_id):
    lab = Laboratory.query.get_or_404(lab_id)
    
    # MUDANÇA: .all() em vez de .first() para pegar TODOS os professores
    profs = lab.users.filter_by(role='professor').all()
    
    students = lab.users.filter_by(role='bolsista', is_active=True).all()
    projects = lab.projects.order_by(Project.created_at.desc()).all()
    
    total_logs = LogEntry.query.join(User).filter(User.laboratory_id == lab.id).count()
    
    # Lógica de Skills (igual anterior)
    from collections import Counter
    all_skills = []
    for s in students:
        if s.skills:
            s_list = [x.strip() for x in s.skills.split(',')]
            all_skills.extend(s_list)
    top_skills = Counter(all_skills).most_common(10)
    
    # Lógica de Atividade Recente
    recent_activity = LogEntry.query.join(User).filter(User.laboratory_id == lab.id).order_by(LogEntry.entry_date.desc()).limit(6).all()

    return render_template('lab_public.html', 
                           title=f"{lab.acronym}",
                           lab=lab,
                           profs=profs, # Passa a lista
                           students=students,
                           projects=projects,
                           total_logs=total_logs,
                           top_skills=top_skills,
                           recent_activity=recent_activity)