import datetime
from flask import Flask, render_template, redirect, session, request, jsonify
from forms import LoginForm, RegisterForm
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
) # путь к общей папке базе данных

from database import db_session, User # импорт папки БД

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key-123')


db_session.global_init("../database/game.db")


@app.route('/')
def index():
    user = None
    if 'user_id' in session:
        db_sess = db_session.create_session()
        user = db_sess.get(User, session['user_id'])
        if not user:
            session.pop('user_id', None)
    return render_template('index.html', user=user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user_ip = request.remote_addr
        try:
            geo = requests.get(f'http://ip-api.com/json/{user_ip}', timeout=3).json()
            country = geo.get('country', 'Неизвестно')
        except Exception:
            country = 'Страна неизвестна'
        f = form.photo.data
        filename = secure_filename(f.filename)
        f.save(os.path.join(app.root_path, 'static', 'img', filename))
        db_sess = db_session.create_session()
        existing_user = db_sess.query(User).filter(User.username == form.username.data).first()
        if existing_user:
            print("Занято")
            return render_template('register.html',
                                   title='Регистрация',
                                   form=form,
                                   error='Логин уже занят!')
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            username=form.username.data,
            country=country,
            photo=filename,
            active_skin=0,
            owned_skin=0,
        )
        user.hashed_password = generate_password_hash(password=form.password.data)
        db_sess.add(user)
        db_sess.commit()
        session['user_id'] = user.id
        print(user)
        return redirect('/profile')
    return render_template('register.html', title="Регистрация", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if user and check_password_hash(user.hashed_password, form.password.data):
            session['user_id'] = user.id
            return redirect('/profile')
        return render_template(
            "login.html",
            title='Вход',
            form=form,
            error='Неверный логин или пароль'
        )
    return render_template("login.html", title='Вход', form=form)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    db_sess = db_session.create_session()
    user = db_sess.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        return redirect('/login')
    return render_template('profile.html', user=user)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/api/update-stats', methods=['POST'])
def update_stats():
    data = request.json
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.username == data['username']).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.update_stats(
        kills=data.get("kills", 0),
        deaths=data.get('deaths', 0),
        bosses_defeated=data.get('bosses_defeated', 0),
        swords_hitted=data.get('swords_hitted', 0),
        swords_thrown=data.get('swords_thrown', 0),
        swords_missed=data.get('swords_missed', 0),
        total_wave=data.get('total_wave', 0),
        enemies_killed=data.get('enemies_killed', 0),
        bats_killed=data.get('bats_killed', 0),
        balance=data.get('balance', 0)
    )
    db_sess.commit()
    return jsonify({
        'status': 'ok',
        'message': 'Stats updated',
        'kills': user.kills,
        'deaths': user.deaths,
        'bosses_defeated': user.bosses_defeated,
        'swords_hitted': user.swords_hitted,
        'swords_thrown': user.swords_thrown,
        'swords_missed': user.swords_missed,
        'enemies_killed': user.enemies_killed,
        'total_wave': user.total_wave,
        'bats_killed': user.bats_killed,
        'balance': user.balance
    })

@app.route("/api/user/<username>", methods=['GET'])
def get_user_stats(username):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        'username': user.username,
        'kills': user.kills,
        'deaths': user.deaths,
        'bosses_defeated': user.bosses_defeated,
        'swords_hitted': user.swords_hitted,
        'swords_thrown': user.swords_thrown,
        'swords_missed': user.swords_missed,
        'enemies_killed': user.enemies_killed,
        'total_wave': user.total_wave,
        'bats_killed': user.bats_killed,
        'balance': user.balance,
        'active_skin': user.active_skin,
        'owned_skin': user.owned_skin
    })

