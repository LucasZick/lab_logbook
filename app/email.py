from flask_mail import Message
from app import mail
from flask import current_app, render_template

def send_email(subject, sender, recipients, text_body, html_body):
    """
    Função auxiliar para enviar e-mails.
    """
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)

    print(sender)

    print(recipients)

def send_password_reset_email(user):
    token = user.get_reset_token()
    send_email('[Logbook] Recuperação de Senha',
               sender=current_app.config['MAIL_USERNAME'],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt',
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))