from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, date, timedelta
import os
import re
import threading
import time
from functools import wraps
import random
import string
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)

# =====================================================
# ДЕКОРАТОР ДЛЯ ПРОВЕРКИ ВХОДА
# =====================================================

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# ФУНКЦИИ ДЛЯ КАПЧИ
# =====================================================

import random
import string
import io
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def generate_captcha_text():
    """Генерирует случайный текст для капчи"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_captcha():
    """Генерирует изображение капчи с БОЛЬШИМИ символами"""
    # Генерируем случайный текст
    captcha_text = generate_captcha_text()
    
    # Сохраняем текст в сессии
    session['captcha_text'] = captcha_text
    session['captcha_time'] = datetime.now().timestamp()
    
    # 📌 ЗДЕСЬ МЕНЯЙ РАЗМЕРЫ (чем больше числа, тем крупнее)
    width = 400          # Ширина картинки (было 400)
    height = 150         # Высота картинки (было 150)
    font_size = 240      # Размер шрифта (было 65)
    symbol_spacing = 45  # Расстояние между буквами (было 55)
    
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Добавляем шум
    for _ in range(1000):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
    
    # Добавляем толстые линии
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(random.randint(100, 150), random.randint(100, 150), random.randint(100, 150)), width=4)
    
    # Загружаем шрифт
    font = None
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except:
            continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # Рисуем большие буквы
    x = 70  # Отступ слева
    y_center = height // 2 - 30  # Центрируем по вертикали
    
    for i, char in enumerate(captcha_text):
        # Случайное смещение для каждой буквы
        y_offset = random.randint(-20, 20)
        y = y_center + y_offset
        
        # Тень
        draw.text((x + 5, y + 5), char, fill=(180, 180, 180), font=font)
        
        # Основная буква со случайным цветом
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x, y), char, fill=color, font=font)
        
        x += symbol_spacing + random.randint(-10, 10)
    
    # Сохраняем
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr

# =====================================================
# МАРШРУТЫ АВТОРИЗАЦИИ
# =====================================================

@app.route('/captcha-image')
def captcha_image():
    """Возвращает изображение капчи"""
    try:
        data = generate_captcha()
        return send_file(
            io.BytesIO(data.getvalue()),
            mimetype='image/png'
        )
    except Exception as e:
        print(f"Ошибка генерации капчи: {e}")
        # Возвращаем простую заглушку при ошибке
        return send_file(
            io.BytesIO(b''),
            mimetype='image/png'
        )

@app.route('/refresh-captcha')
def refresh_captcha():
    """Обновляет капчу"""
    generate_captcha()
    return '', 204

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    if session.get('logged_in'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        captcha_input = request.form.get('captcha', '').strip().upper()
        
        # Проверяем капчу
        captcha_text = session.get('captcha_text')
        captcha_time = session.get('captcha_time', 0)
        
        # Проверяем, не истекло ли время капчи (5 минут)
        if datetime.now().timestamp() - captcha_time > 300:
            flash('Время действия капчи истекло. Попробуйте снова.', 'danger')
            return redirect(url_for('login'))
        
        if not captcha_text or captcha_input != captcha_text:
            flash('Неверный код с картинки!', 'danger')
            return redirect(url_for('login'))
        
        # Проверяем логин и пароль
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Очищаем капчу из сессии
            session.pop('captcha_text', None)
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!', 'danger')
    
    # Генерируем новую капчу при загрузке страницы
    generate_captcha()
    
    return render_template('login.html')
    
# =====================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ВАЛИДАЦИИ
# =====================================================

def calculate_age(birth_date):
    """Расчет возраста на основе даты рождения"""
    if not birth_date:
        return None
    today = date.today()
    
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age

def validate_snils(snils, exclude_id=None):
    """Проверка и очистка СНИЛС"""
    if not snils:
        return None, None
    snils = re.sub(r'\D', '', snils)
    if len(snils) > 14:
        snils = snils[:14]
    query = Employee.query.filter_by(snils=snils)
    if exclude_id:
        query = query.filter(Employee.id != exclude_id)
    existing = query.first()
    if existing:
        return None, "СНИЛС уже существует в базе данных"
    return snils, None

def validate_inn(inn, exclude_id=None):
    """Проверка и очистка ИНН"""
    if not inn:
        return None, None
    inn = re.sub(r'\D', '', inn)
    if len(inn) > 12:
        inn = inn[:12]
    query = Employee.query.filter_by(inn=inn)
    if exclude_id:
        query = query.filter(Employee.id != exclude_id)
    existing = query.first()
    if existing:
        return None, "ИНН уже существует в базе данных"
    return inn, None

def validate_email(email, exclude_id=None):
    """Проверка email на уникальность"""
    if not email:
        return None, None
    email = email.strip().lower()
    query = Employee.query.filter_by(email=email)
    if exclude_id:
        query = query.filter(Employee.id != exclude_id)
    existing = query.first()
    if existing:
        return None, "Email уже существует в базе данных"
    return email, None

def auto_assign_department_head(employee_id, staffing_id):
    """Автоматически назначает сотрудника руководителем отдела, если его должность руководящая"""
    try:
        staffing = Staffing.query.get(staffing_id)
        if not staffing:
            return
        
        position = staffing.position
        department = staffing.department
        
        is_management = position.category in ['top_management', 'middle_management'] or position.is_head
        
        if is_management and department:
            department.manager_id = employee_id
            db.session.commit()
            print(f"✅ Сотрудник {employee_id} назначен руководителем отдела {department.name}")
    except Exception as e:
        print(f"Ошибка при назначении руководителя: {e}")
        db.session.rollback()

def check_head_position_available(staffing_id, exclude_employee_id=None):
    """Проверяет, свободна ли руководящая должность"""
    staffing = Staffing.query.get(staffing_id)
    
    if not staffing:
        return True, None
    
    is_head = staffing.position.category in ['top_management', 'middle_management'] or staffing.position.is_head
    
    if not is_head:
        return True, None
    
    existing_assignment = EmployeePosition.query.filter(
        EmployeePosition.staffing_id == staffing_id,
        EmployeePosition.end_date == None
    )
    
    if exclude_employee_id:
        existing_assignment = existing_assignment.filter(EmployeePosition.employee_id != exclude_employee_id)
    
    existing = existing_assignment.first()
    
    if existing:
        return False, existing.employee.full_name()
    
    return True, None

def cleanup_dismissed_employees():
    """Удаляет данные уволенных сотрудников, у которых прошло 7 дней"""
    try:
        today = date.today()
        to_delete = DismissedEmployee.query.filter(
            DismissedEmployee.delete_after_date <= today
        ).all()
        
        for item in to_delete:
            Employee.query.filter_by(id=item.employee_id).delete()
            Vacation.query.filter_by(employee_id=item.employee_id).delete()
            SickLeave.query.filter_by(employee_id=item.employee_id).delete()
            Education.query.filter_by(employee_id=item.employee_id).delete()
            Order.query.filter_by(employee_id=item.employee_id).delete()
            EmployeePosition.query.filter_by(employee_id=item.employee_id).delete()
            db.session.delete(item)
        
        if to_delete:
            db.session.commit()
            print(f"✅ Удалено {len(to_delete)} уволенных сотрудников")
            
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при очистке уволенных сотрудников: {e}")

# =====================================================
# МОДЕЛИ
# =====================================================

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.Enum('M', 'F', name='gender_enum'), nullable=False)
    snils = db.Column(db.String(14), unique=True)
    inn = db.Column(db.String(12), unique=True)
    passport_series = db.Column(db.String(10))
    passport_number = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    address = db.Column(db.Text)
    hire_date = db.Column(db.Date, nullable=False)
    dismissal_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.now, onupdate=datetime.now)
    
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()
    
    def age(self):
        if self.birth_date:
            today = date.today()
            birth = self.birth_date
            if isinstance(birth, datetime):
                birth = birth.date()
            age = today.year - birth.year
            if (today.month, today.day) < (birth.month, birth.day):
                age -= 1
            return age
        return None

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True)
    parent_department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    description = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    parent = db.relationship('Department', remote_side=[id], backref='children')
    manager = db.relationship('Employee', foreign_keys=[manager_id])

class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.Enum('top_management', 'middle_management', 'specialist', 'worker', 'junior'), default='specialist')
    is_head = db.Column(db.Boolean, default=False)
    base_salary = db.Column(db.Numeric(12,2), default=0)
    requires_education = db.Column(db.Boolean, default=False)
    requires_experience_years = db.Column(db.Integer, default=0)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    def is_management(self):
        return self.category in ['top_management', 'middle_management'] or self.is_head

class Staffing(db.Model):
    __tablename__ = 'staffing'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('positions.id'), nullable=False)
    rate = db.Column(db.Numeric(5,2), default=1.0)
    salary = db.Column(db.Numeric(12,2), nullable=False)
    vacation_days = db.Column(db.Integer, default=28)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    department = db.relationship('Department', backref='staffing')
    position = db.relationship('Position', backref='staffing')
    
    def is_head_position(self):
        return self.position.is_head or self.position.category in ['top_management', 'middle_management']
    
    def get_current_holder(self):
        assignment = EmployeePosition.query.filter_by(
            staffing_id=self.id,
            end_date=None
        ).first()
        return assignment.employee if assignment else None

class EmployeePosition(db.Model):
    __tablename__ = 'employee_positions'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    staffing_id = db.Column(db.Integer, db.ForeignKey('staffing.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_main = db.Column(db.Boolean, default=True)
    contract_number = db.Column(db.String(50))
    contract_date = db.Column(db.Date)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee = db.relationship('Employee', backref='assignments')
    staffing = db.relationship('Staffing', backref='assignments')

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    order_type = db.Column(db.Enum('hiring', 'dismissal', 'transfer', 'vacation', 'salary_change', 'promotion'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    description = db.Column(db.Text)
    document_link = db.Column(db.String(500))
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee = db.relationship('Employee', backref='orders')

class Vacation(db.Model):
    __tablename__ = 'vacations'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    type = db.Column(db.Enum('annual', 'additional', 'unpaid', 'educational', 'maternity'), nullable=False)
    days_count = db.Column(db.Integer)
    approved_by_order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    status = db.Column(db.Enum('planned', 'approved', 'completed', 'cancelled'), default='planned')
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee = db.relationship('Employee', backref='vacations')
    
    def __init__(self, **kwargs):
        super(Vacation, self).__init__(**kwargs)
        if self.start_date and self.end_date:
            if isinstance(self.start_date, datetime):
                self.start_date = self.start_date.date()
            if isinstance(self.end_date, datetime):
                self.end_date = self.end_date.date()
            self.days_count = (self.end_date - self.start_date).days + 1

class SickLeave(db.Model):
    __tablename__ = 'sick_leaves'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    sick_list_number = db.Column(db.String(50), unique=True, nullable=False)
    diagnosis = db.Column(db.String(200))
    doctor_name = db.Column(db.String(200))
    hospital_name = db.Column(db.String(200))
    days_count = db.Column(db.Integer)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee = db.relationship('Employee', backref='sick_leaves')
    
    def __init__(self, **kwargs):
        super(SickLeave, self).__init__(**kwargs)
        if self.start_date and self.end_date:
            if isinstance(self.start_date, datetime):
                self.start_date = self.start_date.date()
            if isinstance(self.end_date, datetime):
                self.end_date = self.end_date.date()
            self.days_count = (self.end_date - self.start_date).days + 1

class SalaryHistory(db.Model):
    __tablename__ = 'salary_history'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_position_id = db.Column(db.Integer, db.ForeignKey('employee_positions.id'), nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    salary_amount = db.Column(db.Numeric(12,2), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    reason = db.Column(db.String(200))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee_position = db.relationship('EmployeePosition', backref='salary_history')

class Education(db.Model):
    __tablename__ = 'education'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    institution_name = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.Enum('high_school', 'vocational', 'bachelor', 'master', 'phd'), nullable=False)
    specialization = db.Column(db.String(200))
    graduation_year = db.Column(db.Integer)
    diploma_number = db.Column(db.String(50))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
    
    employee = db.relationship('Employee', backref='education')

class DismissedEmployee(db.Model):
    """Таблица для отслеживания уволенных сотрудников"""
    __tablename__ = 'dismissed_employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False)
    dismissed_date = db.Column(db.Date, nullable=False)
    delete_after_date = db.Column(db.Date, nullable=False)
    full_name = db.Column(db.String(200))
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)

# =====================================================
# МАРШРУТЫ
# =====================================================

@app.route('/')
@login_required
def index():
    total_employees = Employee.query.filter_by(is_active=True).count()
    total_employees_all = Employee.query.count()
    total_departments = Department.query.count()
    total_positions = Position.query.count()
    
    male_count = Employee.query.filter_by(gender='M', is_active=True).count()
    female_count = Employee.query.filter_by(gender='F', is_active=True).count()
    
    today = date.today()
    age_groups = {'18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '55+': 0}
    
    employees = Employee.query.filter_by(is_active=True).all()
    for emp in employees:
        if emp.birth_date:
            age = calculate_age(emp.birth_date)
            if age:
                if 18 <= age <= 25:
                    age_groups['18-25'] += 1
                elif 26 <= age <= 35:
                    age_groups['26-35'] += 1
                elif 36 <= age <= 45:
                    age_groups['36-45'] += 1
                elif 46 <= age <= 55:
                    age_groups['46-55'] += 1
                elif age > 55:
                    age_groups['55+'] += 1
    
    dept_stats = []
    for dept in Department.query.all():
        employees_count = db.session.query(Employee).join(
            EmployeePosition, Employee.id == EmployeePosition.employee_id
        ).join(
            Staffing, EmployeePosition.staffing_id == Staffing.id
        ).filter(
            Staffing.department_id == dept.id,
            EmployeePosition.end_date == None,
            Employee.is_active == True
        ).count()
        
        salary_result = db.session.query(db.func.sum(Staffing.salary * Staffing.rate)).filter(
            Staffing.department_id == dept.id,
            Staffing.is_active == True
        ).scalar()
        
        salary_fund = float(salary_result) if salary_result else 0
        
        dept_stats.append({
            'name': dept.name,
            'employees_count': employees_count,
            'salary_fund': salary_fund,
            'manager': dept.manager.full_name() if dept.manager else 'Не назначен'
        })
    
    position_stats = []
    for pos in Position.query.all():
        employees_count = db.session.query(Employee).join(
            EmployeePosition, Employee.id == EmployeePosition.employee_id
        ).join(
            Staffing, EmployeePosition.staffing_id == Staffing.id
        ).filter(
            Staffing.position_id == pos.id,
            EmployeePosition.end_date == None,
            Employee.is_active == True
        ).count()
        
        position_stats.append({
            'name': pos.name,
            'category': pos.category,
            'employees_count': employees_count,
            'base_salary': float(pos.base_salary) if pos.base_salary else 0
        })
    
    total_staffing = Staffing.query.filter_by(is_active=True).count()
    occupied_positions = EmployeePosition.query.filter(EmployeePosition.end_date == None).count()
    
    head_positions = Staffing.query.filter(
        Staffing.is_active == True,
        Staffing.position.has(Position.is_head == True)
    ).count()
    
    occupied_head_positions = db.session.query(EmployeePosition).join(
        Staffing, EmployeePosition.staffing_id == Staffing.id
    ).join(
        Position, Staffing.position_id == Position.id
    ).filter(
        EmployeePosition.end_date == None,
        Position.is_head == True
    ).count()
    
    on_vacation_now = db.session.query(Employee).join(
        Vacation, Employee.id == Vacation.employee_id
    ).filter(
        Vacation.start_date <= today,
        Vacation.end_date >= today,
        Vacation.status.in_(['planned', 'approved']),
        Employee.is_active == True
    ).count()
    
    on_sick_leave_now = db.session.query(Employee).join(
        SickLeave, Employee.id == SickLeave.employee_id
    ).filter(
        SickLeave.start_date <= today,
        SickLeave.end_date >= today,
        Employee.is_active == True
    ).count()
    
    current_month = datetime.now().month
    birthdays = Employee.query.filter(
        Employee.is_active == True,
        db.extract('month', Employee.birth_date) == current_month
    ).all()
    
    on_vacation_list = db.session.query(Employee).join(
        Vacation, Employee.id == Vacation.employee_id
    ).filter(
        Vacation.start_date <= today,
        Vacation.end_date >= today,
        Vacation.status.in_(['planned', 'approved']),
        Employee.is_active == True
    ).limit(10).all()
    
    thirty_days_ago = today - timedelta(days=30)
    recent_hires = Employee.query.filter(
        Employee.hire_date >= thirty_days_ago,
        Employee.is_active == True
    ).order_by(Employee.hire_date.desc()).limit(10).all()
    
    next_30_days = today + timedelta(days=30)
    upcoming_birthdays_list = []
    
    for emp in employees:
        if emp.birth_date:
            birthday_this_year = date(today.year, emp.birth_date.month, emp.birth_date.day)
            if today <= birthday_this_year <= next_30_days:
                upcoming_birthdays_list.append(emp)
    
    all_employees = Employee.query.filter_by(is_active=True).all()
    
    return render_template('index.html',
                         total_employees=total_employees,
                         total_employees_all=total_employees_all,
                         total_departments=total_departments,
                         total_positions=total_positions,
                         male_count=male_count,
                         female_count=female_count,
                         age_groups=age_groups,
                         dept_stats=dept_stats,
                         position_stats=position_stats,
                         total_staffing=total_staffing,
                         occupied_positions=occupied_positions,
                         head_positions=head_positions,
                         occupied_head_positions=occupied_head_positions,
                         on_vacation_now=on_vacation_now,
                         on_sick_leave_now=on_sick_leave_now,
                         birthdays=birthdays,
                         on_vacation_list=on_vacation_list,
                         recent_hires=recent_hires,
                         upcoming_birthdays_list=upcoming_birthdays_list[:10],
                         employees=all_employees)

# ==================== СОТРУДНИКИ С ФИЛЬТРАЦИЕЙ ====================

@app.route('/employees')
@login_required
def employees():
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    position_id = request.args.get('position_id', type=int)
    status = request.args.get('status', 'all')
    
    query = Employee.query
    
    if search:
        query = query.filter(
            db.or_(
                Employee.last_name.like(f'%{search}%'),
                Employee.first_name.like(f'%{search}%'),
                Employee.middle_name.like(f'%{search}%'),
                Employee.phone.like(f'%{search}%'),
                Employee.email.like(f'%{search}%')
            )
        )
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'dismissed':
        query = query.filter_by(is_active=False)
    
    if department_id:
        query = query.filter(
            Employee.id.in_(
                db.session.query(EmployeePosition.employee_id)
                .join(Staffing)
                .filter(Staffing.department_id == department_id)
            )
        )
    
    if position_id:
        query = query.filter(
            Employee.id.in_(
                db.session.query(EmployeePosition.employee_id)
                .join(Staffing)
                .filter(Staffing.position_id == position_id)
            )
        )
    
    employees_list = query.order_by(Employee.last_name).all()
    
    departments = Department.query.all()
    positions = Position.query.all()
    
    return render_template('employees.html', 
                         employees=employees_list,
                         departments=departments,
                         positions=positions,
                         search=search,
                         department_id=department_id,
                         position_id=position_id,
                         status=status)

@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        errors = []
        
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        hire_date_str = request.form.get('hire_date')
        
        if not last_name:
            errors.append('Фамилия обязательна для заполнения')
        if not first_name:
            errors.append('Имя обязательно для заполнения')
        if not hire_date_str:
            errors.append('Дата приёма обязательна для заполнения')
        
        gender = request.form.get('gender')
        if not gender or gender not in ['M', 'F']:
            errors.append('Пол обязателен для заполнения')
        
        snils_raw = request.form.get('snils', '')
        snils, snils_error = validate_snils(snils_raw)
        if snils_error:
            errors.append(snils_error)
        
        inn_raw = request.form.get('inn', '')
        inn, inn_error = validate_inn(inn_raw)
        if inn_error:
            errors.append(inn_error)
        
        email_raw = request.form.get('email', '')
        email, email_error = validate_email(email_raw)
        if email_error:
            errors.append(email_error)
        
        birth_date = None
        if request.form.get('birth_date'):
            try:
                birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
                age = calculate_age(birth_date)
                if age is not None and age < 14:
                    errors.append('Возраст сотрудника должен быть не менее 14 лет')
            except ValueError:
                errors.append('Неверный формат даты рождения')
        
        hire_date = None
        try:
            if hire_date_str:
                hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
                if hire_date > date.today():
                    errors.append('Дата приёма не может быть в будущем')
        except ValueError:
            errors.append('Неверный формат даты приёма')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('employee_form.html', employee=None, form_data=request.form)
        
        try:
            employee = Employee(
                last_name=last_name,
                first_name=first_name,
                middle_name=request.form.get('middle_name', '').strip() or None,
                birth_date=birth_date,
                gender=gender,
                snils=snils,
                inn=inn,
                passport_series=request.form.get('passport_series', '').strip() or None,
                passport_number=request.form.get('passport_number', '').strip() or None,
                phone=request.form.get('phone', '').strip() or None,
                email=email,
                address=request.form.get('address', '').strip() or None,
                hire_date=hire_date,
                is_active=True
            )
            db.session.add(employee)
            db.session.commit()
            flash('Сотрудник добавлен успешно!', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'danger')
    
    return render_template('employee_form.html', employee=None, form_data=None)

@app.route('/employee/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if request.method == 'POST':
        errors = []
        
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        hire_date_str = request.form.get('hire_date')
        
        if not last_name:
            errors.append('Фамилия обязательна для заполнения')
        if not first_name:
            errors.append('Имя обязательно для заполнения')
        if not hire_date_str:
            errors.append('Дата приёма обязательна для заполнения')
        
        gender = request.form.get('gender')
        if not gender or gender not in ['M', 'F']:
            errors.append('Пол обязателен для заполнения')
        
        snils_raw = request.form.get('snils', '')
        snils = None
        if snils_raw:
            snils = re.sub(r'\D', '', snils_raw)
            if len(snils) > 14:
                snils = snils[:14]
            existing = Employee.query.filter(Employee.snils == snils, Employee.id != id).first()
            if existing:
                errors.append('СНИЛС уже существует в базе данных')
        
        inn_raw = request.form.get('inn', '')
        inn = None
        if inn_raw:
            inn = re.sub(r'\D', '', inn_raw)
            if len(inn) > 12:
                inn = inn[:12]
            existing = Employee.query.filter(Employee.inn == inn, Employee.id != id).first()
            if existing:
                errors.append('ИНН уже существует в базе данных')
        
        email_raw = request.form.get('email', '')
        email = None
        if email_raw:
            email = email_raw.strip().lower()
            existing = Employee.query.filter(Employee.email == email, Employee.id != id).first()
            if existing:
                errors.append('Email уже существует в базе данных')
        
        birth_date = employee.birth_date
        if request.form.get('birth_date'):
            try:
                birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date()
                age = calculate_age(birth_date)
                if age is not None and age < 14:
                    errors.append('Возраст сотрудника должен быть не менее 14 лет')
            except ValueError:
                errors.append('Неверный формат даты рождения')
        
        hire_date = employee.hire_date
        try:
            if hire_date_str:
                hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
                if hire_date > date.today():
                    errors.append('Дата приёма не может быть в будущем')
        except ValueError:
            errors.append('Неверный формат даты приёма')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('employee_form.html', employee=employee)
        
        try:
            employee.last_name = last_name
            employee.first_name = first_name
            employee.middle_name = request.form.get('middle_name', '').strip() or None
            employee.birth_date = birth_date
            employee.gender = gender
            employee.snils = snils
            employee.inn = inn
            employee.passport_series = request.form.get('passport_series', '').strip() or None
            employee.passport_number = request.form.get('passport_number', '').strip() or None
            employee.phone = request.form.get('phone', '').strip() or None
            employee.email = email
            employee.address = request.form.get('address', '').strip() or None
            employee.hire_date = hire_date
            
            db.session.commit()
            flash('Данные сотрудника обновлены!', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}', 'danger')
    
    return render_template('employee_form.html', employee=employee)

@app.route('/employee/<int:id>/view')
@login_required
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    assignments = EmployeePosition.query.filter_by(employee_id=id).all()
    vacations = Vacation.query.filter_by(employee_id=id).order_by(Vacation.start_date.desc()).all()
    sick_leaves = SickLeave.query.filter_by(employee_id=id).order_by(SickLeave.start_date.desc()).all()
    
    return render_template('employee_view.html', 
                         employee=employee, 
                         assignments=assignments,
                         vacations=vacations,
                         sick_leaves=sick_leaves)

@app.route('/employee/<int:id>/dismiss', methods=['POST'])
@login_required
def dismiss_employee(id):
    employee = Employee.query.get_or_404(id)
    
    try:
        dismissed = DismissedEmployee(
            employee_id=employee.id,
            dismissed_date=date.today(),
            delete_after_date=date.today() + timedelta(days=7),
            full_name=employee.full_name(),
            last_name=employee.last_name,
            first_name=employee.first_name,
            middle_name=employee.middle_name
        )
        db.session.add(dismissed)
        
        active_assignments = EmployeePosition.query.filter_by(employee_id=id, end_date=None).all()
        for assignment in active_assignments:
            assignment.end_date = date.today()
        
        department = Department.query.filter_by(manager_id=id).first()
        if department:
            department.manager_id = None
        
        Vacation.query.filter_by(employee_id=id).delete()
        SickLeave.query.filter_by(employee_id=id).delete()
        Education.query.filter_by(employee_id=id).delete()
        Order.query.filter_by(employee_id=id).delete()
        EmployeePosition.query.filter_by(employee_id=id).delete()
        
        db.session.delete(employee)
        db.session.commit()
        
        flash(f'Сотрудник {employee.full_name()} уволен и будет полностью удалён из базы через 7 дней!', 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при увольнении: {str(e)}', 'danger')
    
    return redirect(url_for('employees'))

@app.route('/dismissed-employees')
@login_required
def dismissed_employees():
    dismissed_list = DismissedEmployee.query.order_by(DismissedEmployee.delete_after_date).all()
    
    today = date.today()
    for item in dismissed_list:
        days_left = (item.delete_after_date - today).days
        item.days_left = days_left
    
    return render_template('dismissed_employees.html', dismissed=dismissed_list)

@app.route('/restore-dismissed/<int:dismissed_id>', methods=['POST'])
@login_required
def restore_dismissed_employee(dismissed_id):
    try:
        dismissed = DismissedEmployee.query.get_or_404(dismissed_id)
        
        employee = Employee(
            id=dismissed.employee_id,
            last_name=dismissed.last_name,
            first_name=dismissed.first_name,
            middle_name=dismissed.middle_name,
            birth_date=None,
            gender='M',
            snils=None,
            inn=None,
            passport_series=None,
            passport_number=None,
            phone=None,
            email=None,
            address=None,
            hire_date=date.today(),
            is_active=True
        )
        
        db.session.add(employee)
        db.session.delete(dismissed)
        db.session.commit()
        
        flash(f'Сотрудник {dismissed.full_name} восстановлен! Пожалуйста, обновите его данные.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при восстановлении: {str(e)}', 'danger')
    
    return redirect(url_for('dismissed_employees'))

# ==================== ОТДЕЛЫ С ФИЛЬТРАЦИЕЙ ====================

@app.route('/departments')
@login_required
def departments():
    search = request.args.get('search', '').strip()
    parent_id = request.args.get('parent_id', type=int)
    
    query = Department.query
    
    if search:
        query = query.filter(
            db.or_(
                Department.name.like(f'%{search}%'),
                Department.code.like(f'%{search}%')
            )
        )
    
    if parent_id:
        query = query.filter_by(parent_department_id=parent_id)
    
    dept_list = query.all()
    
    all_departments = Department.query.all()
    
    return render_template('departments.html', 
                         departments=dept_list,
                         all_departments=all_departments,
                         search=search,
                         parent_id=parent_id)

@app.route('/department/add', methods=['GET', 'POST'])
@login_required
def add_department():
    if request.method == 'POST':
        try:
            department = Department(
                name=request.form['name'].strip(),
                code=request.form.get('code', '').strip() or None,
                parent_department_id=int(request.form['parent_department_id']) if request.form.get('parent_department_id') else None,
                manager_id=int(request.form['manager_id']) if request.form.get('manager_id') else None,
                description=request.form.get('description', '').strip() or None
            )
            db.session.add(department)
            db.session.commit()
            flash('Отдел добавлен!', 'success')
            return redirect(url_for('departments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    departments_list = Department.query.all()
    employees_list = Employee.query.filter_by(is_active=True).all()
    return render_template('department_form.html', department=None, departments=departments_list, employees=employees_list)

@app.route('/department/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_department(id):
    department = Department.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            department.name = request.form['name'].strip()
            department.code = request.form.get('code', '').strip() or None
            department.parent_department_id = int(request.form['parent_department_id']) if request.form.get('parent_department_id') else None
            department.manager_id = int(request.form['manager_id']) if request.form.get('manager_id') else None
            department.description = request.form.get('description', '').strip() or None
            db.session.commit()
            flash('Отдел обновлён!', 'success')
            return redirect(url_for('departments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    departments_list = Department.query.filter(Department.id != id).all()
    employees_list = Employee.query.filter_by(is_active=True).all()
    return render_template('department_form.html', department=department, departments=departments_list, employees=employees_list)

@app.route('/department/<int:id>/delete', methods=['POST'])
@login_required
def delete_department(id):
    try:
        department = Department.query.get_or_404(id)
        db.session.delete(department)
        db.session.commit()
        flash('Отдел удалён!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    return redirect(url_for('departments'))

@app.route('/department/<int:id>/view')
@login_required
def view_department(id):
    department = Department.query.get_or_404(id)
    
    employees_in_dept = db.session.query(Employee).join(
        EmployeePosition, Employee.id == EmployeePosition.employee_id
    ).join(
        Staffing, EmployeePosition.staffing_id == Staffing.id
    ).filter(
        Staffing.department_id == id,
        EmployeePosition.end_date == None,
        Employee.is_active == True
    ).all()
    
    staffing_units = Staffing.query.filter_by(department_id=id, is_active=True).all()
    
    total_employees = len(employees_in_dept)
    total_salary_fund = sum(float(s.salary * s.rate) for s in staffing_units)
    
    sub_departments = Department.query.filter_by(parent_department_id=id).all()
    
    return render_template('department_view.html', 
                         department=department,
                         employees=employees_in_dept,
                         staffing_units=staffing_units,
                         total_employees=total_employees,
                         total_salary_fund=total_salary_fund,
                         sub_departments=sub_departments)

# ==================== ДОЛЖНОСТИ С ФИЛЬТРАЦИЕЙ ====================

@app.route('/positions')
@login_required
def positions():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '')
    is_head = request.args.get('is_head', '')
    
    query = Position.query
    
    if search:
        query = query.filter(Position.name.like(f'%{search}%'))
    
    if category:
        query = query.filter_by(category=category)
    
    if is_head == 'yes':
        query = query.filter_by(is_head=True)
    elif is_head == 'no':
        query = query.filter_by(is_head=False)
    
    positions_list = query.all()
    
    return render_template('positions.html', 
                         positions=positions_list,
                         search=search,
                         category=category,
                         is_head=is_head)

@app.route('/position/add', methods=['GET', 'POST'])
@login_required
def add_position():
    if request.method == 'POST':
        try:
            position = Position(
                name=request.form['name'].strip(),
                category=request.form.get('category', 'specialist'),
                is_head='is_head' in request.form,
                base_salary=float(request.form.get('base_salary', 0)),
                requires_education='requires_education' in request.form,
                requires_experience_years=int(request.form.get('requires_experience_years', 0))
            )
            db.session.add(position)
            db.session.commit()
            flash('Должность добавлена!', 'success')
            return redirect(url_for('positions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('position_form.html', position=None)

@app.route('/position/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_position(id):
    position = Position.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            position.name = request.form['name'].strip()
            position.category = request.form.get('category', 'specialist')
            position.is_head = 'is_head' in request.form
            position.base_salary = float(request.form.get('base_salary', 0))
            position.requires_education = 'requires_education' in request.form
            position.requires_experience_years = int(request.form.get('requires_experience_years', 0))
            db.session.commit()
            flash('Должность обновлена!', 'success')
            return redirect(url_for('positions'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('position_form.html', position=position)

@app.route('/position/<int:id>/delete', methods=['POST'])
@login_required
def delete_position(id):
    try:
        position = Position.query.get_or_404(id)
        db.session.delete(position)
        db.session.commit()
        flash('Должность удалена!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    return redirect(url_for('positions'))

@app.route('/position/<int:id>/view')
@login_required
def view_position(id):
    position = Position.query.get_or_404(id)
    
    employees_in_position = db.session.query(Employee).join(
        EmployeePosition, Employee.id == EmployeePosition.employee_id
    ).join(
        Staffing, EmployeePosition.staffing_id == Staffing.id
    ).filter(
        Staffing.position_id == id,
        EmployeePosition.end_date == None,
        Employee.is_active == True
    ).all()
    
    staffing_units = Staffing.query.filter_by(position_id=id, is_active=True).all()
    
    total_employees = len(employees_in_position)
    avg_salary = 0
    if staffing_units:
        salaries = [float(s.salary) for s in staffing_units]
        avg_salary = sum(salaries) / len(salaries)
    
    return render_template('position_view.html', 
                         position=position,
                         employees=employees_in_position,
                         staffing_units=staffing_units,
                         total_employees=total_employees,
                         avg_salary=avg_salary)

# ==================== ШТАТНОЕ РАСПИСАНИЕ С ФИЛЬТРАЦИЕЙ ====================

@app.route('/staffing')
@login_required
def staffing():
    search = request.args.get('search', '').strip()
    department_id = request.args.get('department_id', type=int)
    position_id = request.args.get('position_id', type=int)
    is_active = request.args.get('is_active', '')
    
    query = Staffing.query
    
    if search:
        query = query.filter(
            db.or_(
                Staffing.department.has(Department.name.like(f'%{search}%')),
                Staffing.position.has(Position.name.like(f'%{search}%'))
            )
        )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    if position_id:
        query = query.filter_by(position_id=position_id)
    
    if is_active == 'active':
        query = query.filter_by(is_active=True)
    elif is_active == 'inactive':
        query = query.filter_by(is_active=False)
    
    staffing_list = query.all()
    
    departments = Department.query.all()
    positions = Position.query.all()
    
    return render_template('staffing.html', 
                         staffing=staffing_list,
                         departments=departments,
                         positions=positions,
                         search=search,
                         department_id=department_id,
                         position_id=position_id,
                         is_active=is_active)

@app.route('/staffing/add', methods=['GET', 'POST'])
@login_required
def add_staffing():
    if request.method == 'POST':
        try:
            staff = Staffing(
                department_id=int(request.form['department_id']),
                position_id=int(request.form['position_id']),
                rate=float(request.form.get('rate', 1.0)),
                salary=float(request.form['salary']),
                vacation_days=int(request.form.get('vacation_days', 28)),
                is_active=True
            )
            db.session.add(staff)
            db.session.commit()
            flash('Штатная единица добавлена!', 'success')
            return redirect(url_for('staffing'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    departments = Department.query.all()
    positions = Position.query.all()
    return render_template('staffing_form.html', staffing=None, departments=departments, positions=positions)

@app.route('/staffing/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_staffing(id):
    staff = Staffing.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            staff.department_id = int(request.form['department_id'])
            staff.position_id = int(request.form['position_id'])
            staff.rate = float(request.form.get('rate', 1.0))
            staff.salary = float(request.form['salary'])
            staff.vacation_days = int(request.form.get('vacation_days', 28))
            
            db.session.commit()
            flash('Штатная единица обновлена!', 'success')
            return redirect(url_for('staffing'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    departments = Department.query.all()
    positions = Position.query.all()
    return render_template('staffing_form.html', staffing=staff, departments=departments, positions=positions)

@app.route('/staffing/<int:id>/delete', methods=['POST'])
@login_required
def delete_staffing(id):
    try:
        staff = Staffing.query.get_or_404(id)
        staff.is_active = False
        db.session.commit()
        flash('Штатная единица деактивирована!', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    return redirect(url_for('staffing'))

@app.route('/assignment/add/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def add_assignment(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        try:
            staffing_id = int(request.form['staffing_id'])
            
            is_available, current_holder = check_head_position_available(staffing_id)
            
            if not is_available:
                flash(f'❌ Эта руководящая должность уже занята сотрудником {current_holder}!', 'danger')
                return redirect(url_for('add_assignment', employee_id=employee_id))
            
            assignment = EmployeePosition(
                employee_id=employee_id,
                staffing_id=staffing_id,
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                is_main='is_main' in request.form,
                contract_number=request.form.get('contract_number', '').strip() or None,
                contract_date=datetime.strptime(request.form['contract_date'], '%Y-%m-%d').date() if request.form.get('contract_date') else None
            )
            db.session.add(assignment)
            db.session.commit()
            
            auto_assign_department_head(employee_id, staffing_id)
            
            flash('Назначение добавлено!', 'success')
            return redirect(url_for('view_employee', id=employee_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    active_staffing = Staffing.query.filter_by(is_active=True).all()
    
    for staff in active_staffing:
        if staff.is_head_position():
            current_holder = staff.get_current_holder()
            staff.is_occupied = current_holder is not None
            staff.current_holder_name = current_holder.full_name() if current_holder else None
    
    return render_template('assignment_form.html', employee=employee, staffing_list=active_staffing)

@app.route('/assignment/<int:id>/delete', methods=['POST'])
@login_required
def delete_assignment(id):
    try:
        assignment = EmployeePosition.query.get_or_404(id)
        employee_id = assignment.employee_id
        staffing_id = assignment.staffing_id
        
        staffing = Staffing.query.get(staffing_id)
        
        db.session.delete(assignment)
        db.session.commit()
        
        department = Department.query.filter_by(manager_id=employee_id).first()
        if department:
            other_head_positions = db.session.query(EmployeePosition).join(Staffing).join(Position).filter(
                EmployeePosition.employee_id == employee_id,
                EmployeePosition.end_date == None,
                Position.is_head == True
            ).first()
            
            if not other_head_positions:
                department.manager_id = None
                db.session.commit()
                flash(f'Сотрудник больше не является руководителем отдела "{department.name}"', 'info')
        
        flash('Назначение удалено!', 'success')
        return redirect(url_for('view_employee', id=employee_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
        return redirect(url_for('view_employee', id=employee_id))

@app.route('/vacation/add/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def add_vacation(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            days_count = (end_date - start_date).days + 1
            
            vacation = Vacation(
                employee_id=employee_id,
                start_date=start_date,
                end_date=end_date,
                type=request.form['type'],
                days_count=days_count,
                status=request.form.get('status', 'planned')
            )
            db.session.add(vacation)
            db.session.commit()
            flash('Отпуск добавлен!', 'success')
            return redirect(url_for('view_employee', id=employee_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('vacation_form.html', employee=employee)

@app.route('/vacation/<int:id>/delete', methods=['POST'])
@login_required
def delete_vacation(id):
    try:
        vacation = Vacation.query.get_or_404(id)
        employee_id = vacation.employee_id
        db.session.delete(vacation)
        db.session.commit()
        flash('Запись об отпуске удалена!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    return redirect(url_for('view_employee', id=employee_id))

@app.route('/employee/<int:employee_id>/set_manager/<int:department_id>', methods=['POST'])
@login_required
def set_department_manager(employee_id, department_id):
    try:
        employee = Employee.query.get_or_404(employee_id)
        department = Department.query.get_or_404(department_id)
        
        department.manager_id = employee_id
        db.session.commit()
        
        flash(f'Сотрудник {employee.full_name()} назначен руководителем отдела "{department.name}"!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('departments'))

@app.route('/department/<int:department_id>/remove_manager', methods=['POST'])
@login_required
def remove_department_manager(department_id):
    try:
        department = Department.query.get_or_404(department_id)
        department.manager_id = None
        db.session.commit()
        
        flash(f'Руководитель отдела "{department.name}" удалён!', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/head-positions')
@login_required
def head_positions():
    staffing_list = Staffing.query.filter_by(is_active=True).all()
    
    head_positions = []
    for staff in staffing_list:
        if staff.is_head_position():
            holder = staff.get_current_holder()
            head_positions.append({
                'department': staff.department.name,
                'position': staff.position.name,
                'is_occupied': holder is not None,
                'holder_name': holder.full_name() if holder else None,
                'holder_id': holder.id if holder else None
            })
    
    return render_template('head_positions.html', head_positions=head_positions)

# ==================== БОЛЬНИЧНЫЕ ====================

@app.route('/sick-leaves')
@login_required
def sick_leaves():
    from datetime import date
    
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    
    query = SickLeave.query.join(Employee).filter(Employee.is_active == True)
    
    if search:
        query = query.filter(
            db.or_(
                Employee.last_name.like(f'%{search}%'),
                Employee.first_name.like(f'%{search}%'),
                SickLeave.sick_list_number.like(f'%{search}%'),
                SickLeave.diagnosis.like(f'%{search}%')
            )
        )
    
    if status == 'active':
        query = query.filter(SickLeave.end_date >= date.today())
    elif status == 'closed':
        query = query.filter(SickLeave.end_date < date.today())
    
    sick_leaves_list = query.order_by(SickLeave.start_date.desc()).all()
    
    return render_template('sick_leaves.html', 
                         sick_leaves=sick_leaves_list, 
                         search=search, 
                         status=status,
                         today=date.today())

@app.route('/sick-leave/add/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def add_sick_leave(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            if end_date < start_date:
                flash('Дата окончания не может быть раньше даты начала!', 'danger')
                return redirect(url_for('add_sick_leave', employee_id=employee_id))
            
            days_count = (end_date - start_date).days + 1
            
            existing = SickLeave.query.filter_by(sick_list_number=request.form['sick_list_number']).first()
            if existing:
                flash('Больничный лист с таким номером уже существует!', 'danger')
                return redirect(url_for('add_sick_leave', employee_id=employee_id))
            
            sick_leave = SickLeave(
                employee_id=employee_id,
                start_date=start_date,
                end_date=end_date,
                sick_list_number=request.form['sick_list_number'].strip(),
                diagnosis=request.form.get('diagnosis', '').strip(),
                doctor_name=request.form.get('doctor_name', '').strip(),
                hospital_name=request.form.get('hospital_name', '').strip(),
                days_count=days_count
            )
            db.session.add(sick_leave)
            db.session.commit()
            
            flash('Больничный лист добавлен!', 'success')
            return redirect(url_for('view_employee', id=employee_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('sick_leave_form.html', employee=employee)

@app.route('/sick-leave/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sick_leave(id):
    sick_leave = SickLeave.query.get_or_404(id)
    employee_id = sick_leave.employee_id
    
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            
            if end_date < start_date:
                flash('Дата окончания не может быть раньше даты начала!', 'danger')
                return redirect(url_for('edit_sick_leave', id=id))
            
            days_count = (end_date - start_date).days + 1
            
            existing = SickLeave.query.filter(
                SickLeave.sick_list_number == request.form['sick_list_number'],
                SickLeave.id != id
            ).first()
            if existing:
                flash('Больничный лист с таким номером уже существует!', 'danger')
                return redirect(url_for('edit_sick_leave', id=id))
            
            sick_leave.start_date = start_date
            sick_leave.end_date = end_date
            sick_leave.sick_list_number = request.form['sick_list_number'].strip()
            sick_leave.diagnosis = request.form.get('diagnosis', '').strip()
            sick_leave.doctor_name = request.form.get('doctor_name', '').strip()
            sick_leave.hospital_name = request.form.get('hospital_name', '').strip()
            sick_leave.days_count = days_count
            
            db.session.commit()
            flash('Больничный лист обновлён!', 'success')
            return redirect(url_for('view_employee', id=employee_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка: {str(e)}', 'danger')
    
    return render_template('sick_leave_form.html', sick_leave=sick_leave, employee=sick_leave.employee)

@app.route('/sick-leave/<int:id>/delete', methods=['POST'])
@login_required
def delete_sick_leave(id):
    try:
        sick_leave = SickLeave.query.get_or_404(id)
        employee_id = sick_leave.employee_id
        db.session.delete(sick_leave)
        db.session.commit()
        flash('Запись о больничном удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    
    return redirect(url_for('view_employee', id=employee_id))

@app.route('/sick-leave/close/<int:id>', methods=['POST'])
@login_required
def close_sick_leave(id):
    try:
        sick_leave = SickLeave.query.get_or_404(id)
        sick_leave.end_date = date.today()
        sick_leave.days_count = (sick_leave.end_date - sick_leave.start_date).days + 1
        db.session.commit()
        flash('Больничный лист закрыт!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    
    return redirect(url_for('view_employee', id=sick_leave.employee_id))

@app.route('/sick-leave/stats')
@login_required
def sick_leave_stats():
    from sqlalchemy import extract, func
    
    current_year = datetime.now().year
    
    monthly_stats = db.session.query(
        extract('month', SickLeave.start_date).label('month'),
        func.count(SickLeave.id).label('count'),
        func.sum(SickLeave.days_count).label('total_days')
    ).filter(
        extract('year', SickLeave.start_date) == current_year
    ).group_by('month').all()
    
    top_employees = db.session.query(
        Employee.id,
        Employee.last_name,
        Employee.first_name,
        func.count(SickLeave.id).label('sick_count'),
        func.sum(SickLeave.days_count).label('total_days')
    ).join(SickLeave).group_by(Employee.id).order_by(func.sum(SickLeave.days_count).desc()).limit(5).all()
    
    total_sick_leaves = SickLeave.query.filter(
        extract('year', SickLeave.start_date) == current_year
    ).count()
    
    total_days = db.session.query(func.sum(SickLeave.days_count)).filter(
        extract('year', SickLeave.start_date) == current_year
    ).scalar() or 0
    
    avg_days = db.session.query(func.avg(SickLeave.days_count)).filter(
        extract('year', SickLeave.start_date) == current_year
    ).scalar() or 0
    
    return render_template('sick_leave_stats.html',
                         monthly_stats=monthly_stats,
                         top_employees=top_employees,
                         total_sick_leaves=total_sick_leaves,
                         total_days=total_days,
                         avg_days=avg_days,
                         current_year=current_year)

# =====================================================
# ОТЧЁТЫ
# =====================================================

@app.route('/reports')
@login_required
def reports_index():
    return render_template('reports/index.html')

@app.route('/reports/employees-list')
@login_required
def report_employees_list():
    department_id = request.args.get('department_id', type=int)
    status = request.args.get('status', 'all')
    
    query = Employee.query
    
    if department_id:
        query = query.filter(
            Employee.id.in_(
                db.session.query(EmployeePosition.employee_id)
                .join(Staffing)
                .filter(Staffing.department_id == department_id)
            )
        )
    
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'dismissed':
        query = query.filter_by(is_active=False)
    
    employees = query.order_by(Employee.last_name).all()
    
    departments = Department.query.all()
    
    return render_template('reports/employees_list.html', 
                         employees=employees, 
                         departments=departments,
                         department_id=department_id,
                         status=status)

@app.route('/reports/salary-report')
@login_required
def report_salary():
    department_id = request.args.get('department_id', type=int)
    
    query = Staffing.query.filter_by(is_active=True)
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    staffing = query.all()
    
    total_salary = sum(float(s.salary * s.rate) for s in staffing)
    total_employees = EmployeePosition.query.filter(EmployeePosition.end_date == None).count()
    avg_salary = total_salary / total_employees if total_employees > 0 else 0
    
    dept_salary = {}
    for s in staffing:
        dept_name = s.department.name
        if dept_name not in dept_salary:
            dept_salary[dept_name] = {'salary': 0, 'employees': 0, 'rate': 0}
        dept_salary[dept_name]['salary'] += float(s.salary * s.rate)
        dept_salary[dept_name]['rate'] += float(s.rate)
    
    pos_salary = {}
    for s in staffing:
        pos_name = s.position.name
        if pos_name not in pos_salary:
            pos_salary[pos_name] = {'salary': 0, 'employees': 0, 'avg': 0, 'count': 0}
        pos_salary[pos_name]['salary'] += float(s.salary * s.rate)
        pos_salary[pos_name]['count'] += 1
        pos_salary[pos_name]['avg'] = pos_salary[pos_name]['salary'] / pos_salary[pos_name]['count']
    
    departments = Department.query.all()
    
    return render_template('reports/salary_report.html',
                         staffing=staffing,
                         departments=departments,
                         department_id=department_id,
                         total_salary=total_salary,
                         avg_salary=avg_salary,
                         total_employees=total_employees,
                         dept_salary=dept_salary,
                         pos_salary=pos_salary)

@app.route('/reports/birthday-report')
@login_required
def report_birthdays():
    month = request.args.get('month', type=int)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    query = Employee.query.filter(Employee.is_active == True, Employee.birth_date.isnot(None))
    
    if month:
        query = query.filter(extract('month', Employee.birth_date) == month)
        title = f"Дни рождения за {month} месяц"
    else:
        title = "Все дни рождения"
    
    employees = query.order_by(extract('month', Employee.birth_date), 
                                extract('day', Employee.birth_date)).all()
    
    birthdays_by_month = {i: [] for i in range(1, 13)}
    for emp in employees:
        if emp.birth_date:
            m = emp.birth_date.month
            birthdays_by_month[m].append(emp)
    
    return render_template('reports/birthday_report.html',
                         employees=employees,
                         birthdays_by_month=birthdays_by_month,
                         current_month=current_month,
                         current_year=current_year,
                         selected_month=month,
                         title=title)

@app.route('/reports/vacation-report')
@login_required
def report_vacations():
    year = request.args.get('year', type=int, default=datetime.now().year)
    department_id = request.args.get('department_id', type=int)
    
    query = Vacation.query.filter(extract('year', Vacation.start_date) == year)
    
    if department_id:
        query = query.join(Employee).join(EmployeePosition).join(Staffing).filter(
            Staffing.department_id == department_id
        )
    
    vacations = query.order_by(Vacation.start_date).all()
    
    total_vacations = len(vacations)
    total_days = sum(v.days_count for v in vacations)
    avg_days = total_days / total_vacations if total_vacations > 0 else 0
    
    by_type = {}
    for v in vacations:
        if v.type not in by_type:
            by_type[v.type] = {'count': 0, 'days': 0}
        by_type[v.type]['count'] += 1
        by_type[v.type]['days'] += v.days_count
    
    departments = Department.query.all()
    years = range(2020, datetime.now().year + 2)
    
    return render_template('reports/vacation_report.html',
                         vacations=vacations,
                         departments=departments,
                         department_id=department_id,
                         year=year,
                         years=years,
                         total_vacations=total_vacations,
                         total_days=total_days,
                         avg_days=avg_days,
                         by_type=by_type)

@app.route('/reports/sick-leave-report')
@login_required
def report_sick_leaves():
    year = request.args.get('year', type=int, default=datetime.now().year)
    department_id = request.args.get('department_id', type=int)
    
    query = SickLeave.query.filter(extract('year', SickLeave.start_date) == year)
    
    if department_id:
        query = query.join(Employee).join(EmployeePosition).join(Staffing).filter(
            Staffing.department_id == department_id
        )
    
    sick_leaves = query.order_by(SickLeave.start_date).all()
    
    total_sick = len(sick_leaves)
    total_days = sum(s.days_count for s in sick_leaves)
    avg_days = total_days / total_sick if total_sick > 0 else 0
    
    by_month = {i: {'count': 0, 'days': 0} for i in range(1, 13)}
    for sl in sick_leaves:
        m = sl.start_date.month
        by_month[m]['count'] += 1
        by_month[m]['days'] += sl.days_count
    
    diagnosis_stats = db.session.query(
        SickLeave.diagnosis,
        func.count(SickLeave.id).label('count'),
        func.sum(SickLeave.days_count).label('total_days')
    ).filter(extract('year', SickLeave.start_date) == year)\
     .group_by(SickLeave.diagnosis).order_by(func.count(SickLeave.id).desc()).limit(5).all()
    
    departments = Department.query.all()
    years = range(2020, datetime.now().year + 2)
    
    return render_template('reports/sick_leave_report.html',
                         sick_leaves=sick_leaves,
                         departments=departments,
                         department_id=department_id,
                         year=year,
                         years=years,
                         total_sick=total_sick,
                         total_days=total_days,
                         avg_days=avg_days,
                         by_month=by_month,
                         diagnosis_stats=diagnosis_stats)

@app.route('/reports/staffing-report')
@login_required
def report_staffing():
    department_id = request.args.get('department_id', type=int)
    
    query = Staffing.query.filter_by(is_active=True)
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    staffing = query.all()
    
    total_positions = len(staffing)
    total_rate = sum(float(s.rate) for s in staffing)
    
    occupied_positions = 0
    occupied_rate = 0
    
    for s in staffing:
        occupied = len([a for a in s.assignments if a.end_date is None])
        if occupied > 0:
            occupied_positions += 1
            occupied_rate += float(s.rate)
    
    departments = Department.query.all()
    
    return render_template('reports/staffing_report.html',
                         staffing=staffing,
                         departments=departments,
                         department_id=department_id,
                         total_positions=total_positions,
                         total_rate=total_rate,
                         occupied_positions=occupied_positions,
                         occupied_rate=occupied_rate)

@app.route('/reports/turnover-report')
@login_required
def report_turnover():
    year = request.args.get('year', type=int, default=datetime.now().year)
    
    hired = Employee.query.filter(extract('year', Employee.hire_date) == year).count()
    
    dismissed = Employee.query.filter(
        extract('year', Employee.dismissal_date) == year,
        Employee.is_active == False
    ).count()
    
    start_date = date(year, 1, 1)
    employees_start = Employee.query.filter(
        Employee.hire_date < start_date,
        db.or_(
            Employee.dismissal_date == None,
            Employee.dismissal_date >= start_date
        )
    ).count()
    
    avg_employees = (employees_start + (employees_start + hired - dismissed)) / 2
    turnover_rate = (dismissed / avg_employees * 100) if avg_employees > 0 else 0
    
    months = range(1, 13)
    hired_by_month = {}
    dismissed_by_month = {}
    
    for m in months:
        hired_by_month[m] = Employee.query.filter(
            extract('year', Employee.hire_date) == year,
            extract('month', Employee.hire_date) == m
        ).count()
        dismissed_by_month[m] = Employee.query.filter(
            extract('year', Employee.dismissal_date) == year,
            extract('month', Employee.dismissal_date) == m,
            Employee.is_active == False
        ).count()
    
    years = range(2020, datetime.now().year + 2)
    
    return render_template('reports/turnover_report.html',
                         year=year,
                         years=years,
                         hired=hired,
                         dismissed=dismissed,
                         employees_start=employees_start,
                         turnover_rate=turnover_rate,
                         hired_by_month=hired_by_month,
                         dismissed_by_month=dismissed_by_month)

@app.route('/reports/age-report')
@login_required
def report_age():
    employees = Employee.query.filter_by(is_active=True).all()
    
    age_groups = {
        '18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '56+': 0
    }
    
    age_list = []
    
    for emp in employees:
        if emp.birth_date:
            age = emp.age()
            if age:
                age_list.append(age)
                if 18 <= age <= 25:
                    age_groups['18-25'] += 1
                elif 26 <= age <= 35:
                    age_groups['26-35'] += 1
                elif 36 <= age <= 45:
                    age_groups['36-45'] += 1
                elif 46 <= age <= 55:
                    age_groups['46-55'] += 1
                elif age >= 56:
                    age_groups['56+'] += 1
    
    avg_age = sum(age_list) / len(age_list) if age_list else 0
    
    dept_age = {}
    for dept in Department.query.all():
        dept_employees = []
        for emp in employees:
            main_assignment = next((a for a in emp.assignments if a.is_main and a.end_date is None), None)
            if main_assignment and main_assignment.staffing.department_id == dept.id and emp.age():
                dept_employees.append(emp.age())
        if dept_employees:
            dept_age[dept.name] = sum(dept_employees) / len(dept_employees)
    
    return render_template('reports/age_report.html',
                         employees=employees,
                         age_groups=age_groups,
                         avg_age=avg_age,
                         total_employees=len(employees),
                         dept_age=dept_age)

@app.route('/reports/print/<report_name>')
@login_required
def print_report(report_name):
    from datetime import date
    
    department_id = request.args.get('department_id')
    if department_id:
        department_id = int(department_id)
    
    status = request.args.get('status', 'all')
    year = request.args.get('year')
    if year:
        year = int(year)
    
    month = request.args.get('month')
    if month:
        month = int(month)
    
    today_date = date.today()
    
    if report_name == 'employees':
        query = Employee.query
        if department_id:
            query = query.filter(
                Employee.id.in_(
                    db.session.query(EmployeePosition.employee_id)
                    .join(Staffing)
                    .filter(Staffing.department_id == department_id)
                )
            )
        if status == 'active':
            query = query.filter_by(is_active=True)
        elif status == 'dismissed':
            query = query.filter_by(is_active=False)
        
        employees = query.order_by(Employee.last_name).all()
        department_name = Department.query.get(department_id).name if department_id else 'Все'
        status_name = {'active': 'Активные', 'dismissed': 'Уволенные', 'all': 'Все'}.get(status, 'Все')
        
        return render_template('reports/print_employees.html',
                             title='Список сотрудников',
                             employees=employees,
                             filters=f"Отдел: {department_name}, Статус: {status_name}",
                             today=today_date)
    
    elif report_name == 'salary':
        query = Staffing.query.filter_by(is_active=True)
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        staffing = query.all()
        
        total_salary = sum(float(s.salary * s.rate) for s in staffing)
        total_employees = EmployeePosition.query.filter(EmployeePosition.end_date == None).count()
        avg_salary = total_salary / total_employees if total_employees > 0 else 0
        
        dept_salary = {}
        for s in staffing:
            dept_name = s.department.name
            if dept_name not in dept_salary:
                dept_salary[dept_name] = {'salary': 0, 'employees': 0}
            dept_salary[dept_name]['salary'] += float(s.salary * s.rate)
        
        department_name = Department.query.get(department_id).name if department_id else 'Все отделы'
        
        return render_template('reports/print_salary.html',
                             title='Зарплатная ведомость',
                             staffing=staffing,
                             total_salary=total_salary,
                             avg_salary=avg_salary,
                             total_employees=total_employees,
                             dept_salary=dept_salary,
                             filters=f"Отдел: {department_name}",
                             today=today_date)
    
    elif report_name == 'birthdays':
        query = Employee.query.filter(Employee.is_active == True, Employee.birth_date.isnot(None))
        if month:
            query = query.filter(extract('month', Employee.birth_date) == month)
        
        employees = query.order_by(extract('month', Employee.birth_date), 
                                    extract('day', Employee.birth_date)).all()
        
        month_name = f"{month} месяц" if month else 'Все месяцы'
        
        return render_template('reports/print_birthdays.html',
                             title='Дни рождения сотрудников',
                             employees=employees,
                             filters=f"Период: {month_name}",
                             today=today_date)
    
    elif report_name == 'vacations':
        if not year:
            year = datetime.now().year
        
        query = Vacation.query.filter(extract('year', Vacation.start_date) == year)
        if department_id:
            query = query.join(Employee).join(EmployeePosition).join(Staffing).filter(
                Staffing.department_id == department_id
            )
        
        vacations = query.order_by(Vacation.start_date).all()
        
        total_vacations = len(vacations)
        total_days = sum(v.days_count for v in vacations)
        
        department_name = Department.query.get(department_id).name if department_id else 'Все отделы'
        
        return render_template('reports/print_vacations.html',
                             title='Отчёт по отпускам',
                             vacations=vacations,
                             year=year,
                             total_vacations=total_vacations,
                             total_days=total_days,
                             filters=f"Год: {year}, Отдел: {department_name}",
                             today=today_date)
    
    elif report_name == 'sick-leaves':
        if not year:
            year = datetime.now().year
        
        query = SickLeave.query.filter(extract('year', SickLeave.start_date) == year)
        if department_id:
            query = query.join(Employee).join(EmployeePosition).join(Staffing).filter(
                Staffing.department_id == department_id
            )
        
        sick_leaves = query.order_by(SickLeave.start_date).all()
        
        total_sick = len(sick_leaves)
        total_days = sum(s.days_count for s in sick_leaves)
        
        by_month = {i: {'count': 0, 'days': 0} for i in range(1, 13)}
        for sl in sick_leaves:
            m = sl.start_date.month
            by_month[m]['count'] += 1
            by_month[m]['days'] += sl.days_count
        
        department_name = Department.query.get(department_id).name if department_id else 'Все отделы'
        
        return render_template('reports/print_sick_leaves.html',
                             title='Отчёт по больничным листам',
                             sick_leaves=sick_leaves,
                             year=year,
                             total_sick=total_sick,
                             total_days=total_days,
                             by_month=by_month,
                             filters=f"Год: {year}, Отдел: {department_name}",
                             today=today_date)
    
    elif report_name == 'staffing':
        query = Staffing.query.filter_by(is_active=True)
        if department_id:
            query = query.filter_by(department_id=department_id)
        
        staffing = query.all()
        
        total_positions = len(staffing)
        total_rate = sum(float(s.rate) for s in staffing)
        
        occupied_positions = 0
        for s in staffing:
            if len([a for a in s.assignments if a.end_date is None]) > 0:
                occupied_positions += 1
        
        department_name = Department.query.get(department_id).name if department_id else 'Все отделы'
        
        return render_template('reports/print_staffing.html',
                             title='Штатное расписание',
                             staffing=staffing,
                             total_positions=total_positions,
                             total_rate=total_rate,
                             occupied_positions=occupied_positions,
                             filters=f"Отдел: {department_name}",
                             today=today_date)
    
    elif report_name == 'turnover':
        if not year:
            year = datetime.now().year
        
        hired = Employee.query.filter(extract('year', Employee.hire_date) == year).count()
        dismissed = Employee.query.filter(
            extract('year', Employee.dismissal_date) == year,
            Employee.is_active == False
        ).count()
        
        hired_by_month = {}
        dismissed_by_month = {}
        for m in range(1, 13):
            hired_by_month[m] = Employee.query.filter(
                extract('year', Employee.hire_date) == year,
                extract('month', Employee.hire_date) == m
            ).count()
            dismissed_by_month[m] = Employee.query.filter(
                extract('year', Employee.dismissal_date) == year,
                extract('month', Employee.dismissal_date) == m,
                Employee.is_active == False
            ).count()
        
        return render_template('reports/print_turnover.html',
                             title='Текучесть кадров',
                             year=year,
                             hired=hired,
                             dismissed=dismissed,
                             hired_by_month=hired_by_month,
                             dismissed_by_month=dismissed_by_month,
                             filters=f"Год: {year}",
                             today=today_date)
    
    elif report_name == 'age':
        employees = Employee.query.filter_by(is_active=True).all()
        
        age_groups = {'18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '56+': 0}
        age_list = []
        
        for emp in employees:
            if emp.birth_date:
                age = emp.age()
                if age:
                    age_list.append(age)
                    if 18 <= age <= 25:
                        age_groups['18-25'] += 1
                    elif 26 <= age <= 35:
                        age_groups['26-35'] += 1
                    elif 36 <= age <= 45:
                        age_groups['36-45'] += 1
                    elif 46 <= age <= 55:
                        age_groups['46-55'] += 1
                    elif age >= 56:
                        age_groups['56+'] += 1
        
        avg_age = sum(age_list) / len(age_list) if age_list else 0
        
        return render_template('reports/print_age.html',
                             title='Возрастной состав персонала',
                             employees=employees,
                             age_groups=age_groups,
                             avg_age=avg_age,
                             total_employees=len(employees),
                             filters="Активные сотрудники",
                             today=today_date)
    
    return redirect(url_for('reports_index'))

# =====================================================
# ОБРАБОТЧИКИ ОШИБОК
# =====================================================

@app.errorhandler(404)
def page_not_found(error):
    """Страница 404 - страница не найдена"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(error):
    """Страница 500 - внутренняя ошибка сервера"""
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    """Страница 403 - доступ запрещён"""
    return render_template('403.html'), 403

# =====================================================
# ЗАПУСК ПЛАНИРОВЩИКА И ПРИЛОЖЕНИЯ
# =====================================================

def run_cleanup_scheduler():
    """Фоновая задача для автоматической очистки уволенных сотрудников"""
    while True:
        try:
            with app.app_context():
                cleanup_dismissed_employees()
        except Exception as e:
            print(f"Ошибка в планировщике: {e}")
        
        time.sleep(86400)

cleanup_thread = threading.Thread(target=run_cleanup_scheduler, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("⚠️ База данных пуста. Запустите python init_db.py для инициализации")
        else:
            print(f"✅ База данных готова к работе. Найдено таблиц: {len(tables)}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
