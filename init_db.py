import os
import pymysql
from app import app, db
from sqlalchemy import inspect, text
from datetime import datetime

# Конфигурация подключения к MySQL (без указания БД)
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST') or 'localhost',
    'user': os.environ.get('MYSQL_USER') or 'root',
    'password': os.environ.get('MYSQL_PASSWORD') or '',
    'charset': 'utf8mb4'
}

DB_NAME = os.environ.get('MYSQL_DB') or 'hr_system'


def create_database_if_not_exists():
    """Проверяет существование базы данных и создаёт её при необходимости"""
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"📁 База данных '{DB_NAME}' не найдена. Создаём...")
            cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ База данных '{DB_NAME}' успешно создана!")
        else:
            print(f"✅ База данных '{DB_NAME}' уже существует")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке/создании базы данных: {e}")
        return False


def update_gender_column():
    """Обновляет структуру поля gender, делая его обязательным"""
    try:
        connection = pymysql.connect(**DB_CONFIG, database=DB_NAME)
        cursor = connection.cursor()
        
        cursor.execute("SHOW TABLES LIKE 'employees'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("\n🔧 Обновление структуры поля gender...")
            
            cursor.execute("SHOW COLUMNS FROM employees LIKE 'gender'")
            column_info = cursor.fetchone()
            
            if column_info and column_info[1] != "enum('M','F')":
                cursor.execute("SELECT COUNT(*) FROM employees WHERE gender IS NULL")
                null_count = cursor.fetchone()[0]
                
                if null_count > 0:
                    print(f"📝 Найдено {null_count} записей с неуказанным полом. Устанавливаем значение по умолчанию 'M'...")
                    cursor.execute("UPDATE employees SET gender = 'M' WHERE gender IS NULL")
                    print(f"✅ Обновлено {null_count} записей")
                
                cursor.execute("ALTER TABLE employees MODIFY COLUMN gender ENUM('M', 'F') NOT NULL")
                print("✅ Поле gender теперь обязательное (NOT NULL)")
            else:
                print("✅ Поле gender уже имеет правильную структуру")
            
            connection.commit()
        else:
            print("⚠️ Таблица employees не найдена, пропускаем обновление gender")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении поля gender: {e}")
        return False


def add_is_head_column():
    """Добавляет колонку is_head в таблицу positions, если её нет"""
    try:
        connection = pymysql.connect(**DB_CONFIG, database=DB_NAME)
        cursor = connection.cursor()
        
        cursor.execute("SHOW TABLES LIKE 'positions'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("\n🔧 Проверка структуры таблицы positions...")
            
            cursor.execute("SHOW COLUMNS FROM positions LIKE 'is_head'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                print("📝 Добавление колонки is_head в таблицу positions...")
                cursor.execute("ALTER TABLE positions ADD COLUMN is_head BOOLEAN DEFAULT FALSE")
                print("✅ Колонка is_head добавлена")
                
                print("📝 Обновление руководящих должностей...")
                cursor.execute("UPDATE positions SET is_head = 1 WHERE category IN ('top_management', 'middle_management')")
                print("✅ Руководящие должности отмечены")
            else:
                print("✅ Колонка is_head уже существует")
            
            connection.commit()
        else:
            print("⚠️ Таблица positions не найдена, пропускаем добавление is_head")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении колонки is_head: {e}")
        return False


def update_sick_leaves_table():
    """Добавляет колонки doctor_name и hospital_name в таблицу sick_leaves, если их нет"""
    try:
        connection = pymysql.connect(**DB_CONFIG, database=DB_NAME)
        cursor = connection.cursor()
        
        cursor.execute("SHOW TABLES LIKE 'sick_leaves'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("\n🔧 Проверка структуры таблицы sick_leaves...")
            
            # Добавляем колонку doctor_name
            cursor.execute("SHOW COLUMNS FROM sick_leaves LIKE 'doctor_name'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                print("📝 Добавление колонки doctor_name в таблицу sick_leaves...")
                cursor.execute("ALTER TABLE sick_leaves ADD COLUMN doctor_name VARCHAR(200) AFTER diagnosis")
                print("✅ Колонка doctor_name добавлена")
            else:
                print("✅ Колонка doctor_name уже существует")
            
            # Добавляем колонку hospital_name
            cursor.execute("SHOW COLUMNS FROM sick_leaves LIKE 'hospital_name'")
            column_exists = cursor.fetchone()
            
            if not column_exists:
                print("📝 Добавление колонки hospital_name в таблицу sick_leaves...")
                cursor.execute("ALTER TABLE sick_leaves ADD COLUMN hospital_name VARCHAR(200) AFTER doctor_name")
                print("✅ Колонка hospital_name добавлена")
            else:
                print("✅ Колонка hospital_name уже существует")
            
            connection.commit()
        else:
            print("⚠️ Таблица sick_leaves не найдена, пропускаем обновление")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении таблицы sick_leaves: {e}")
        return False


def table_exists(table_name):
    """Проверяет существование таблицы в базе данных"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def get_tables_status():
    """Возвращает статус всех таблиц"""
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    
    all_tables = ['employees', 'departments', 'positions', 'staffing', 
                  'employee_positions', 'orders', 'vacations', 'sick_leaves', 
                  'salary_history', 'education', 'dismissed_employees']
    
    status = {}
    for table in all_tables:
        status[table] = table in existing_tables
    
    return status


def init_database():
    """Основная функция инициализации базы данных"""
    print("\n" + "="*50)
    print("🚀 Инициализация базы данных HR системы")
    print("="*50 + "\n")
    
    # Шаг 1: Проверка и создание БД
    if not create_database_if_not_exists():
        print("❌ Не удалось создать базу данных. Проверьте подключение к MySQL.")
        return False
    
    # Шаг 2: Создание таблиц через SQLAlchemy
    with app.app_context():
        print("\n📋 Проверка структуры базы данных...")
        
        tables_before = get_tables_status()
        existing_count = sum(tables_before.values())
        
        if existing_count > 0:
            print(f"📊 Найдено существующих таблиц: {existing_count}/11")
            for table, exists in tables_before.items():
                status = "✅" if exists else "❌"
                print(f"  {status} {table}")
        
        print("\n🔧 Создание/обновление структуры таблиц...")
        db.create_all()
        
        tables_after = get_tables_status()
        created_count = sum(tables_after.values())
        
        print(f"\n📊 Итоговое состояние: {created_count}/11 таблиц")
        for table, exists in tables_after.items():
            status = "✅" if exists else "❌"
            print(f"  {status} {table}")
        
        if created_count == 11:
            print("\n🎉 Все таблицы успешно созданы!")
        else:
            print(f"\n⚠️ Создано только {created_count} из 11 таблиц")
    
    # Шаг 3: Обновление структуры поля gender
    update_gender_column()
    
    # Шаг 4: Добавление колонки is_head в positions
    add_is_head_column()
    
    # Шаг 5: Добавление колонок в sick_leaves
    update_sick_leaves_table()
    
    # Шаг 6: Проверка наличия тестовых данных
    with app.app_context():
        print("\n📊 Проверка тестовых данных...")
        
        from app import Employee, Department, Position, Staffing, Vacation, SickLeave, DismissedEmployee
        
        employees_count = Employee.query.count()
        if employees_count == 0:
            print("📝 Добавление тестовых данных...")
            add_test_data()
        else:
            print(f"✅ Найдено {employees_count} сотрудников в базе")
            
            print("\n🔍 Проверка руководящих должностей...")
            update_head_positions()


def update_head_positions():
    """Обновляет статус руководящих должностей на основе категорий"""
    try:
        from app import Position
        
        Position.query.filter(
            Position.category.in_(['top_management', 'middle_management'])
        ).update({Position.is_head: True}, synchronize_session=False)
        
        db.session.commit()
        print("✅ Статус руководящих должностей обновлён")
        
        head_positions = Position.query.filter_by(is_head=True).all()
        if head_positions:
            print(f"\n📋 Руководящие должности ({len(head_positions)}):")
            for pos in head_positions:
                print(f"  👔 {pos.name} ({pos.category})")
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении руководящих должностей: {e}")
        db.session.rollback()


def add_test_data():
    """Добавляет тестовые данные в базу"""
    from app import (Employee, Department, Position, Staffing, EmployeePosition, 
                     Vacation, SickLeave, DismissedEmployee, db)
    
    try:
        # Добавление должностей (с полем is_head)
        positions_data = [
            ('Генеральный директор', 'top_management', True, 300000, 10),
            ('Финансовый директор', 'top_management', True, 250000, 8),
            ('Технический директор', 'top_management', True, 250000, 8),
            ('Начальник отдела', 'middle_management', True, 150000, 5),
            ('Ведущий программист', 'specialist', False, 120000, 3),
            ('Программист', 'specialist', False, 80000, 1),
            ('Бухгалтер', 'specialist', False, 70000, 2),
            ('Инженер', 'specialist', False, 75000, 2),
            ('Оператор ПК', 'worker', False, 45000, 0),
            ('Уборщица', 'worker', False, 30000, 0),
        ]
        
        positions = {}
        for name, category, is_head, salary, exp in positions_data:
            pos = Position.query.filter_by(name=name).first()
            if not pos:
                pos = Position(
                    name=name,
                    category=category,
                    is_head=is_head,
                    base_salary=salary,
                    requires_experience_years=exp
                )
                db.session.add(pos)
                db.session.flush()
            positions[name] = pos
        print("  ✅ Должности добавлены")
        
        # Добавление отделов
        depts_data = [
            ('Управление', 'D00', None),
            ('Финансовый отдел', 'D01', 1),
            ('IT-отдел', 'D02', 1),
            ('Технический отдел', 'D03', 1),
            ('Отдел кадров', 'D04', 1),
        ]
        
        departments = {}
        for name, code, parent_id in depts_data:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, code=code)
                if parent_id:
                    dept.parent_department_id = parent_id
                db.session.add(dept)
                db.session.flush()
            departments[name] = dept
        print("  ✅ Отделы добавлены")
        
        db.session.commit()
        
        # Обновляем parent_department_id после фиксации
        for name, code, parent_name in [('Финансовый отдел', 'D01', 'Управление'),
                                         ('IT-отдел', 'D02', 'Управление'),
                                         ('Технический отдел', 'D03', 'Управление'),
                                         ('Отдел кадров', 'D04', 'Управление')]:
            dept = Department.query.filter_by(name=name).first()
            if dept and dept.parent_department_id is None:
                parent = Department.query.filter_by(name=parent_name).first()
                if parent:
                    dept.parent_department_id = parent.id
        db.session.commit()
        
        # Добавление сотрудников
        employees_data = [
            ('Иванов', 'Иван', 'Иванович', '1980-05-15', 'M', '+7-999-123-4567', 'ivanov@company.com', '2010-03-01'),
            ('Петрова', 'Мария', 'Сергеевна', '1985-08-20', 'F', '+7-999-234-5678', 'petrova@company.com', '2012-06-15'),
            ('Сидоров', 'Алексей', 'Владимирович', '1990-12-10', 'M', '+7-999-345-6789', 'sidorov@company.com', '2015-01-20'),
            ('Козлова', 'Елена', 'Андреевна', '1988-03-25', 'F', '+7-999-456-7890', 'kozlova@company.com', '2018-09-10'),
            ('Смирнов', 'Дмитрий', 'Петрович', '1995-07-30', 'M', '+7-999-567-8901', 'smirnov@company.com', '2020-02-14'),
            ('Васильева', 'Ольга', 'Николаевна', '1992-11-11', 'F', '+7-999-678-9012', 'vasilyeva@company.com', '2019-03-25'),
            ('Павлов', 'Павел', 'Павлович', '1982-09-05', 'M', '+7-999-789-0123', 'pavlov@company.com', '2008-12-01'),
        ]
        
        employees = []
        for last, first, middle, birth, gender, phone, email, hire in employees_data:
            emp = Employee.query.filter_by(email=email).first()
            if not emp:
                emp = Employee(
                    last_name=last,
                    first_name=first,
                    middle_name=middle,
                    birth_date=datetime.strptime(birth, '%Y-%m-%d').date(),
                    gender=gender,
                    phone=phone,
                    email=email,
                    hire_date=datetime.strptime(hire, '%Y-%m-%d').date(),
                    is_active=True
                )
                db.session.add(emp)
                db.session.flush()
            employees.append(emp)
        print("  ✅ Сотрудники добавлены")
        
        db.session.commit()
        
        # Добавление штатного расписания
        staffing_data = [
            (departments['Управление'], positions['Генеральный директор'], 1.0, 300000, 35),
            (departments['Управление'], positions['Финансовый директор'], 1.0, 250000, 32),
            (departments['Управление'], positions['Технический директор'], 1.0, 250000, 32),
            (departments['Финансовый отдел'], positions['Начальник отдела'], 1.0, 150000, 30),
            (departments['Финансовый отдел'], positions['Бухгалтер'], 2.0, 70000, 28),
            (departments['IT-отдел'], positions['Начальник отдела'], 1.0, 150000, 30),
            (departments['IT-отдел'], positions['Ведущий программист'], 2.0, 120000, 28),
            (departments['IT-отдел'], positions['Программист'], 3.0, 80000, 28),
            (departments['Технический отдел'], positions['Инженер'], 2.0, 75000, 28),
            (departments['Отдел кадров'], positions['Начальник отдела'], 1.0, 130000, 30),
        ]
        
        staffing_units = []
        for dept, pos, rate, salary, vacation_days in staffing_data:
            staff = Staffing.query.filter_by(department_id=dept.id, position_id=pos.id).first()
            if not staff:
                staff = Staffing(
                    department_id=dept.id,
                    position_id=pos.id,
                    rate=rate,
                    salary=salary,
                    vacation_days=vacation_days,
                    is_active=True
                )
                db.session.add(staff)
                db.session.flush()
            staffing_units.append(staff)
        print("  ✅ Штатное расписание добавлено")
        
        db.session.commit()
        
        # Добавление назначений
        assignments_data = [
            (employees[0], staffing_units[0], '2010-03-01', True),
            (employees[1], staffing_units[1], '2012-06-15', True),
            (employees[2], staffing_units[2], '2015-01-20', True),
            (employees[3], staffing_units[3], '2018-09-10', True),
            (employees[4], staffing_units[6], '2020-02-14', True),
            (employees[5], staffing_units[7], '2019-03-25', True),
            (employees[6], staffing_units[5], '2008-12-01', True),
        ]
        
        for emp, staff, start_date, is_main in assignments_data:
            existing = EmployeePosition.query.filter_by(
                employee_id=emp.id, 
                staffing_id=staff.id,
                end_date=None
            ).first()
            if not existing:
                assignment = EmployeePosition(
                    employee_id=emp.id,
                    staffing_id=staff.id,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                    is_main=is_main,
                    contract_number=f"ТД-{emp.id:03d}"
                )
                db.session.add(assignment)
        print("  ✅ Назначения добавлены")
        
        db.session.commit()
        
        # Автоматическое назначение руководителей отделов
        print("  👔 Назначение руководителей отделов...")
        
        management_dept = departments['Управление']
        gen_dir_staff = staffing_units[0]
        gen_dir_assignment = EmployeePosition.query.filter_by(staffing_id=gen_dir_staff.id, end_date=None).first()
        if gen_dir_assignment:
            management_dept.manager_id = gen_dir_assignment.employee_id
            print(f"    - Управление: {gen_dir_assignment.employee.full_name()} (Генеральный директор)")
        
        head_mappings = [
            ('Финансовый отдел', 'Начальник отдела'),
            ('IT-отдел', 'Начальник отдела'),
            ('Отдел кадров', 'Начальник отдела'),
        ]
        
        for dept_name, pos_name in head_mappings:
            department = Department.query.filter_by(name=dept_name).first()
            position = Position.query.filter_by(name=pos_name).first()
            
            if department and position:
                staff = Staffing.query.filter_by(department_id=department.id, position_id=position.id).first()
                if staff:
                    emp_pos = EmployeePosition.query.filter_by(staffing_id=staff.id, end_date=None).first()
                    if emp_pos:
                        department.manager_id = emp_pos.employee_id
                        print(f"    - {dept_name}: {emp_pos.employee.full_name()} ({pos_name})")
        
        db.session.commit()
        
        # Добавление отпусков
        vacations_data = [
            (employees[0], '2024-06-01', '2024-06-28', 'annual', 'approved'),
            (employees[1], '2024-07-10', '2024-07-24', 'annual', 'approved'),
            (employees[2], '2024-08-05', '2024-08-19', 'annual', 'planned'),
            (employees[4], '2024-05-15', '2024-05-29', 'additional', 'approved'),
        ]
        
        for emp, start, end, vtype, status in vacations_data:
            existing = Vacation.query.filter_by(
                employee_id=emp.id,
                start_date=datetime.strptime(start, '%Y-%m-%d').date()
            ).first()
            if not existing:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.strptime(end, '%Y-%m-%d').date()
                days_count = (end_date - start_date).days + 1
                vacation = Vacation(
                    employee_id=emp.id,
                    start_date=start_date,
                    end_date=end_date,
                    type=vtype,
                    days_count=days_count,
                    status=status
                )
                db.session.add(vacation)
        print("  ✅ Отпуска добавлены")
        
        # Добавление больничных (с новыми полями)
        sick_leaves_data = [
            (employees[3], '2024-03-10', '2024-03-15', 'SL-2024-001', 'ОРВИ', 'Иванова А.А.', 'Городская поликлиника №1'),
            (employees[5], '2024-04-20', '2024-04-25', 'SL-2024-002', 'Грипп', 'Петров Б.Б.', 'Областная больница'),
        ]
        
        for emp, start, end, number, diagnosis, doctor, hospital in sick_leaves_data:
            existing = SickLeave.query.filter_by(sick_list_number=number).first()
            if not existing:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.strptime(end, '%Y-%m-%d').date()
                days_count = (end_date - start_date).days + 1
                sick = SickLeave(
                    employee_id=emp.id,
                    start_date=start_date,
                    end_date=end_date,
                    sick_list_number=number,
                    diagnosis=diagnosis,
                    doctor_name=doctor,
                    hospital_name=hospital,
                    days_count=days_count
                )
                db.session.add(sick)
        print("  ✅ Больничные добавлены")
        
        db.session.commit()
        print("\n🎉 Все тестовые данные успешно добавлены!")
        
        print("\n📊 Статистика:")
        print(f"  👥 Сотрудников: {Employee.query.count()}")
        print(f"  🏢 Отделов: {Department.query.count()}")
        print(f"  💼 Должностей: {Position.query.count()}")
        print(f"  📋 Штатных единиц: {Staffing.query.count()}")
        print(f"  🔗 Назначений: {EmployeePosition.query.count()}")
        print(f"  🌴 Отпусков: {Vacation.query.count()}")
        print(f"  🤒 Больничных: {SickLeave.query.count()}")
        print(f"  🗑️ Уволенных сотрудников в очереди: {DismissedEmployee.query.count()}")
        
        print("\n👔 Руководители отделов:")
        for dept in Department.query.all():
            if dept.manager:
                print(f"  - {dept.name}: {dept.manager.full_name()}")
            else:
                print(f"  - {dept.name}: Не назначен")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Ошибка при добавлении тестовых данных: {e}")
        import traceback
        traceback.print_exc()
        raise


def reset_database():
    """Полный сброс базы данных (удаляет и создаёт заново)"""
    print("\n⚠️ ВНИМАНИЕ! Это удалит ВСЕ данные в базе данных!")
    confirm = input("Вы уверены? (введите 'yes' для подтверждения): ")
    
    if confirm.lower() != 'yes':
        print("❌ Операция отменена")
        return False
    
    with app.app_context():
        print("🗑️ Удаление всех таблиц...")
        db.drop_all()
        print("✅ Все таблицы удалены")
        
        print("🔧 Создание таблиц заново...")
        db.create_all()
        print("✅ Таблицы созданы")
    
    update_gender_column()
    add_is_head_column()
    update_sick_leaves_table()
    
    with app.app_context():
        print("📝 Добавление тестовых данных...")
        add_test_data()
        
        print("\n🎉 База данных полностью пересоздана!")
        return True


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        init_database()
        
        print("\n" + "="*50)
        print("✨ Инициализация завершена!")
        print("="*50)
        print("\nДля запуска приложения выполните:")
        print("  python app.py")
        print("\nДля просмотра руководящих должностей:")
        print("  http://localhost:5000/head-positions")
        print("\nДля просмотра уволенных сотрудников:")
        print("  http://localhost:5000/dismissed-employees")
        print("\nДля просмотра больничных:")
        print("  http://localhost:5000/sick-leaves")
        print("\nДля полного сброса базы данных:")
        print("  python init_db.py --reset")