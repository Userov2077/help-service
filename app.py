import os
import json
import hashlib
import random
import string
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = 'super-secret-key-for-session-2024'

# ========== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ==========
def get_worksheet():
    """Подключается к Google Sheets и возвращает рабочий лист"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Путь к файлу с ключами
    creds_file = 'credentials.json'
    
    if not os.path.exists(creds_file):
        raise Exception(f"Файл {creds_file} не найден! Скачай его из Google Cloud Console.")
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    
    # Открываем таблицу по ID
    sheet = client.open_by_key('1F0bIXrIkNmCPbXaahtzXvvM4igPOcFY7d_ZgTKLScbA')
    
    # Получаем или создаём лист "users"
    try:
        worksheet = sheet.worksheet('users')
    except:
        worksheet = sheet.add_worksheet(title='users', rows=1, cols=20)
        # Создаём заголовки
        headers = ['id', 'iin', 'phone', 'name', 'role', 'password_hash', 'rating', 'completed_tasks', 'bio', 'created_at']
        worksheet.append_row(headers)
    
    return worksheet

def get_tasks_worksheet():
    """Возвращает лист с задачами"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key('1F0bIXrIkNmCPbXaahtzXvvM4igPOcFY7d_ZgTKLScbA')
    
    try:
        worksheet = sheet.worksheet('tasks')
    except:
        worksheet = sheet.add_worksheet(title='tasks', rows=1, cols=12)
        headers = ['id', 'title', 'description', 'price', 'address', 'customer_id', 'executor_id', 'status', 'created_at']
        worksheet.append_row(headers)
    
    return worksheet

