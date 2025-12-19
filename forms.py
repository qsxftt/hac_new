from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    """Форма регистрации нового пользователя"""
    
    username = StringField(
        'Имя',
        validators=[
            DataRequired(message='Введите ваше имя'),
            Length(min=2, max=80, message='Имя должно быть от 2 до 80 символов')
        ],
        render_kw={'placeholder': 'Например: Иван Иванов'}
    )
    
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Введите email'),
            Email(message='Введите корректный email')
        ],
        render_kw={'placeholder': 'example@mail.com'}
    )
    
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Введите пароль'),
            Length(min=6, message='Пароль должен быть минимум 6 символов')
        ],
        render_kw={'placeholder': 'Минимум 6 символов'}
    )
    
    confirm_password = PasswordField(
        'Подтвердите пароль',
        validators=[
            DataRequired(message='Подтвердите пароль'),
            EqualTo('password', message='Пароли должны совпадать')
        ],
        render_kw={'placeholder': 'Повторите пароль'}
    )
    
    submit = SubmitField('Зарегистрироваться')
    
    def validate_email(self, email):
        """Check that email is not already registered"""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('This email is already registered. Please login or use a different email.')


class LoginForm(FlaskForm):
    """Форма входа в систему"""
    
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Введите email'),
            Email(message='Введите корректный email')
        ],
        render_kw={'placeholder': 'example@mail.com'}
    )
    
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Введите пароль')
        ],
        render_kw={'placeholder': 'Ваш пароль'}
    )
    
    remember_me = BooleanField('Запомнить меня')
    
    submit = SubmitField('Войти')
