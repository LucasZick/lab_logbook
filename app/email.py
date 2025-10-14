from flask_mail import Message
from app import mail
from flask import current_app

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