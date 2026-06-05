from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta  # <-- Добавлен timedelta
import os
import re

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)

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
        return True, None  # Не руководящая должность, можно назначать
    
    # Проверяем, есть ли уже активное назначение на эту должность
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
        """Проверяет, является ли должность руководящей"""
        return self.position.is_head or self.position.category in ['top_management', 'middle_management']
    
    def get_current_holder(self):
        """Возвращает текущего сотрудника, занимающего эту должность"""
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

# =====================================================
# МАРШРУТЫ
# =====================================================

@app.route('/')
def index():
    # Основная статистика
    total_employees = Employee.query.filter_by(is_active=True).count()
    total_employees_all = Employee.query.count()
    total_departments = Department.query.count()
    total_positions = Position.query.count()
    
    # Статистика по полу
    male_count = Employee.query.filter_by(gender='M', is_active=True).count()
    female_count = Employee.query.filter_by(gender='F', is_active=True).count()
    
    # Статистика по возрасту
    today = date.today()
    age_groups = {
        '18-25': 0, '26-35': 0, '36-45': 0, '46-55': 0, '55+': 0
    }
    
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
    
    # Статистика по отделам
    dept_stats = []
    for dept in Department.query.all():
        # Количество сотрудников в отделе
        employees_count = db.session.query(Employee).join(
            EmployeePosition, Employee.id == EmployeePosition.employee_id
        ).join(
            Staffing, EmployeePosition.staffing_id == Staffing.id
        ).filter(
            Staffing.department_id == dept.id,
            EmployeePosition.end_date == None,
            Employee.is_active == True
        ).count()
        
        # Фонд оплаты труда
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
    
    # Статистика по должностям
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
    
    # Статистика по занятости (штатное расписание)
    total_staffing = Staffing.query.filter_by(is_active=True).count()
    occupied_positions = EmployeePosition.query.filter(
        EmployeePosition.end_date == None
    ).count()
    
    # Руководящие должности
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
    
    # Сотрудники в отпуске сейчас
    on_vacation_now = db.session.query(Employee).join(
        Vacation, Employee.id == Vacation.employee_id
    ).filter(
        Vacation.start_date <= today,
        Vacation.end_date >= today,
        Vacation.status.in_(['planned', 'approved']),
        Employee.is_active == True
    ).count()
    
    # Сотрудники на больничном сейчас
    on_sick_leave_now = db.session.query(Employee).join(
        SickLeave, Employee.id == SickLeave.employee_id
    ).filter(
        SickLeave.start_date <= today,
        SickLeave.end_date >= today,
        Employee.is_active == True
    ).count()
    
    # Дни рождения в этом месяце
    current_month = datetime.now().month
    birthdays = Employee.query.filter(
        Employee.is_active == True,
        db.extract('month', Employee.birth_date) == current_month
    ).all()
    
    # Сотрудники в отпуске (список)
    on_vacation_list = db.session.query(Employee).join(
        Vacation, Employee.id == Vacation.employee_id
    ).filter(
        Vacation.start_date <= today,
        Vacation.end_date >= today,
        Vacation.status.in_(['planned', 'approved']),
        Employee.is_active == True
    ).limit(10).all()
    
    # Недавно принятые (последние 30 дней) - исправлено
    thirty_days_ago = today - timedelta(days=30)  # Теперь timedelta работает
    recent_hires = Employee.query.filter(
        Employee.hire_date >= thirty_days_ago,
        Employee.is_active == True
    ).order_by(Employee.hire_date.desc()).limit(10).all()
    
    # Сотрудники, у которых скоро день рождения (следующие 30 дней) - исправлено
    next_30_days = today + timedelta(days=30)
    upcoming_birthdays_list = []
    
    for emp in employees:
        if emp.birth_date:
            # Создаем дату рождения в текущем году
            birthday_this_year = date(today.year, emp.birth_date.month, emp.birth_date.day)
            if today <= birthday_this_year <= next_30_days:
                upcoming_birthdays_list.append(emp)
    
    # Список всех сотрудников для расчёта среднего возраста
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
                         
# ==================== СОТРУДНИКИ ====================

@app.route('/employees')
def employees():
    employees_list = Employee.query.order_by(Employee.last_name).all()
    return render_template('employees.html', employees=employees_list)

@app.route('/employee/add', methods=['GET', 'POST'])
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
def dismiss_employee(id):
    employee = Employee.query.get_or_404(id)
    employee.dismissal_date = date.today()
    employee.is_active = False
    
    active_assignments = EmployeePosition.query.filter_by(employee_id=id, end_date=None).all()
    for assignment in active_assignments:
        assignment.end_date = date.today()
    
    db.session.commit()
    flash('Сотрудник уволен!', 'warning')
    return redirect(url_for('employees'))

