import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# --- SUAS CONFIGURAÇÕES ---
SMTP_SERVER = 'smtp-relay.brevo.com'
SMTP_PORT = 587
SMTP_USERNAME = os.environ.get('MAIL_USERNAME')
SMTP_PASSWORD = os.environ.get('MAIL_PASSWORD')

# QUEM ENVIA E QUEM RECEBE
SENDER_EMAIL = os.environ.get('ADMIN_EMAIL')
TARGET_EMAIL = os.environ.get('ADMIN_EMAIL')
# --------------------------

try:
    print(f"--- Iniciando Teste de SMTP ---")
    print(f"1. Servidor: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"2. Usuário: {SMTP_USERNAME}")
    
    # Remove espaços invisíveis da senha (segurança contra erro de cópia)
    password_limpa = SMTP_PASSWORD.strip()
    
    # Conecta
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.set_debuglevel(1) # Mostra o log detalhado no terminal
    server.ehlo()
    
    print("3. Iniciando TLS (Criptografia)...")
    server.starttls()
    server.ehlo()
    
    print(f"4. Tentando LOGIN...")
    server.login(SMTP_USERNAME, password_limpa)
    print("   ✅ LOGIN SUCESSO! A senha está correta.")
    
    print("5. Enviando e-mail...")
    msg = MIMEMultipart()
    msg['From'] = f"Logbook Lab <{SENDER_EMAIL}>"
    msg['To'] = TARGET_EMAIL
    msg['Subject'] = "Teste Final Logbook - Funcionou!"
    msg.attach(MIMEText("Se você recebeu isso, o sistema de e-mail está 100% operacional.", 'plain'))
    
    server.sendmail(SENDER_EMAIL, TARGET_EMAIL, msg.as_string())
    server.quit()
    
    print("\n" + "="*40)
    print("🏆 SUCESSO TOTAL! VERIFIQUE SEU GMAIL.")
    print("="*40)

except smtplib.SMTPAuthenticationError as e:
    print("\n❌ ERRO DE AUTENTICAÇÃO (535):")
    print("O Brevo recusou sua senha ou o remetente.")
    print(f"Detalhe: {e}")
    print("\nDICA: Verifique se a conta no Brevo está Ativa e se criou o Sender 'suporte'.")

except Exception as e:
    print(f"\n❌ ERRO GERAL: {e}")