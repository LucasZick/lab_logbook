# Sistema de Gestão de Laboratórios (Logbook Multi-Tenant)

Plataforma SaaS institucional desenvolvida para a gestão integrada de múltiplos laboratórios de pesquisa e inovação.  
O sistema centraliza diários de bordo, gestão de projetos, portfólios públicos e relatórios automatizados com Inteligência Artificial, permitindo que universidades e centros de pesquisa acompanhem o progresso de centenas de bolsistas de forma organizada e visual.

---

## 🚀 Funcionalidades Principais

### 🏢 Arquitetura & Gestão

- **Multi-Tenant:** Suporte para múltiplos laboratórios isolados no mesmo sistema  
  *(Ex: Robótica, Química, Redes)* — cada um com seus dados, logos e configurações.

### 👥 Hierarquia de Acesso

- **Super Admin:** Visão global da instituição, criação e gestão de laboratórios.  
- **Professor (Coordenador):** Gestão completa do laboratório, equipa e projetos.  
- **Bolsista (Pesquisador):** Registo de atividades e gestão do próprio perfil.

### 🎨 Identidade Institucional

Cada laboratório possui sua própria **Página Pública**, contendo:

- Capa personalizada  
- Logo  
- Afiliação (ex: UDESC, CNPq)  
- Endereço  
- Redes sociais  

---

## 🧪 Operacional & Diário de Bordo

- **Logs Diários:** Registo rápido de atividades com data, tarefas, observações e próximos passos.  
- **Timeline Interativa:** Visualização cronológica com filtros por mês e ano.  
- **Edição Segura:** Bolsistas podem editar logs recentes (até 7 dias).  
- **Busca Global:** Motor avançado para localizar termos técnicos, projetos ou atividades.

---

## 📂 Projetos & Portfólio

- **Galeria de Projetos:** Vitrine visual com capas, descrições e estatísticas.  
- **Tags Personalizadas:** Áreas de atuação definidas por cada laboratório.  
- **QR Codes Automáticos:** Etiquetas para robôs/equipamentos levando à página do projeto.

---

## 🤖 Inteligência & Automação

- **Relatórios com IA (Gemini):** Geração automática de resumo semanal por e-mail.  
- **Documentação Oficial:** Relatórios PDF A4 prontos para impressão e assinatura.

---

## 🎮 Engajamento & Visual

- **Gamificação (RPG):** Sistema de XP baseado na consistência dos registros.  
- **Modo TV (Kiosk):** Interface cinematográfica para monitores do laboratório.  
- **Crachá Digital:** Criação automática de crachás prontos para imprimir.

---

## 🛠️ Tecnologias Utilizadas

### Backend
- Python, Flask, SQLAlchemy, Flask-Login, Flask-Mail

### Banco de Dados
- PostgreSQL (Produção)  
- SQLite (Desenvolvimento)

### Frontend
- HTML5, CSS3 (Bootstrap 5 Custom), JavaScript (Chart.js, Vis.js)

### IA
- Google Gemini API

### Utilitários
- Qrcode, Pillow, WeasyPrint

### Infra
- Docker, Docker Compose, Gunicorn, Nginx

---

## ⚙️ Configuração e Instalação

### Pré-requisitos
- Python 3.9+  
- Docker (opcional para dev, **obrigatório** para produção)

### Clonar o Repositório
```
git clone <url_do_repo>
cd logbook_app
```

### Variáveis de Ambiente

Crie o arquivo `.env`:

```
SECRET_KEY=chave
DATABASE_URL=postgresql://user:pass@db:5432/logbook
GEMINI_API_KEY=chave
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=email@gmail.com
MAIL_PASSWORD=senha
ADMIN_EMAIL=email_admin@gmail.com
```

### Executar com Docker
```
docker-compose up -d --build
```

### Inicializar Banco de Dados
```
docker-compose exec web python populate_db.py
```

### Criar Super Admin
```
docker-compose exec web flask create-super-admin admin@udesc.br senha123
```

---

## 📖 Guia de Uso Rápido

### Super Admin
1. Acesse `/login`.  
2. Crie e configure laboratórios.

### Professor
1. Ative a conta via link enviado por e-mail.  
2. Configure o laboratório (logo, capa, redes).  
3. Convide a equipa.

### Bolsista
1. Registe-se em `/register`.  
2. Aguarde aprovação.  
3. Registe atividades no painel.

---

## 📄 Estrutura do Projeto

```
/app
├── commands.py      # Comandos CLI
├── email.py         # Envio de e-mails
├── forms.py         # Formulários
├── models.py        # Modelos
├── routes.py        # Rotas e controladores
├── tasks.py         # Tarefas agendadas (IA)
├── templates/       # HTML Jinja2
│   ├── email/       # Templates de e-mail
│   └── ...
└── static/
    ├── lab_logos/   # Logos
    └── profile_pics/# Avatares e capas
```

---

## 🏁 Licença
Projeto interno institucional.  
Uso externo deve ser autorizado pela coordenação.