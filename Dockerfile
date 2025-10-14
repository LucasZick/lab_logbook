# Usa uma imagem oficial do Python como base
FROM python:3.9-slim

# Define o diretório de trabalho dentro do contentor
WORKDIR /app

# Copia o ficheiro de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências, incluindo o psycopg2-binary e o gunicorn
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install psycopg2-binary gunicorn

# Copia o resto do código da sua aplicação para dentro do contentor
COPY . .

# Expõe a porta que o Gunicorn irá usar
EXPOSE 5000

# Comando para executar a aplicação em produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]