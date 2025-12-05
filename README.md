# Diário de Bordo para Laboratórios (Logbook App)

![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

Aplicação web desenvolvida para a gestão de atividades diárias em laboratórios de pesquisa, com um foco especial em ambientes de robótica. O sistema permite que bolsistas registem o seu progresso diário e que professores supervisionem, aprovem contas e analisem o trabalho da equipe de forma centralizada e eficiente.

## ✨ Funcionalidades Principais

- **Sistema de Papéis:** Distinção entre **Professores** (administradores) e **Bolsistas** (utilizadores padrão).
- **Gestão de Utilizadores:** Fluxo completo de registro, com aprovação/rejeição de novas contas por professores.
- **Contas Ativas/Inativas:** Professores podem ativar e desativar contas de bolsistas conforme a necessidade.
- **Registro Diário:** Formulário simples e validado para que os bolsistas insiram as suas atividades.
- **Painel do Professor:** Uma visão centralizada para gerir utilizadores e acessar aos relatórios.
- **Visualização de Diários:** Interface de linha do tempo para que os professores analisem os registros de cada bolsista de forma limpa e cronológica.
- **Grade de Atividades (Calendário):** Uma visão geral do mês que mostra quais bolsistas fizeram os seus registros em cada dia, destacando os fins de semana.
- **Busca Global:** Ferramenta de pesquisa poderosa para que professores encontrem informações em todos os registros de todos os bolsistas.
- **Relatórios com IA:** Geração automática de relatórios semanais que resumem o progresso, identificam gargalos e sugerem tópicos para reuniões, utilizando a API do Google Gemini.
- **Envio Automático de E-mails:** O relatório semanal é enviado automaticamente por e-mail para todos os professores no final da semana.

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python com Flask
- **Base de Dados:** SQLAlchemy e Flask-Migrate (desenvolvido com SQLite, configurado para PostgreSQL em produção)
- **Frontend:** HTML, CSS, Bootstrap 5
- **Inteligência Artificial:** Google Gemini API
- **Implantação (Deployment):** Docker, Docker Compose, Gunicorn, Nginx

## 🚀 Como Executar (Ambiente de Desenvolvimento)

**Pré-requisitos:** Python 3.9 ou superior.

1.  **Clone o repositório:**
    ```bash
    git clone <url_do_seu_repositorio>
    cd logbook_app
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    python3.9 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    - Crie uma cópia do ficheiro `.env.example` (se o tiver) ou crie um novo ficheiro chamado `.env`.
    - Preencha as seguintes variáveis:
      ```
      SECRET_KEY='uma_chave_super_secreta'
      GEMINI_API_KEY='sua_chave_da_api_do_gemini'
      MAIL_USERNAME='seu_email@gmail.com'
      MAIL_PASSWORD='sua_senha_de_app_do_gmail'
      ```
      *Nota: Para o desenvolvimento local, o `DATABASE_URL` não é necessário se estiver a usar o `app.db` (SQLite).*

5.  **Crie e atualize a base de dados:**
    ```bash
    flask db upgrade
    ```

6.  **Inicie a aplicação:**
    ```bash
    flask run
    ```

## 📋 Utilização

1.  **Crie o primeiro utilizador professor:**
    ```bash
    flask create-professor <username> <email> <password>
    ```
2.  Acesse `http://127.0.0.1:5000` e faça login com a conta de professor.
3.  Peça aos bolsistas para se registrarem. As solicitações aparecerão no seu painel para aprovação.

## 🐳 Implantação com Docker

Este projeto está configurado para uma implantação fácil e robusta com Docker. Após clonar o projeto no seu servidor e configurar o ficheiro `.env` com os dados de produção (incluindo o `DATABASE_URL` para PostgreSQL), basta executar:

```bash
docker-compose up -d --build