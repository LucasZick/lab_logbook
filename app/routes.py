import os
import secrets
from PIL import Image
import itertools
from datetime import date, timedelta
import calendar
from flask import render_template, flash, redirect, url_for, request, Blueprint, abort, current_app
from app import db
# Importar o novo formulário
from app.forms import ChangePasswordForm, LoginForm, RegistrationForm, LogEntryForm, EditProfileForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, LogEntry
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from functools import wraps
import google.generativeai as genai
import markdown

bp = Blueprint('main', __name__)

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'professor':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- FUNÇÃO AUXILIAR PARA SALVAR FOTO ---
def save_picture(form_picture):
    # 1. Gera nome aleatório para evitar conflitos
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    
    # 2. Define o caminho completo (pasta static/profile_pics)
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    # 3. Redimensiona a imagem para 150x150 (poupa espaço)
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # 4. Salva
    i.save(picture_path)

    return picture_fn

# --- ROTAS DE PERFIL ---

@bp.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    total_logs = user.logs.count()
    # Define a imagem. Se for default, busca a padrão, senão busca a do usuário
    image_file = url_for('static', filename='profile_pics/' + user.image_file)
    return render_template('user_profile.html', user=user, total_logs=total_logs, image_file=image_file)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        # ... (salvar imagem se houver) ...
        
        # Guardar dados
        current_user.username = form.username.data
        current_user.course = form.course.data
        current_user.bio = form.bio.data
        current_user.skills = form.skills.data # <--- ADICIONAR ESTA LINHA
        current_user.lattes_link = form.lattes_link.data
        current_user.linkedin_link = form.linkedin_link.data
        current_user.github_link = form.github_link.data
        
        db.session.commit()
        flash('O seu perfil foi atualizado!', 'success')
        return redirect(url_for('main.user_profile', username=current_user.username))
    
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.course.data = current_user.course
        form.bio.data = current_user.bio
        form.skills.data = current_user.skills # <--- ADICIONAR ESTA LINHA
        form.lattes_link.data = current_user.lattes_link
        form.linkedin_link.data = current_user.linkedin_link
        form.github_link.data = current_user.github_link
        
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('edit_profile.html', title='Editar Perfil', form=form, image_file=image_file)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if current_user.role == 'professor':
        return redirect(url_for('main.dashboard'))

    form = LogEntryForm()
    if form.validate_on_submit():
        log_entry = LogEntry(
            entry_date=form.entry_date.data,
            project=form.project.data,
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
        # Redireciona de volta para a mesma página (index)
        return redirect(url_for('main.index'))

    # --- LÓGICA DA PÁGINA (GET) ---

    # 1. LÓGICA DO "REGISTO DE HOJE"
    today = date.today()
    has_log_today = LogEntry.query.filter_by(
        author=current_user,
        entry_date=today
    ).first() is not None

    # 2. LÓGICA DO CALENDÁRIO E HISTÓRICO (UNIFICADA)
    # A página inteira (calendário e histórico) será controlada por estes parâmetros
    year = request.args.get('ano', default=today.year, type=int)
    month = request.args.get('mes', default=today.month, type=int)

    # 3. Calcula as datas para os botões de navegação
    current_date = date(year, month, 1)
    prev_month_date = current_date - timedelta(days=1)
    next_month_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    
    # 4. Busca os registos do utilizador para o mês/ano selecionado
    _, num_days_in_month = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days_in_month)
    
    # Busca os logs UMA SÓ VEZ
    logs_in_month = LogEntry.query.filter_by(author=current_user).filter(
        LogEntry.entry_date >= start_date,
        LogEntry.entry_date <= end_date
    ).order_by(LogEntry.entry_date.desc()).all() # Ordena descendentemente para o histórico

    # 5. Prepara os dados para a grelha do calendário
    logs_lookup = {log.entry_date.day for log in logs_in_month}
    days_status_list = []
    for day in range(1, num_days_in_month + 1):
        current_day_date = date(year, month, day)
        is_weekend_day = current_day_date.weekday() >= 5
        has_log = day in logs_lookup
        
        show_icon = True
        icon_type = 'none'
        if has_log:
            icon_type = 'check'
        elif current_day_date > today:
            show_icon = False
        elif is_weekend_day:
            show_icon = False
        else:
            icon_type = 'times'
            
        days_status_list.append({
            'day': day, 'show_icon': show_icon, 'icon_type': icon_type, 'is_weekend': is_weekend_day
        })
    
    # 6. Prepara o cabeçalho da tabela
    days_header_list = []
    for day in range(1, num_days_in_month + 1):
        is_weekend_day = date(year, month, day).weekday() >= 5
        days_header_list.append({'day': day, 'is_weekend': is_weekend_day})

    current_month_name = f"{meses[month]} de {year}"
    
    return render_template('index.html', 
                           title='Meu Painel',
                           form=form,
                           has_log_today=has_log_today,
                           days_status=days_status_list,
                           days_header=days_header_list,
                           logs_to_display=logs_in_month, # Passa os logs para o histórico
                           current_month_name=current_month_name,
                           prev_month={'ano': prev_month_date.year, 'mes': prev_month_date.month},
                           next_month={'ano': next_month_date.year, 'mes': next_month_date.month})

