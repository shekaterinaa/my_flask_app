from flask import Flask, request, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from models import db, User, Expense, AuditLog
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "1111"  
user_db = "katya"
host_ip = "localhost"
host_port = "5432"
database_name = "expense"
password = "34567"

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'goforaccount'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def main():
    return render_template('main.html', name=current_user.name)

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == "POST":
        email = request.form['email']
        password = generate_password_hash(request.form['password']) 
        name = request.form['name']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('registration.html', error="Такой аккаунт существует")

        new_user = User(email=email, password=password, name=name)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/goforaccount')

    return render_template("registration.html")

@app.route('/goforaccount', methods=['GET', 'POST'])
def goforaccount():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, password):  # Проверяем хешированный пароль
            return render_template('goforaccount.html', error="Неправильный email или пароль")

        login_user(user)
        return redirect('/')

    return render_template('goforaccount.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/goforaccount')

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        data = request.form
        new_expense = Expense(
            user_id=current_user.id,
            amount=data['amount'],
            category=data['category'],
            description=data['description']
        )
        db.session.add(new_expense)
        db.session.commit()

        # Логирование действий
        log_action(current_user.id, 'добавление', new_expense.id)
        flash("Расход добавлен!", "success")
        return redirect(url_for('list_expenses'))

    return render_template('add.html')

@app.route('/list', methods=['GET'])
@login_required
def list_expenses():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    return render_template('list.html', expenses=expenses)

@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == 'POST':
        data = request.form
        # Проверка наличия ключей в данных формы
        if 'amount' in data and 'category' in data:
            expense.amount = data['amount']
            expense.category = data['category']
            expense.description = data.get('description', '')  
            db.session.commit()

            # Логирование действий
            log_action(current_user.id, 'изменение', expense.id)
            flash("Запись обновлена!", "success")
            return redirect(url_for('list_expenses'))
        else:
            flash("Пожалуйста, заполните все поля.", "danger")
    
    return render_template('edit.html', expense=expense)


@app.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    db.session.delete(expense)
    db.session.commit()

    # Логирование действий
    log_action(current_user.id, 'удаление', expense.id)
    flash("Запись удалена!", "success")
    return redirect(url_for('list_expenses'))

# Функция логирования действий
def log_action(user_id, action_type, record_id):
    new_log = AuditLog(user_id=user_id, action_type=action_type, record_id=record_id)
    db.session.add(new_log)
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создание базовых таблиц при запуске
    app.run(debug=True)



