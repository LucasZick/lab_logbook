from flask_wtf import FlaskForm
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
    password2 = PasswordField(
        'Repita a Senha', validators=[DataRequired(message='Este campo é obrigatório.'), EqualTo('password', message='As senhas devem ser iguais.')])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este e-mail já está em uso.')

class LogEntryForm(FlaskForm):
    entry_date = DateField('Data do Registro',
                           format='%Y-%m-%d',
                           validators=[DataRequired(message='Você precisa selecionar uma data.')],
                           default=date.today)

    project = StringField('Projeto ou Robô',
                          validators=[DataRequired(message='O campo de projeto é obrigatório.'), Length(max=140)])

    tasks_completed = TextAreaField('Tarefas Realizadas',
                                    validators=[DataRequired(message='Você precisa descrever as tarefas realizadas.')],
                                    render_kw={"placeholder": "O que foi feito hoje? (Use tópicos)", "rows": 5})

    observations = TextAreaField('Observações (Resultados, Dificuldades, Ideias)',
                                 render_kw={"placeholder": "(Opcional) Algum resultado importante? Algum problema? Uma nova ideia?", "rows": 4})

    next_steps = TextAreaField('Próximos Passos',
                               validators=[DataRequired(message='Você precisa planejar os próximos passos.')],
                               render_kw={"placeholder": "Qual o plano para amanhã?", "rows": 3})

    submit = SubmitField('Salvar Registro')

    def validate_entry_date(self, field):
        if field.data > date.today():
            raise ValidationError('Não é permitido criar registros para datas futuras.')