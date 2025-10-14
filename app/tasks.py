import google.generativeai as genai
import markdown
from datetime import date, timedelta
from app import create_app
from app.models import User, LogEntry
from app.email import send_email

def send_weekly_report_job():
    """
    A tarefa que será executada semanalmente. Agora cria o seu
    próprio contexto de aplicação de forma segura.
    """
    # Criamos uma instância da app SEM iniciar o agendador
    app = create_app(start_scheduler=False)
    
    # Usamos essa instância para criar o contexto
    with app.app_context():
        print("Executando a tarefa agendada: Envio do relatório semanal...")

        professors = User.query.filter_by(role='professor', is_active=True).all()
        recipients = [p.email for p in professors]

        if not recipients:
            print("Nenhum professor ativo encontrado. A tarefa será encerrada.")
            return

        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        
        logs_current_week = LogEntry.query.join(User).filter(
            User.role == 'bolsista', User.is_active == True,
            LogEntry.entry_date >= start_of_week, LogEntry.entry_date <= today
        ).order_by(User.username, LogEntry.entry_date).all()

        if not logs_current_week:
            print(f"Nenhum registo encontrado na semana ({start_of_week.strftime('%d/%m')} a {today.strftime('%d/%m')}). Nenhum e-mail será enviado.")
            return
            
        formatted_logs = ""
        for log in logs_current_week:
            formatted_logs += f"Data: {log.entry_date.strftime('%d/%m/%Y')}\nBolsista: {log.author.username}\nProjeto: {log.project}\nTarefas Realizadas: {log.tasks_completed}\n"
            if log.observations: formatted_logs += f"Observações: {log.observations}\n"
            formatted_logs += f"Próximos Passos: {log.next_steps}\n---\n"

        master_prompt = f"""
        Objetivo: Atue como um analisador de dados. Analise os registos de diário de bordo fornecidos e produza um relatório em formato Markdown.

        Instruções Estritas:
        1. Baseie a sua análise EXCLUSIVAMENTE nos dados fornecidos.
        2. NÃO inclua saudações, introduções ou conclusões.
        3. Use o seguinte formato Markdown:
        # Análise Semanal de Atividades
        ## Resumo Geral
        (Parágrafo conciso sobre o progresso.)
        ## Principais Avanços
        - (Tópicos com as conquistas.)
        ## Gargalos e Pontos de Atenção
        - (Tópicos com os problemas.)
        ## Sugestões para Reunião Semanal
        - (Tópicos para discussão.)

        Dados Brutos para Análise:
        ---
        {formatted_logs}
        """

        try:
            api_key = app.config['GEMINI_API_KEY']
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(master_prompt)
            report_html = markdown.markdown(response.text)
        except Exception as e:
            print(f"Erro ao comunicar com a IA: {e}")
            return
        
        subject = f"Logbook: Análise Semanal ({start_of_week.strftime('%d/%m')} a {today.strftime('%d/%m')})"
        
        send_email(subject,
                   sender=app.config['MAIL_USERNAME'],
                   recipients=recipients,
                   text_body="O seu relatório semanal de atividades está em anexo.",
                   html_body=report_html)
        
        print(f"Relatório semanal enviado com sucesso para: {', '.join(recipients)}")