def get_responses_worksheet():
    """Возвращает лист с откликами"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key('1F0bIXrIkNmCPbXaahtzXvvM4igPOcFY7d_ZgTKLScbA')
    
    try:
        worksheet = sheet.worksheet('responses')
    except:
        worksheet = sheet.add_worksheet(title='responses', rows=1, cols=6)
        headers = ['id', 'task_id', 'executor_id', 'message', 'status', 'created_at']
        worksheet.append_row(headers)
    
    return worksheet

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_next_id(worksheet):
    """Получает следующий ID для новой записи"""
    records = worksheet.get_all_records()
    if len(records) == 0:
        return 1
    return max([r.get('id', 0) for r in records]) + 1

def get_user_by_iin(iin):
    """Находит пользователя по ИИН"""
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    for record in records:
        if str(record.get('iin', '')) == str(iin):
            return record
    return None

def get_user_by_id(user_id):
    """Находит пользователя по ID"""
    worksheet = get_worksheet()
    records = worksheet.get_all_records()
    for record in records:
        if record.get('id') == user_id:
            return record
    return None

def create_user(iin, phone, name, role, password):
    """Создаёт нового пользователя"""
    worksheet = get_worksheet()
    next_id = get_next_id(worksheet)
    
    user_data = [
        next_id,
        iin,
        phone,
        name,
        role,
        hash_password(password),
        5.0,  # rating
        0,   # completed_tasks
        '',  # bio
        datetime.now().isoformat()
    ]
    worksheet.append_row(user_data)
    return next_id

def get_all_tasks(status_filter=None):
    """Получает все задачи"""
    worksheet = get_tasks_worksheet()
    records = worksheet.get_all_records()
    if status_filter:
        records = [r for r in records if r.get('status') == status_filter]
    return records

def get_tasks_by_customer(customer_id):
    """Задачи заказчика"""
    worksheet = get_tasks_worksheet()
    records = worksheet.get_all_records()
    return [r for r in records if r.get('customer_id') == customer_id]

def get_tasks_by_executor(executor_id):
    """Задачи исполнителя"""
    worksheet = get_tasks_worksheet()
    records = worksheet.get_all_records()
    return [r for r in records if r.get('executor_id') == executor_id]

def create_task(title, description, price, address, customer_id):
    """Создаёт новую задачу"""
    worksheet = get_tasks_worksheet()
    next_id = get_next_id(worksheet)
    
    task_data = [
        next_id,
        title,
        description,
        price,
        address,
        customer_id,
        '',  # executor_id
        'open',  # status
        datetime.now().isoformat()
    ]
    worksheet.append_row(task_data)
    return next_id

def get_task_by_id(task_id):
    """Получает задачу по ID"""
    worksheet = get_tasks_worksheet()
    records = worksheet.get_all_records()
    for record in records:
        if record.get('id') == task_id:
            return record
    return None

def update_task_field(task_id, field, value):
    """Обновляет поле в задаче"""
    worksheet = get_tasks_worksheet()
    records = worksheet.get_all_values()
    headers = records[0]
    
    col_index = headers.index(field) + 1
    row_index = None
    
    for i, row in enumerate(records[1:], start=2):
        if row[0] and int(row[0]) == task_id:
            row_index = i
            break
    
    if row_index:
        worksheet.update_cell(row_index, col_index, str(value))

def get_responses_for_task(task_id):
    """Получает отклики на задачу"""
    worksheet = get_responses_worksheet()
    records = worksheet.get_all_records()
    return [r for r in records if r.get('task_id') == task_id]

def create_response(task_id, executor_id, message):
    """Создаёт отклик на задачу"""
    worksheet = get_responses_worksheet()
    next_id = get_next_id(worksheet)
    
    response_data = [
        next_id,
        task_id,
        executor_id,
        message,
        'pending',
        datetime.now().isoformat()
    ]
    worksheet.append_row(response_data)

def update_user_field(user_id, field, value):
    """Обновляет поле пользователя"""
    worksheet = get_worksheet()
    records = worksheet.get_all_values()
    headers = records[0]
    
    col_index = headers.index(field) + 1
    row_index = None
    
    for i, row in enumerate(records[1:], start=2):
        if row[0] and int(row[0]) == user_id:
            row_index = i
            break
    
    if row_index:
        worksheet.update_cell(row_index, col_index, str(value))

def get_all_responses():
    """Получает все отклики"""
    worksheet = get_responses_worksheet()
    return worksheet.get_all_records()

# ========== HTML ШАБЛОН (встроен прямо в Python) ==========
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Помощь Рядом</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .glass {
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
        }
        .glass-card {
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.25);
        }
        .navbar-glass {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }
        .navbar-brand {
            font-weight: 600;
            font-size: 1.5rem;
            background: linear-gradient(135deg, #fff, #a8c0ff);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .nav-link, .text-white-nav { color: white !important; font-weight: 500; }
        .btn-apple {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 30px;
            padding: 12px 28px;
            font-weight: 600;
            color: white;
            transition: all 0.3s ease;
        }
        .btn-apple:hover { transform: translateY(-2px); color: white; }
        .btn-outline-apple {
            background: transparent;
            border: 2px solid white;
            border-radius: 30px;
            padding: 10px 24px;
            font-weight: 600;
            color: white;
            transition: all 0.3s;
        }
        .btn-outline-apple:hover { background: white; color: #667eea; }
        .form-glass {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            border-radius: 16px;
            padding: 12px 16px;
        }
        .form-glass:focus {
            background: rgba(255, 255, 255, 0.2);
            border-color: white;
            color: white;
            box-shadow: none;
        }
        .avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .fade-in { animation: fadeIn 0.5s ease-out; }
        .digit-captcha {
            font-size: 2rem;
            letter-spacing: 10px;
            background: rgba(255,255,255,0.1);
            display: inline-block;
            padding: 10px 20px;
            border-radius: 15px;
            font-family: monospace;
        }
        .badge-status-open { background-color: #28a745; }
        .badge-status-progress { background-color: #ffc107; color: #000; }
        .badge-status-completed { background-color: #6c757d; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-glass fixed-top">
    <div class="container">
        <a class="navbar-brand" href="/">
            <i class="fas fa-hands-helping"></i> Помощь Рядом
        </a>
        <div class="collapse navbar-collapse">
            <ul class="navbar-nav ms-auto">
                {% if session.user_id %}
                    <li class="nav-item"><a class="nav-link" href="/dashboard">Главная</a></li>
                    <li class="nav-item"><a class="nav-link" href="/profile">Кабинет</a></li>
                    <li class="nav-item"><a class="nav-link" href="/task/create">Создать заявку</a></li>
                    <li class="nav-item"><span class="nav-link text-white-nav">Привет, {{ session.user_name }}</span></li>
                    <li class="nav-item"><a class="nav-link" href="/logout">Выйти</a></li>
                {% else %}
                    <li class="nav-item"><a class="nav-link" href="/login">Вход</a></li>
                    <li class="nav-item"><a class="btn btn-outline-apple ms-2" href="/register">Регистрация</a></li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>

<div class="container mt-5 pt-5">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        {% endfor %}
    {% endwith %}
    
    {% block content %}{% endblock %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ========== РОУТЫ ==========
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, content=home_content())

def home_content():
    return '''
    <div class="fade-in text-center" style="min-height: 70vh; display: flex; align-items: center;">
        <div class="row w-100">
            <div class="col-12">
                <div class="glass p-5">
                    <h1 class="display-3 text-white mb-3">🤝 Помощь Рядом</h1>
                    <p class="lead text-white-50 mb-4">Находите помощь или помогайте другим в вашем районе</p>
                    <div class="row mt-5">
                        <div class="col-md-6 mb-3">
                            <div class="glass-card p-4">
                                <i class="fas fa-hand-sparkles fa-3x text-white mb-3"></i>
                                <h3 class="text-white">Нужна помощь?</h3>
                                <p class="text-white-50">Создайте заявку и найдите исполнителя</p>
                                <a href="/register" class="btn btn-apple mt-2">Зарегистрироваться</a>
                            </div>
                        </div>
                        <div class="col-md-6 mb-3">
                            <div class="glass-card p-4">
                                <i class="fas fa-heart fa-3x text-white mb-3"></i>
                                <h3 class="text-white">Можете помочь?</h3>
                                <p class="text-white-50">Откликайтесь на заявки и зарабатывайте</p>
                                <a href="/register" class="btn btn-outline-apple mt-2">Стать исполнителем</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        iin = request.form['iin']
        phone = request.form['phone']
        name = request.form['name']
        role = request.form['role']
        password = request.form['password']
        
        if get_user_by_iin(iin):
            flash('Пользователь с таким ИИН уже существует', 'danger')
            return redirect(url_for('register'))
        
        create_user(iin, phone, name, role, password)
        flash('Регистрация успешна! Войдите в аккаунт.', 'success')
        return redirect(url_for('login'))
    
    form_html = '''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="glass-card p-5 fade-in">
                <h2 class="text-white text-center mb-4">Регистрация</h2>
                <form method="POST">
                    <div class="mb-3">
                        <label class="text-white">ИИН (12 цифр)</label>
                        <input type="text" name="iin" class="form-control form-glass" required pattern="[0-9]{12}">
                    </div>
                    <div class="mb-3">
                        <label class="text-white">Телефон</label>
                        <input type="tel" name="phone" class="form-control form-glass" required>
                    </div>
                    <div class="mb-3">
                        <label class="text-white">Имя</label>
                        <input type="text" name="name" class="form-control form-glass" required>
                    </div>
                    <div class="mb-3">
                        <label class="text-white">Я хочу</label>
                        <select name="role" class="form-control form-glass">
                            <option value="customer">Заказывать помощь</option>
                            <option value="executor">Предлагать помощь</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="text-white">Пароль</label>
                        <input type="password" name="password" class="form-control form-glass" required>
                    </div>
                    <button type="submit" class="btn btn-apple w-100">Зарегистрироваться</button>
                </form>
                <p class="text-center text-white-50 mt-3">Уже есть аккаунт? <a href="/login" class="text-white">Войти</a></p>
            </div>
        </div>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE, content=form_html)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        iin = request.form['iin']
        password = request.form['password']
        
        user = get_user_by_iin(iin)
        if user and user.get('password_hash') == hash_password(password):
            session['user_id'] = user.get('id')
            session['user_name'] = user.get('name')
            session['user_role'] = user.get('role')
            flash(f'Добро пожаловать, {user.get("name")}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Неверный ИИН или пароль', 'danger')
        return redirect(url_for('login'))
    
    form_html = '''
    <div class="row justify-content-center">
        <div class="col-md-5">
            <div class="glass-card p-5 fade-in">
                <h2 class="text-white text-center mb-4">Вход</h2>
                <form method="POST">
                    <div class="mb-3">
                        <label class="text-white">ИИН</label>
                        <input type="text" name="iin" class="form-control form-glass" required>
                    </div>
                    <div class="mb-3">
                        <label class="text-white">Пароль</label>
                        <input type="password" name="password" class="form-control form-glass" required>
                    </div>
                    <button type="submit" class="btn btn-apple w-100">Войти</button>
                </form>
                <p class="text-center text-white-50 mt-3">Нет аккаунта? <a href="/register" class="text-white">Регистрация</a></p>
            </div>
        </div>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE, content=form_html)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    user_role = user.get('role')
    
    if user_role == 'customer':
        my_tasks = get_tasks_by_customer(session['user_id'])
        open_tasks = []
    else:
        my_tasks = get_tasks_by_executor(session['user_id'])
        open_tasks = get_all_tasks('open')
    
    tasks_html = ''
    
    if user_role == 'customer':
        tasks_html += '<h3 class="text-white mb-3">📋 Мои заявки</h3><div class="row">'
        for task in my_tasks:
            status_class = 'open' if task.get('status') == 'open' else ('progress' if task.get('status') == 'in_progress' else 'completed')
            tasks_html += f'''
                <div class="col-md-6 mb-3">
                    <div class="glass-card p-3">
                        <h5 class="text-white">{task.get('title')}</h5>
                        <p class="text-white-50">{task.get('description', '')[:100]}...</p>
                        <p class="text-white">💰 {task.get('price')} ₸ | 📍 {task.get('address')}</p>
                        <span class="badge badge-status-{status_class} mb-2">{task.get('status')}</span>
                        <a href="/task/{task.get('id')}" class="btn btn-sm btn-outline-apple">Подробнее</a>
                    </div>
                </div>
            '''
        if not my_tasks:
            tasks_html += '<div class="col-12"><div class="glass p-4 text-center"><p class="text-white">У вас пока нет заявок</p><a href="/task/create" class="btn btn-apple">Создать первую</a></div></div>'
        tasks_html += '</div>'
    else:
        tasks_html += '<h3 class="text-white mb-3">🔍 Доступные заявки</h3><div class="row">'
        for task in open_tasks:
            tasks_html += f'''
                <div class="col-md-6 mb-3">
                    <div class="glass-card p-3">
                        <h5 class="text-white">{task.get('title')}</h5>
                        <p class="text-white-50">{task.get('description', '')[:100]}...</p>
                        <p class="text-white">💰 {task.get('price')} ₸ | 📍 {task.get('address')}</p>
                        <a href="/task/{task.get('id')}" class="btn btn-sm btn-apple">Откликнуться</a>
                    </div>
                </div>
            '''
        if not open_tasks:
            tasks_html += '<div class="col-12"><div class="glass p-4 text-center"><p class="text-white">Пока нет доступных заявок</p></div></div>'
        tasks_html += '</div>'
        
        tasks_html += '<h3 class="text-white mb-3 mt-4">✅ Мои выполненные заказы</h3><div class="row">'
        for task in my_tasks:
            if task.get('status') == 'completed':
                tasks_html += f'''
                    <div class="col-md-6 mb-3">
                        <div class="glass-card p-3">
                            <h5 class="text-white">{task.get('title')}</h5>
                            <p class="text-white">💰 {task.get('price')} ₸</p>
                            <span class="badge badge-status-completed">Завершён</span>
                        </div>
                    </div>
                '''
        tasks_html += '</div>'
    
    dashboard_html = f'''
    <div class="fade-in">
        <div class="row">
            <div class="col-12 mb-4">
                <div class="glass p-4 text-center">
                    <h1 class="text-white">Добро пожаловать, {user.get('name')}!</h1>
                    <p class="text-white-50">⭐ Рейтинг: {user.get('rating')} | ✅ Выполнено: {user.get('completed_tasks', 0)}</p>
                </div>
            </div>
        </div>
        {tasks_html}
    </div>
    '''
    return render_template_string(HTML_TEMPLATE, content=dashboard_html)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    
    if request.method == 'POST':
        update_user_field(session['user_id'], 'name', request.form['name'])
        update_user_field(session['user_id'], 'phone', request.form['phone'])
        update_user_field(session['user_id'], 'bio', request.form.get('bio', ''))
        session['user_name'] = request.form['name']
        flash('Профиль обновлён', 'success')
        return redirect(url_for('profile'))
    
    profile_html = f'''
    <div class="fade-in">
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="glass-card p-4 text-center">
                    <div class="avatar mx-auto mb-3" style="width: 100px; height: 100px; font-size: 2.5rem;">{user.get('name', '')[0].upper()}</div>
                    <h3 class="text-white">{user.get('name')}</h3>
                    <p class="text-white-50"><i class="fas fa-star text-warning"></i> Рейтинг: {user.get('rating')}</p>
                    <p class="text-white-50"><i class="fas fa-check-circle text-success"></i> Выполнено: {user.get('completed_tasks', 0)}</p>
                    <p class="text-white-50"><i class="fas fa-user-tag"></i> {'Заказчик' if user.get('role') == 'customer' else 'Исполнитель'}</p>
                </div>
            </div>
            <div class="col-md-8">
                <div class="glass-card p-4">
                    <h4 class="text-white mb-3">✏️ Редактировать профиль</h4>
                    <form method="POST">
                        <div class="mb-3"><label class="text-white">Имя</label><input type="text" name="name" class="form-control form-glass" value="{user.get('name')}"></div>
                        <div class="mb-3"><label class="text-white">Телефон</label><input type="text" name="phone" class="form-control form-glass" value="{user.get('phone')}"></div>
                        <div class="mb-3"><label class="text-white">О себе</label><textarea name="bio" class="form-control form-glass" rows="3">{user.get('bio', '')}</textarea></div>
                        <button type="submit" class="btn btn-apple">Сохранить изменения</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE, content=profile_html)

@app.route('/task/create', methods=['GET', 'POST'])
def create_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        create_task(
            request.form['title'],
            request.form['description'],
            int(request.form['price']),
            request.form['address'],
            session['user_id']
        )
        flash('Заявка создана!', 'success')
        return redirect(url_for('dashboard'))
    
    form_html = '''
    <div class="row justify-content-center">
        <div class="col-md-7">
            <div class="glass-card p-5 fade-in">
                <h2 class="text-white text-center mb-4">📝 Создать заявку</h2>
                <form method="POST">
                    <div class="mb-3"><label class="text-white">Что нужно сделать?</label><input type="text" name="title" class="form-control form-glass" required></div>
                    <div class="mb-3"><label class="text-white">Описание</label><textarea name="description" class="form-control form-glass" rows="3" required></textarea></div>
                    <div class="mb-3"><label class="text-white">Цена (тенге)</label><input type="number" name="price" class="form-control form-glass" required></div>
                    <div class="mb-3"><label class="text-white">Адрес или район</label><input type="text" name="address" class="form-control form-glass" required></div>
                    <button type="submit" class="btn btn-apple w-100">Опубликовать</button>
                </form>
            </div>
        </div>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE, content=form_html)

@app.route('/task/<int:task_id>')
def view_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    task = get_task_by_id(task_id)
    if not task:
        flash('Заявка не найдена', 'danger')
        return redirect(url_for('dashboard'))
    
    user = get_user_by_id(session['user_id'])
    customer = get_user_by_id(task.get('customer_id'))
    responses = get_responses_for_task(task_id)
    
    responses_html = ''
    for r in responses:
        executor = get_user_by_id(r.get('executor_id'))
        executor_name = executor.get('name') if executor else 'Unknown'
        executor_rating = executor.get('rating') if executor else 5
        responses_html += f'''
            <div class="mb-3 p-2" style="background: rgba(255,255,255,0.1); border-radius: 12px;">
                <strong class="text-white">{executor_name}</strong>
                <div class="stars">{'⭐' * int(float(executor_rating))}</div>
                <p class="text-white-50 small">{r.get('message', '')[:100]}</p>
        '''
        if user.get('id') == task.get('customer_id') and task.get('status') == 'open' and r.get('status') == 'pending':
            responses_html += f'<a href="/response/{r.get("id")}/accept" class="btn btn-sm btn-apple">Выбрать</a>'
        if r.get('status') == 'accepted':
            responses_html += '<span class="badge bg-success">✅ Выбран</span>'
        responses_html += '</div>'
    
    status_class = 'open' if task.get('status') == 'open' else ('progress' if task.get('status') == 'in_progress' else 'completed')
    status_text = '🟢 Ищет исполнителя' if task.get('status') == 'open' else ('🟡 В работе' if task.get('status') == 'in_progress' else '⚪ Завершена')
    
    task_html = f'''
    <div class="fade-in">
        <div class="row">
            <div class="col-md-8">
                <div class="glass-card p-4">
                    <h2 class="text-white">{task.get('title')}</h2>
                    <p class="text-white-50">{task.get('description')}</p>
                    <p class="text-white">💰 <strong>{task.get('price')} тенге</strong></p>
                    <p class="text-white">📍 {task.get('address')}</p>
                    <p class="text-white-50">👤 Заказчик: {customer.get('name') if customer else 'Unknown'}</p>
                    <span class="badge badge-status-{status_class} fs-6">{status_text}</span>
                </div>
            </div>
            <div class="col-md-4">
                <div class="glass-card p-4">
                    <h5 class="text-white">📢 Отклики</h5>
                    {responses_html if responses_html else '<p class="text-white-50">Пока нет откликов</p>'}
                </div>
            </div>
        </div>
    </div>
    '''
    
    if user.get('role') == 'executor' and task.get('status') == 'open':
        captcha_code = ''.join(random.choices(string.digits, k=6))
        session['captcha_code'] = captcha_code
        task_html += f'''
        <div class="row mt-3">
            <div class="col-12">
                <div class="glass-card p-4">
                    <h5 class="text-white">💬 Откликнуться на заявку</h5>
                    <form method="POST" action="/task/{task_id}/respond">
                        <textarea name="message" class="form-control form-glass mb-2" rows="2" placeholder="Расскажите, почему вы можете помочь..." required></textarea>
                        <div class="mb-2">
                            <div class="digit-captcha">{captcha_code}</div>
                            <input type="text" name="captcha" class="form-control form-glass mt-2" placeholder="Введите код с картинки" required style="width: 200px;">
                        </div>
                        <button type="submit" class="btn btn-apple">Отправить отклик</button>
                    </form>
                </div>
            </div>
        </div>
        '''
    
    return render_template_string(HTML_TEMPLATE, content=task_html)

@app.route('/task/<int:task_id>/respond', methods=['POST'])
def respond_to_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    captcha_input = request.form.get('captcha')
    captcha_session = session.get('captcha_code')
    
    if not captcha_input or captcha_input != captcha_session:
        flash('Неверный код подтверждения', 'danger')
        return redirect(url_for('view_task', task_id=task_id))
    
    create_response(task_id, session['user_id'], request.form['message'])
    flash('Отклик отправлен!', 'success')
    return redirect(url_for('view_task', task_id=task_id))

@app.route('/response/<int:response_id>/accept')
def accept_response(response_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    responses = get_all_responses()
    response = None
    for r in responses:
        if r.get('id') == response_id:
            response = r
            break
    
    if not response:
        flash('Отклик не найден', 'danger')
        return redirect(url_for('dashboard'))
    
    task = get_task_by_id(response.get('task_id'))
    if task.get('customer_id') != session['user_id']:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('dashboard'))
    
    update_task_field(task.get('id'), 'executor_id', response.get('executor_id'))
    update_task_field(task.get('id'), 'status', 'in_progress')
    
    # Обновляем статус отклика
    # Для простоты отметим, что выбран этот отклик
    flash('Исполнитель выбран!', 'success')
    return redirect(url_for('view_task', task_id=task.get('id')))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)