# ==================== ОТДЕЛЫ ====================

@app.route('/departments')
def departments():
    dept_list = Department.query.all()
    employees_list = Employee.query.filter_by(is_active=True).all()
    
    for emp in employees_list:
        main_assignment = EmployeePosition.query.filter_by(
            employee_id=emp.id, 
            end_date=None,
            is_main=True
        ).first()
        emp.position_name = main_assignment.staffing.position.name if main_assignment and main_assignment.staffing else 'Нет должности'
    
    return render_template('departments.html', departments=dept_list, employees=employees_list)

@app.route('/department/add', methods=['GET', 'POST'])
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

# ==================== ДОЛЖНОСТИ ====================

@app.route('/positions')
def positions():
    positions_list = Position.query.all()
    return render_template('positions.html', positions=positions_list)

@app.route('/position/add', methods=['GET', 'POST'])
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

# ==================== ШТАТНОЕ РАСПИСАНИЕ ====================

@app.route('/staffing')
def staffing():
    staffing_list = Staffing.query.filter_by(is_active=True).all()
    return render_template('staffing.html', staffing=staffing_list)

@app.route('/staffing/add', methods=['GET', 'POST'])
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

# ==================== НАЗНАЧЕНИЯ ====================

@app.route('/assignment/add/<int:employee_id>', methods=['GET', 'POST'])
def add_assignment(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    
    if request.method == 'POST':
        try:
            staffing_id = int(request.form['staffing_id'])
            
            # Проверяем, свободна ли руководящая должность
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
    
    # Отмечаем, какие должности уже заняты
    for staff in active_staffing:
        if staff.is_head_position():
            current_holder = staff.get_current_holder()
            staff.is_occupied = current_holder is not None
            staff.current_holder_name = current_holder.full_name() if current_holder else None
    
    return render_template('assignment_form.html', employee=employee, staffing_list=active_staffing)

@app.route('/assignment/<int:id>/delete', methods=['POST'])
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

# ==================== ОТПУСКА ====================

@app.route('/vacation/add/<int:employee_id>', methods=['GET', 'POST'])
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

# ==================== НАЗНАЧЕНИЕ РУКОВОДИТЕЛЯ ====================

@app.route('/employee/<int:employee_id>/set_manager/<int:department_id>', methods=['POST'])
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

# ==================== РУКОВОДЯЩИЕ ДОЛЖНОСТИ ====================

@app.route('/head-positions')
def head_positions():
    """Показывает все руководящие должности и их статус"""
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

# ==================== ПРОСМОТР ОТДЕЛА ====================

@app.route('/department/<int:id>/view')
def view_department(id):
    department = Department.query.get_or_404(id)
    
    # Сотрудники отдела
    employees_in_dept = db.session.query(Employee).join(
        EmployeePosition, Employee.id == EmployeePosition.employee_id
    ).join(
        Staffing, EmployeePosition.staffing_id == Staffing.id
    ).filter(
        Staffing.department_id == id,
        EmployeePosition.end_date == None,
        Employee.is_active == True
    ).all()
    
    # Штатные единицы отдела
    staffing_units = Staffing.query.filter_by(department_id=id, is_active=True).all()
    
    # Статистика по отделам
    total_employees = len(employees_in_dept)
    total_salary_fund = sum(float(s.salary * s.rate) for s in staffing_units)
    
    # Подчиненные отделы
    sub_departments = Department.query.filter_by(parent_department_id=id).all()
    
    return render_template('department_view.html', 
                         department=department,
                         employees=employees_in_dept,
                         staffing_units=staffing_units,
                         total_employees=total_employees,
                         total_salary_fund=total_salary_fund,
                         sub_departments=sub_departments)

# ==================== ПРОСМОТР ДОЛЖНОСТИ ====================

@app.route('/position/<int:id>/view')
def view_position(id):
    position = Position.query.get_or_404(id)
    
    # Сотрудники на этой должности
    employees_in_position = db.session.query(Employee).join(
        EmployeePosition, Employee.id == EmployeePosition.employee_id
    ).join(
        Staffing, EmployeePosition.staffing_id == Staffing.id
    ).filter(
        Staffing.position_id == id,
        EmployeePosition.end_date == None,
        Employee.is_active == True
    ).all()
    
    # Штатные единицы этой должности
    staffing_units = Staffing.query.filter_by(position_id=id, is_active=True).all()
    
    # Статистика
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

# ==================== ЗАПУСК ====================

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