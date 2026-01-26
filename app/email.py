from flask_mail import Message
from app import mail
from flask import current_app, render_template

def send_email(subject, sender, recipients, text_body, html_body):
    """
    Função auxiliar para enviar e-mails.
    """
    # O sender aqui receberá a tupla ('Logbook Lab', 'suporte@...') vinda da config
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    
    try:
        mail.send(msg)
        print(f"✅ Email enviado de {sender} para {recipients}")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        raise e

def send_password_reset_email(user):
    token = user.get_reset_token()
    
    # AQUI ESTAVA O ERRO: Mudamos de MAIL_USERNAME para MAIL_DEFAULT_SENDER
    # Isso pega ('Logbook Lab', 'suporte@logbook-lab.com.br')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')
    
    send_email('[Logbook] Recuperação de Senha',
               sender=sender, 
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))
    
def send_invite_email(user, lab_name):
    token = user.get_reset_token() 

    # AQUI TAMBÉM: Usar o sender padrão
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    send_email(f'[Logbook] Convite para administrar o {lab_name}',
               sender=sender,
               recipients=[user.email],
               text_body=render_template('email/invite_professor.txt',
                                         user=user, lab_name=lab_name, token=token),
               html_body=render_template('email/invite_professor.html',
                                         user=user, lab_name=lab_name, token=token))