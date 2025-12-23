#!/bin/bash

# ================= CONFIGURAÇÕES =================
# Onde seu projeto mora
PROJECT_DIR="/home/ubuntu/lab_logbook"

# Onde vamos guardar os backups
BACKUP_DIR="/home/ubuntu/backups"

# Data e Hora para o nome do arquivo (Ex: 2023-10-27_14-00)
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILENAME="backup_completo_$DATE.tar.gz"

# Quantos dias manter os arquivos? (Apaga os mais velhos que 7 dias)
RETENTION_DAYS=7
# =================================================

# 1. Cria a pasta de backup se não existir
mkdir -p $BACKUP_DIR

# 2. Entra na pasta do projeto
cd $PROJECT_DIR

echo "--- Iniciando Backup: $DATE ---"

# 3. Dump do Banco de Dados
# O comando 'exec -T' é vital para funcionar no automático (sem terminal interativo)
echo "Salvando Banco de Dados..."
docker compose exec -T db pg_dump -U logbook_user logbook > db_dump.sql

# 4. Compactar TUDO (SQL + Imagens) em um arquivo só
# Estamos salvando o SQL e a pasta 'app/static' onde ficam as fotos
echo "Compactando arquivos..."
tar -czf $BACKUP_DIR/$FILENAME db_dump.sql app/static/profile_pics app/static/lab_logos

# 5. Limpeza Temporária
# Remove o arquivo .sql solto (já está dentro do tar.gz)
rm db_dump.sql

# 6. Rotação de Backups (Limpeza de disco)
# Encontra arquivos .tar.gz modificados há mais de X dias e deleta
echo "Limpando backups antigos (+ de $RETENTION_DAYS dias)..."
find $BACKUP_DIR -type f -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 7. Verifica se deu certo
if [ -f "$BACKUP_DIR/$FILENAME" ]; then
    echo "SUCESSO: Backup criado em $BACKUP_DIR/$FILENAME"
else
    echo "ERRO: O arquivo de backup não foi criado!"
fi

echo "Enviando para o Google Drive..."
rclone copy "$BACKUP_DIR/$FILENAME" gdrive:Backups_Oracle

# (Opcional) Limpa arquivos antigos no Google Drive (mantém 30 dias)
rclone delete gdrive:Backups_Oracle --min-age 30d
# =============================================

echo "--- Fim ---"