# --- ROTA DE LOGIN ATUALIZADA ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'professor': return redirect(url_for('main.dashboard'))
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Usuário ou senha inválidos', 'warning')
            return redirect(url_for('main.login'))
        if not user.is_approved:
            flash('Sua conta ainda não foi aprovada.', 'warning')
            return redirect(url_for('main.login'))
        # NOVA VERIFICAÇÃO: Impede login de usuários inativos
        if not user.is_active:
            flash('Sua conta está desativada. Entre em contato com um professor.', 'warning')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        if current_user.role == 'professor': return redirect(url_for('main.dashboard'))
        else:
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '': next_page = url_for('main.index')
            return redirect(next_page)
    return render_template('login.html', title='Entrar', form=form)

# --- ROTA DE APROVAÇÃO ATUALIZADA ---
@bp.route('/approve/<int:user_id>')
@login_required
@professor_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    user.is_active = True # Ativa o usuário ao aprovar
    db.session.commit()
    flash(f'O usuário {user.username} foi aprovado e ativado!', 'success')
    return redirect(url_for('main.dashboard'))

meses = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
    7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

@bp.route('/dashboard')
@login_required
@professor_required
def dashboard():
    pending_users = User.query.filter_by(is_approved=False).all()
    active_bolsistas = User.query.filter_by(role='bolsista', is_approved=True, is_active=True).order_by(User.username).all()
    inactive_bolsistas = User.query.filter_by(role='bolsista', is_approved=True, is_active=False).order_by(User.username).all()
    
    # --- DADOS PARA OS SELETORES ---
    today = date.today()
    current_year = today.year
    current_month_num = today.month
    today_date_str = today.strftime('%Y-%m-%d')
    available_years = [current_year, current_year - 1, current_year - 2, current_year - 3]
    
    return render_template('dashboard.html', title='Painel do Professor', 
                           pending_users=pending_users, 
                           active_bolsistas=active_bolsistas, 
                           inactive_bolsistas=inactive_bolsistas,
                           today_date=today_date_str, # Para o seletor de semana
                           meses=meses, # Para o seletor de mês
                           available_years=available_years, # Para o seletor de ano
                           current_year=current_year,
                           current_month_num=current_month_num)

@bp.route('/get_week_range')
@login_required
@professor_required
def get_week_range():
    """
    Calcula e retorna o intervalo de uma semana (Seg-Dom) com base numa data.
    Usado pelo JavaScript para dar feedback ao utilizador.
    """
    selected_date_str = request.args.get('date')
    if not selected_date_str:
        return jsonify({'error': 'Nenhuma data fornecida'}), 400
    
    try:
        selected_date = date.fromisoformat(selected_date_str)
        # Calcula o início (Segunda) e o fim (Domingo) da semana
        start_of_week = selected_date - timedelta(days=selected_date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Formata a string de exibição no formato DD/MM/YYYY
        display_string = f"Semana: {start_of_week.strftime('%d/%m/%Y')} a {end_of_week.strftime('%d/%m/%Y')}"
        
        return jsonify({'display': display_string})
    except ValueError:
        return jsonify({'error': 'Formato de data inválido'}), 400

# --- CALENDÁRIO ATUALIZADO ---
# Mostra apenas bolsistas ativos na grade
@bp.route('/calendar')
@login_required
@professor_required
def calendar_view():
    bolsistas = User.query.filter_by(role='bolsista', is_approved=True, is_active=True).order_by(User.username).all()
    # ... (o resto da função é o mesmo)
    year = request.args.get('ano', default=date.today().year, type=int)
    month = request.args.get('mes', default=date.today().month, type=int)
    current_date = date(year, month, 1)
    prev_month_date = current_date - timedelta(days=1)
    next_month_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    _, num_days_in_month = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days_in_month)
    logs_in_month = LogEntry.query.filter(LogEntry.entry_date >= start_date, LogEntry.entry_date <= end_date).all()
    logs_lookup = {(log.user_id, log.entry_date.day) for log in logs_in_month}
    grid_data = []
    for bolsista in bolsistas:
        days_status = []
        for day in range(1, num_days_in_month + 1):
            is_weekend_day = date(year, month, day).weekday() >= 5
            has_log = (bolsista.id, day) in logs_lookup
            days_status.append({'day': day, 'has_log': has_log, 'is_weekend': is_weekend_day})
        grid_data.append({'student': bolsista, 'days': days_status})
    days_header = []
    for day in range(1, num_days_in_month + 1):
        is_weekend_day = date(year, month, day).weekday() >= 5
        days_header.append({'day': day, 'is_weekend': is_weekend_day})
    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    current_month_name = f"{meses[month]} de {year}"
    return render_template('calendar_view.html', title="Calendário de Atividades", grid_data=grid_data, days_header=days_header, current_month_name=current_month_name, prev_month={'ano': prev_month_date.year, 'mes': prev_month_date.month}, next_month={'ano': next_month_date.year, 'mes': next_month_date.month})