@app.route("/api/game/register", methods=['POST'])
def api_register():
    """Регистрация из игры"""
    user_ip = request.remote_addr
    try:
        geo = requests.get(f'http://ip-api.com/json/{user_ip}', timeout=3).json()
        country = geo.get('country', 'Неизвестно')
        print(country)
    except Exception:
        country = 'Страна неизвестна'
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing data"}), 400
    username = data["username"].strip()
    password = data["password"]
    if len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    db_sess = db_session.create_session()
    existintg_user = db_sess.query(User).filter(User.username == username).first()
    if existintg_user:
        return jsonify({"error": "Username already exists"}), 409
    user = User(
        username=username,
        hashed_password=generate_password_hash(password),
        kills= 0,
        deaths=0,
        bosses_defeated=0,
        swords_hitted=0,
        swords_thrown=0,
        swords_missed=0,
        total_wave=0,
        enemies_killed=0,
        bats_killed=0,
        balance=0,
        country=country,
        active_skin=0,
        owned_skin=0
    )
    db_sess.add(user)
    db_sess.commit()
    return jsonify({
        "status": "ok",
        "user_id": user.id,
        "message": "User created"
    }), 201


@app.route("/api/game/login", methods=['POST'])
def api_login():
    data = request.json
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing data"}), 400
    username = data["username"].strip()
    password = data["password"]
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.username == username).first()
    if not user:
        return jsonify({"error": "Wrong login or password"}), 401
    if not check_password_hash(user.hashed_password, password):
        return jsonify({"error": "Wrong login or password"}), 401
    return jsonify({
        "status": "ok",
        "user_id": user.id,
        "username": user.username
    }), 200


@app.route("/edit-profile", methods=['GET', 'POST'])
def edit_profile():
    db_sess = db_session.create_session()
    user = db_sess.get(User, session['user_id'])
    if request.method == 'GET':
        return render_template("edit-profile.html", user=user)
    if request.method == 'POST':
        user.username = request.form.get("username", user.username)
        user.name = request.form.get("name", user.name)
        user.surname = request.form.get("surname", user.surname)
        new_password = request.form.get("new_password", '').strip()
        if new_password:
            if len(new_password) < 6:
                return render_template("edit-profile.html",
                                       user=user,
                                       error='Пароль должен быть минимум 6 символов')
            user.hashed_password = generate_password_hash(new_password)
        if 'photo' in request.files and request.files['photo'].filename:
            f = request.files['photo']
            filename = secure_filename(f.filename)
            f.save(os.path.join(app.root_path, 'static', 'img', filename))
            user.photo = filename
        user.modified_date = datetime.datetime.now()
        db_sess.commit()
        return redirect('/profile')
    return render_template("edit-profile.html", user=user)


@app.route("/profile/stats", methods=['GET'])
def profile_stats():
    if 'user_id' not in session:
        return redirect('/login')
    db_sess = db_session.create_session()
    user = db_sess.get(User, session['user_id'])
    if not user:
        session.pop('user_id', None)
        return redirect('/login')
    return render_template('profile_stat.html', user=user)


@app.route("/about/game", methods=['GET'])
def about_game():
    return render_template("about_game.html")


@app.route("/leaderboard", methods=['GET'])
def leaderboard():
    db_sess = db_session.create_session()
    users = db_sess.query(User).order_by(User.kills.desc()).limit(10).all()
    return render_template('leaderboard.html', users=users)

@app.route("/shop", methods=['GET', 'POST'])
def shop():
    if 'user_id' not in session:
        return redirect('/login')
    db_sess = db_session.create_session()
    user = db_sess.get(User, session['user_id'])
    owned = user.owned_skin
    return render_template('shop.html', user=user, owned=owned)

@app.route("/shop/buy", methods=['POST'])
def shop_buy():
    db_sess = db_session.create_session()
    if 'user_id' not in session:
        return redirect('/login')
    user = db_sess.get(User, session['user_id'])
    skin_id = request.form.get('skin_id', type=int)
    if skin_id == 1:
        if user.owned_skin == 0 and user.balance >= 1000:
            user.balance -= 1000
            user.owned_skin = 1
            db_sess.commit()
    return redirect('/shop')

@app.route("/shop/select", methods=['POST'])
def shop_select():
    db_sess = db_session.create_session()
    if 'user_id' not in session:
        return redirect('/login')
    user = db_sess.get(User, session['user_id'])
    skin_id = request.form.get('skin_id', type=int)
    if skin_id == 0:
        user.active_skin = 0
        db_sess.commit()
    if skin_id == 1:
        if user.owned_skin == 1:
            user.active_skin = 1
            db_sess.commit()
    return redirect('/shop')



if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')