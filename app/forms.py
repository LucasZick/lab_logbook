from flask_wtf import FlaskForm
# Adicionado FileField e FileAllowed
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from datetime import date
from app.models import User

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
    submit = SubmitField('Registrar')
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None: raise ValidationError('Este nome de usuário já está em uso.')
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None: raise ValidationError('Este e-mail já está em uso.')

class LogEntryForm(FlaskForm):
    entry_date = DateField('Data do Registro', format='%Y-%m-%d', validators=[DataRequired(message='Você precisa selecionar uma data.')], default=date.today)
    project = StringField('Projeto ou Robô', validators=[DataRequired(message='O campo de projeto é obrigatório.'), Length(max=140)])
    tasks_completed = TextAreaField('Tarefas Realizadas', validators=[DataRequired(message='Você precisa descrever as tarefas realizadas.')], render_kw={"placeholder": "O que foi feito hoje? (Use tópicos)", "rows": 5})
    observations = TextAreaField('Observações (Resultados, Dificuldades, Ideias)', render_kw={"placeholder": "(Opcional) Algum resultado importante? Algum problema? Uma nova ideia?", "rows": 4})
    next_steps = TextAreaField('Próximos Passos', validators=[DataRequired(message='Você precisa planejar os próximos passos.')], render_kw={"placeholder": "Qual o plano para amanhã?", "rows": 3})
    submit = SubmitField('Salvar Registro')
    def validate_entry_date(self, field):
        if field.data > date.today(): raise ValidationError('Não é permitido criar registros para datas futuras.')

# --- NOVO FORMULÁRIO DE PERFIL COMPLETO ---
class EditProfileForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired()])
    picture = FileField('Atualizar Foto de Perfil', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Apenas imagens jpg e png são permitidas!')])
    
    course = StringField('Curso / Graduação', render_kw={"placeholder": "Ex: Eng. Mecânica - 5º Semestre"})
    bio = TextAreaField('Sobre Mim', render_kw={"rows": 3, "placeholder": "Breve descrição dos seus interesses..."})
    skills = StringField('Habilidades', render_kw={"placeholder": "Digite e pressione Enter (ex: Python, ROS, Soldagem)"})
    lattes_link = StringField('Link do Lattes')
    linkedin_link = StringField('Link do LinkedIn')
    github_link = StringField('Link do GitHub')
    
    submit = SubmitField('Atualizar Perfil')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Este nome de usuário já está em uso.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Senha Atual', validators=[DataRequired(message="Digite sua senha atual.")])
    new_password = PasswordField('Nova Senha', validators=[DataRequired(message="Digite a nova senha.")])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[DataRequired(), EqualTo('new_password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Alterar Senha')