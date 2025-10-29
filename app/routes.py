import itertools
import google.generativeai as genai
from datetime import date, timedelta
import calendar
from flask import current_app, render_template, flash, redirect, url_for, request, Blueprint, abort
from sqlalchemy import or_
from app import db
from app.forms import LoginForm, RegistrationForm, LogEntryForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, LogEntry
from urllib.parse import urlparse
from sqlalchemy.exc import IntegrityError
from functools import wraps
import markdown

bp = Blueprint('main', __name__)

def professor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'professor':
            abort(403) # Erro de Acesso Proibido
        return f(*args, **kwargs)
    return decorated_function

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
            observations=form.observations.data, # Campo atualizado
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

    target_year = request.args.get('ano', type=int)
    target_month = request.args.get('mes', type=int)

    all_logs = current_user.logs.order_by(LogEntry.entry_date.desc()).all()
    
    meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

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
    return render_template('index.html', title='Página Inicial', form=form, logs_to_display=display_logs, available_months=available_months, current_month_name=current_month_name)


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

# --- PAINEL DO PROFESSOR ATUALIZADO ---
@bp.route('/dashboard')
@login_required
@professor_required
def dashboard():
    pending_users = User.query.filter_by(is_approved=False).all()
    active_bolsistas = User.query.filter_by(role='bolsista', is_approved=True, is_active=True).order_by(User.username).all()
    inactive_bolsistas = User.query.filter_by(role='bolsista', is_approved=True, is_active=False).order_by(User.username).all()
    
    today = date.today()
    today_date_str = today.strftime('%Y-%m-%d') 
    current_month_str = today.strftime('%Y-%m')
    
    return render_template('dashboard.html', title='Painel do Professor', 
                           pending_users=pending_users, 
                           active_bolsistas=active_bolsistas, 
                           inactive_bolsistas=inactive_bolsistas,
                           today_date=today_date_str,
                           current_month=current_month_str) # Variável adicionada

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

    # 1. Identifica o tipo de relatório solicitado
    report_type = request.args.get('report_type', 'week') # Padrão é semanal

    start_period = None
    end_period = None
    period_description = ""
    report_title = ""

    meses = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}

    try:
        if report_type == 'month':
            # --- LÓGICA PARA RELATÓRIO MENSAL ---
            selected_month_str = request.args.get('selected_month') # Formato YYYY-MM
            if not selected_month_str:
                flash('Mês não selecionado para o relatório mensal.', 'warning')
                return redirect(url_for('main.dashboard'))
            
            year, month = map(int, selected_month_str.split('-'))
            start_period = date(year, month, 1)
            _, last_day = calendar.monthrange(year, month)
            end_period = date(year, month, last_day)
            
            month_name = meses[month]
            period_description = f"o mês de {month_name} de {year}"
            report_title = f"Análise Mensal: {month_name} de {year}"

        else: # Assume report_type == 'week'
            # --- LÓGICA PARA RELATÓRIO SEMANAL ---
            selected_date_str = request.args.get('selected_date')
            if selected_date_str:
                selected_date = date.fromisoformat(selected_date_str)
            else:
                selected_date = date.today() # Usa hoje se nada for selecionado

            # Calcula início (Segunda) e fim (Domingo) da semana
            start_period = selected_date - timedelta(days=selected_date.weekday())
            end_period = start_period + timedelta(days=6)
            
            period_description = f"a semana de {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"
            report_title = f"Análise Semanal: {start_period.strftime('%d/%m/%Y')} a {end_period.strftime('%d/%m/%Y')}"

    except ValueError:
        flash('Data ou mês inválido selecionado.', 'warning')
        return redirect(url_for('main.dashboard'))

    # 2. Busca os logs para o período calculado
    logs_period = LogEntry.query.join(User).filter(
        User.role == 'bolsista',
        User.is_active == True,
        LogEntry.entry_date >= start_period,
        LogEntry.entry_date <= end_period
    ).order_by(User.username, LogEntry.entry_date).all()

    if not logs_period:
        flash(f"Não há registos n{period_description} para gerar uma análise.", 'info')
        return redirect(url_for('main.dashboard'))

    # 3. Formata os dados (igual para ambos os tipos)
    formatted_logs = ""
    for log in logs_period:
        formatted_logs += f"Data: {log.entry_date.strftime('%d/%m/%Y')}\nBolsista: {log.author.username}\nProjeto: {log.project}\nTarefas Realizadas: {log.tasks_completed}\n"
        if log.observations: formatted_logs += f"Observações: {log.observations}\n"
        formatted_logs += f"Próximos Passos: {log.next_steps}\n---\n"

    # 4. Seleciona e formata o Prompt Mestre
    if report_type == 'month':
        prompt_analysis_type = "mensal"
        prompt_focus = "tendências, progressos gerais e problemas recorrentes ao longo do mês"
        prompt_suggestions_focus = "estratégicos ou de longo prazo"
    else:
        prompt_analysis_type = "semanal"
        prompt_focus = "progresso geral, ritmo de trabalho e projetos em foco na semana"
        prompt_suggestions_focus = "imediatos ou para a próxima reunião"

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
        model = genai.GenerativeModel('gemini-pro')
        # Aumentar o tempo limite pode ser útil para relatórios mensais mais longos
        response = model.generate_content(master_prompt, request_options={'timeout': 120}) # Timeout de 2 minutos
        report_text = response.text
        report_html = markdown.markdown(report_text)
    except Exception as e:
        # Imprime o erro no log do servidor para depuração
        print(f"Erro detalhado da API do Gemini: {e}") 
        flash(f'Ocorreu um erro ao comunicar com a IA. Verifique os logs do servidor para detalhes.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('report_view.html',
                           title=report_title,
                           report_html=report_html,
                           start_date=start_period,
                           end_date=end_period)