# --- NOVAS ROTAS PARA ATIVAR/DESATIVAR ---
@bp.route('/deactivate/<int:user_id>')
@login_required
@professor_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'bolsista':
        user.is_active = False
        db.session.commit()
        flash(f'O bolsista {user.username} foi desativado.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/activate/<int:user_id>')
@login_required
@professor_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'bolsista':
        user.is_active = True
        db.session.commit()
        flash(f'O bolsista {user.username} foi reativado.', 'success')
    return redirect(url_for('main.dashboard'))


@bp.route('/view_logs/<int:student_id>')
@login_required
@professor_required
def view_logs(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'bolsista': abort(404)
    target_year = request.args.get('ano', type=int)
    target_month = request.args.get('mes', type=int)
    all_logs = student.logs.order_by(LogEntry.entry_date.desc()).all()
    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
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

@bp.route('/reject/<int:user_id>')
@login_required
@professor_required
def reject_user(user_id):
    user_to_reject = User.query.filter_by(id=user_id, is_approved=False).first_or_404()
    username = user_to_reject.username
    db.session.delete(user_to_reject)
    db.session.commit()
    flash(f'A solicitação do usuário {username} foi rejeitada.', 'success')
    return redirect(url_for('main.dashboard'))

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Solicitação de registro enviada! Aguarde a aprovação.', 'info')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Registrar', form=form)

# --- NOVA ROTA PARA A BUSCA GLOBAL ---
@bp.route('/search')
@login_required
@professor_required
def search():
    """
    Realiza uma busca por um termo em todos os registros de todos os bolsistas.
    """
    # Pega o termo de busca da URL (ex: /search?q=motor)
    query = request.args.get('q', '', type=str)
    results = []

    if query:
        search_term = f"%{query}%"
        # A query busca o termo em vários campos do LogEntry,
        # apenas de usuários que são 'bolsista'.
        results = LogEntry.query.join(User).filter(
            User.role == 'bolsista',
            or_(
                LogEntry.project.ilike(search_term),
                LogEntry.tasks_completed.ilike(search_term),
                LogEntry.observations.ilike(search_term),
                LogEntry.next_steps.ilike(search_term)
            )
        ).order_by(LogEntry.entry_date.desc()).all()

    return render_template('search_results.html', 
                           title=f"Resultados para '{query}'", 
                           results=results, 
                           query=query)


