# auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from models import db, User
from forms import RegistrationForm, LoginForm
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Создаем Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Создаем нового пользователя
            user = User(
                username=form.username.data.strip(),
                email=form.email.data.lower().strip()
            )
            user.set_password(form.password.data)
            
            # Сохраняем в БД
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Новый пользователь зарегистрирован: {user.email}")
            
            flash('🎉 Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка регистрации: {e}")
            flash('❌ Произошла ошибка при регистрации. Попробуйте еще раз.', 'danger')
    
    return render_template('register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    
    # Если пользователь уже авторизован, перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        # Ищем пользователя по email
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        
        # Проверяем пароль
        if user and user.check_password(form.password.data):
            # Авторизуем пользователя
            login_user(user, remember=form.remember_me.data)
            
            # Обновляем время последнего входа
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Пользователь вошел: {user.email}")
            
            flash(f'👋 Добро пожаловать, {user.username}!', 'success')
            
            # Перенаправляем на страницу, с которой пришел пользователь (или на dashboard)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('❌ Неверный email или пароль. Попробуйте еще раз.', 'danger')
            logger.warning(f"Неудачная попытка входа: {form.email.data}")
    
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    if current_user.is_authenticated:
        logger.info(f"Пользователь вышел: {current_user.email}")
        logout_user()
        flash('👋 Вы успешно вышли из системы.', 'info')
    
    return redirect(url_for('index'))
