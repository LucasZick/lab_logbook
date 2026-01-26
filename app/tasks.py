from flask import render_template
import google.generativeai as genai
import markdown
from datetime import date, timedelta
from app import create_app
from app.models import User, LogEntry, Laboratory
from app.email import send_email

def send_weekly_report_job(test_mode=False, force_email=None, target_lab_id=None):
    """
    Gera e envia relatórios semanais.
    :param target_lab_id: Se informado, processa APENAS este laboratório.
    """
    app = create_app(start_scheduler=False)
    
    with app.app_context():
        print(f"--- Job Iniciado ({'TESTE' if test_mode else 'PROD'}) ---")
        
        # FILTRAGEM INTELIGENTE
        if target_lab_id:
            labs = Laboratory.query.filter_by(id=target_lab_id).all()
            print(f"   -> Foco no Lab ID: {target_lab_id}")
        else:
            labs = Laboratory.query.all()
        
        today = date.today()
        
        if test_mode:
            # MODO TESTE: Pega a semana passada (hoje - 7 dias)
            # Isso garante que haja dados se testar numa segunda-feira
            target_date = today - timedelta(days=7)
            start_of_week = target_date - timedelta(days=target_date.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            print(f"   -> Data de Referência (Teste): {start_of_week} a {end_of_week}")
        else:
            # MODO NORMAL: Pega a semana atual
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = today # Até hoje
        
        period_str = f"{start_of_week.strftime('%d/%m')} a {end_of_week.strftime('%d/%m')}"

        for lab in labs:
            print(f"> Processando Laboratório: {lab.name} ({lab.acronym})...")

            # 1. Definir Destinatários
            if test_mode and force_email:
                recipients = [force_email]
                print(f"   [TESTE] Redirecionando email para: {force_email}")
            else:
                professors = lab.users.filter_by(role='professor', is_active=True).all()
                recipients = [p.email for p in professors]

            if not recipients:
                print(f"  x Sem destinatários para {lab.acronym}. Pulando.")
                continue

            # 2. Busca Logs (Semana Passada se for teste, Atual se for produção)
            logs_current_week = LogEntry.query.join(User).filter(
                User.laboratory_id == lab.id,
                User.role == 'bolsista', 
                User.is_active == True,
                LogEntry.entry_date >= start_of_week, 
                LogEntry.entry_date <= end_of_week
            ).order_by(User.username, LogEntry.entry_date).all()

            if not logs_current_week:
                print(f"  x Sem registros no {lab.acronym} no período.")
                continue
            
            # 3. Montagem dos Dados
            formatted_logs = ""
            for log in logs_current_week:
                formatted_logs += f"""
                BOLSISTA: {log.author.username} ({log.author.course or 'N/D'})
                PROJETO: {log.project}
                DATA: {log.entry_date.strftime('%d/%m/%Y')}
                FEITO: {log.tasks_completed}
                OBS: {log.observations if log.observations else '-'}
                PRÓXIMOS: {log.next_steps}
                --------------------------------------------------
                """

            # 4. Prompt IA
            lab_context = f"Lab: {lab.name} ({lab.acronym}). Descrição: {lab.description or 'P&D'}."
            
            master_prompt = f"""
            Atue como Gestor de Laboratório.
            CONTEXTO: {lab_context}
            PERÍODO: {period_str}

            DADOS DOS BOLSISTAS:
            {formatted_logs}

            OBJETIVO:
            Crie um resumo executivo curto e direto em Markdown.
            1. Panorama Geral.
            2. Destaques Individuais.
            3. Bloqueios/Problemas.
            4. Sugestões Práticas.

            Não retorne saudações e nenhum texto externo ao resumo como "com certeza, aqui está um resumo...". Retorne estritamente o que vai para o resumo.
            """

            try:
                api_key = app.config['GEMINI_API_KEY']
                if not api_key:
                    print("  x Erro: API Key não configurada.")
                    continue

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-pro')
                response = model.generate_content(master_prompt)
                report_html = markdown.markdown(response.text)
                
                # 5. Envio
                prefix = "[TESTE] " if test_mode else ""
                subject = f"{prefix}[{lab.acronym}] Relatório Semanal IA - {period_str}"
                
                final_email_html = render_template('email/weekly_report_email.html', 
                                                   report_content=report_html, 
                                                   period=period_str,
                                                   lab_name=lab.name)
                
                # --- A CORREÇÃO ESTÁ AQUI ---
                # Pegamos o sender oficial (Tupla: 'Logbook Lab', 'suporte@...')
                sender_oficial = app.config.get('MAIL_DEFAULT_SENDER') 
                
                # Fallback de segurança caso a config falhe
                if not sender_oficial:
                    sender_oficial = ('Logbook Lab', 'suporte@logbook-lab.com.br')

                send_email(subject,
                           sender=sender_oficial,  # <--- MUDOU DE MAIL_USERNAME PARA ISSO
                           recipients=recipients,
                           text_body="Relatório disponível em HTML.",
                           html_body=final_email_html)
                
                print(f"  v Sucesso! Enviado para {recipients}")

            except Exception as e:
                print(f"  x Erro ao processar {lab.acronym}: {e}")
                continue

        print("--- Job Finalizado ---")