# --- ROTA DE GERAÇÃO DE RELATÓRIO (ATUALIZADA PARA ACEITAR DATA) ---
@bp.route('/generate_report')
@login_required
@professor_required
def generate_report():
    api_key = current_app.config['GEMINI_API_KEY']
    if not api_key:
        flash('A chave de API do Gemini não está configurada no servidor.', 'danger')
        return redirect(url_for('main.dashboard'))

    # --- LÓGICA DE DECISÃO INTELIGENTE ---
    # Verificamos quais parâmetros foram enviados para decidir o tipo de relatório
    if 'month_num' in request.args:
        report_type = 'month'
    else:
        report_type = 'week'

    start_period, end_period = None, None
    period_description, report_title = "", ""

    try:
        if report_type == 'month':
            # --- LÓGICA PARA RELATÓRIO MENSAL ---
            month_num = request.args.get('month_num', type=int)
            year = request.args.get('year', type=int)
            if not month_num or not year: raise ValueError("Mês ou Ano em falta.")

            start_period = date(year, month_num, 1)
            _, last_day = calendar.monthrange(year, month_num)
            end_period = date(year, month_num, last_day)
            month_name = meses[month_num]
            period_description = f"o mês de {month_name} de {year}"
            report_title = f"Análise Mensal: {month_name} de {year}"

        else: # report_type == 'week'
            # --- LÓGICA PARA RELATÓRIO SEMANAL ---
            selected_date_str = request.args.get('selected_date')
            selected_date = date.fromisoformat(selected_date_str) if selected_date_str else date.today()

            start_period = selected_date - timedelta(days=selected_date.weekday())
            end_period = start_period + timedelta(days=6)
            period_description = f"a semana de {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"
            report_title = f"Análise Semanal: {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"

    except Exception as e:
        flash(f'Período inválido selecionado: {e}', 'warning')
        return redirect(url_for('main.dashboard'))

    # ... (O resto da função: buscar logs, formatar, chamar IA, e renderizar o 'report_view.html'
    #      permanece exatamente o mesmo, pois já está a usar estas variáveis)
    
    logs_period = LogEntry.query.join(User).filter(
        User.role == 'bolsista',
        User.is_active == True,
        LogEntry.entry_date >= start_period,
        LogEntry.entry_date <= end_period
    ).order_by(User.username, LogEntry.entry_date).all()
    
    if not logs_period:
        flash(f"Não há registos n{period_description} para gerar uma análise.", 'info')
        return redirect(url_for('main.dashboard'))

    # ... (Formatação dos logs e prompt da IA)
    formatted_logs = ""
    for log in logs_period:
        formatted_logs += f"Data: {log.entry_date.strftime('%d/%m/%Y')}\nBolsista: {log.author.username}\nProjeto: {log.project}\nTarefas Realizadas: {log.tasks_completed}\n"
        if log.observations: formatted_logs += f"Observações: {log.observations}\n"
        formatted_logs += f"Próximos Passos: {log.next_steps}\n---\n"
    
    # Seleção do Prompt
    if report_type == 'month':
        prompt_analysis_type = "mensal"; prompt_focus = "tendências e progressos gerais"; prompt_suggestions_focus = "estratégicos"
    else:
        prompt_analysis_type = "semanal"; prompt_focus = "ritmo de trabalho e projetos em foco"; prompt_suggestions_focus = "imediatos"

    master_prompt = f"""
    Objetivo: Atue como um analisador de dados. Analise os registos de diário de bordo fornecidos para {period_description} e produza um relatório {prompt_analysis_type} em formato Markdown.

    Instruções Estritas:
    1. Baseie a sua análise EXCLUSIVAMENTE nos dados fornecidos para este período.
    2. NÃO inclua saudações, introduções ou conclusões. Comece diretamente no primeiro título.
    3. Use o seguinte formato Markdown:

    # {report_title}

    ## Resumo Geral {('do Mês' if report_type == 'month' else 'da Semana')}
    (Um parágrafo conciso sobre {prompt_focus}, baseado nos dados.)

    ## Principais Avanços
    - (Use um tópico para cada conquista ou progresso significativo extraído dos registos.)
    - (Se não houver avanços claros, indique "Nenhum avanço significativo reportado.")

    ## Gargalos e Pontos de Atenção
    - (Use um tópico para cada problema, dificuldade ou bloqueio mencionado nos registos.)
    - (Agrupe problemas semelhantes e identifique se algum parece ser recorrente.)
    - (Se não houver problemas, indique "Nenhum problema reportado.")

    ## Sugestões {('Estratégicas' if report_type == 'month' else 'para Reunião Semanal')}
    - (Sugira 2 ou 3 tópicos de discussão {prompt_suggestions_focus} baseados estritamente nos avanços e gargalos identificados.)

    Dados Brutos para Análise ({period_description}):
    ---
    {formatted_logs}
    """

    # 5. Chama a IA e renderiza o resultado
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(master_prompt, request_options={'timeout': 120})
        report_text = response.text
        report_html = markdown.markdown(report_text)
    except Exception as e:
        print(f"Erro detalhado da API do Gemini: {e}") 
        flash(f'Ocorreu um erro ao comunicar com a IA. Verifique os logs do servidor para detalhes.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('report_view.html',
                           title=report_title,
                           report_html=report_html,
                           start_date=start_period,
                           end_date=end_period)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # 1. Verifica se a senha antiga está correta
        if not current_user.check_password(form.old_password.data):
            flash('A senha atual está incorreta.', 'danger')
            return redirect(url_for('main.change_password'))
        
        # 2. Define a nova senha
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Sua senha foi alterada com sucesso!', 'success')
        return redirect(url_for('main.user_profile', username=current_user.username))
        
    return render_template('change_password.html', title='Alterar Senha', form=form)