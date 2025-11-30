from flask_wtf import FlaskForm
# Adicionado FileField e FileAllowed
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, StringField, PasswordField, BooleanField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from datetime import date
from app.models import Project, User

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(message='Este campo é obrigatório.')])
    password = PasswordField('Senha', validators=[DataRequired(message='Este campo é obrigatório.')])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(message='Este campo é obrigatório.')])
    email = StringField('Email', validators=[DataRequired(message='Este campo é obrigatório.'), Email(message='Email inválido.')])
    password = PasswordField('Senha', validators=[DataRequired(message='Este campo é obrigatório.')])
    password2 = PasswordField('Repita a Senha', validators=[DataRequired(message='Este campo é obrigatório.'), EqualTo('password', message='As senhas devem ser iguais.')])
    lab_select = SelectField('Laboratório', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Registrar')
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None: raise ValidationError('Este nome de usuário já está em uso.')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None: raise ValidationError('Este e-mail já está em uso.')

class LogEntryForm(FlaskForm):
    entry_date = DateField('Data do Registro', format='%Y-%m-%d', validators=[DataRequired()], default=date.today)
    
    # MUDANÇA AQUI: Removemos o validator=[DataRequired()]
    # O coerce=int garante que recebemos um número (0 ou ID)
    project_select = SelectField('Projeto', coerce=int)
    
    tasks_completed = TextAreaField('Tarefas Realizadas', validators=[DataRequired()], render_kw={"rows": 5})
    observations = TextAreaField('Observações', render_kw={"rows": 4})
    next_steps = TextAreaField('Próximos Passos', validators=[DataRequired()], render_kw={"rows": 3})
    submit = SubmitField('Salvar Registro')
    
    def validate_entry_date(self, field):
        if field.data > date.today(): raise ValidationError('Não é permitido criar registros para datas futuras.')

# --- NOVO FORMULÁRIO DE PERFIL COMPLETO ---
class EditProfileForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired()])
    
    # --- ALTERAÇÃO AQUI ---
    email = StringField('E-mail', validators=[DataRequired(), Email(message='Email inválido.')])
    # Novo campo que obriga a ser igual ao 'email'
    confirm_email = StringField('Confirmar E-mail', validators=[EqualTo('email', message='Os e-mails não coincidem.')])
    # ----------------------

    picture = FileField('Atualizar Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens jpg e png são permitidas!')])
    cover = FileField('Imagem de Capa', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    course = StringField('Curso / Graduação', render_kw={"placeholder": "Ex: Eng. Mecânica - 5º Semestre"})
    bio = TextAreaField('Sobre Mim', render_kw={"rows": 3, "placeholder": "Breve descrição dos seus interesses..."})
    lattes_link = StringField('Link do Lattes')
    linkedin_link = StringField('Link do LinkedIn')
    github_link = StringField('Link do GitHub')
    skills = StringField('Habilidades')
    
    submit = SubmitField('Atualizar Perfil')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None:
                raise ValidationError('Este e-mail já está em uso por outro bolsista.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Senha Atual', validators=[DataRequired(message="Digite sua senha atual.")])
    new_password = PasswordField('Nova Senha', validators=[DataRequired(message="Digite a nova senha.")])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[DataRequired(), EqualTo('new_password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Alterar Senha')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Link de Recuperação')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Definir Nova Senha')

class ProjectForm(FlaskForm):
    name = StringField('Nome do Projeto', validators=[DataRequired(), Length(max=100)])
    
    # Seletor de Categoria (Mantido)
    category = SelectField('Categoria Principal', choices=[
        ('Geral', 'Geral / Outros'),
        ('Robotica', 'Robótica Móvel & Manipuladores'),
        ('IA', 'Inteligência Artificial & Visão'),
        ('Embedded', 'Sistemas Embarcados & IoT'),
        ('3D', 'Impressão 3D & Prototipagem'),
        ('Software', 'Software & Interfaces'),
        ('Eletronica', 'Eletrónica & Circuitos')
    ], validators=[DataRequired()])

    description = TextAreaField('Descrição', validators=[Length(max=500)], render_kw={"rows": 3})
    image = FileField('Imagem do Projeto', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    submit = SubmitField('Salvar Projeto')

    # --- LÓGICA DE VALIDAÇÃO INTELIGENTE ---
    def __init__(self, original_name=None, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, name):
        # Só verifica no banco se o nome for DIFERENTE do original
        if name.data != self.original_name:
            project = Project.query.filter_by(name=name.data).first()
            if project:
                raise ValidationError('Já existe um projeto com esse nome.')

class LabForm(FlaskForm):
    name = StringField('Nome do Laboratório', validators=[DataRequired()])
    acronym = StringField('Sigla (Ex: LAR)', validators=[DataRequired()])
    
    prof_name = StringField('Usuário de Acesso (Login)', validators=[DataRequired()], render_kw={"placeholder": "ex: joao_silva"})
    prof_email = StringField('E-mail do Professor', validators=[DataRequired(), Email()])
    submit = SubmitField('Criar Laboratório')

class EditLabForm(FlaskForm):
    name = StringField('Nome do Laboratório', validators=[DataRequired()])
    acronym = StringField('Sigla (Ex: LAR)', validators=[DataRequired()])
    description = TextAreaField('Descrição / Missão', render_kw={"rows": 3})
    logo = FileField('Logótipo do Laboratório', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens!')])
    submit = SubmitField('Salvar Configurações')

class ActivateAccountForm(FlaskForm):
    username = StringField('Escolha seu Usuário', validators=[DataRequired()])
    password = PasswordField('Crie sua Senha', validators=[DataRequired()])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Ativar Minha Conta')

    def validate_username(self, username):
        # Verifica se o nome já existe (excluindo o próprio usuário temporário)
        user = User.query.filter_by(username=username.data).first()
        if user:
            # Aqui precisamos de um truque: como saber se é o próprio usuário?
            # Na rota vamos tratar o erro de duplicidade se for outro ID
            pass