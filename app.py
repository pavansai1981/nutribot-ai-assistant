import os
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-123' 

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENAI_API_KEY"))

def get_db():
    conn = sqlite3.connect('nutrition_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, age INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, user_msg TEXT, bot_msg TEXT)')
    db.commit()

init_db()

class User(UserMixin):
    def __init__(self, id, username, age):
        self.id, self.username, self.age = id, username, age

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return User(u['id'], u['username'], u['age']) if u else None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user, age = request.form.get('username'), request.form.get('age')
        pw = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password, age) VALUES (?, ?, ?)', (user, pw, age))
            db.commit()
            return redirect(url_for('login'))
        except: return "User exists!"
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        u = db.execute('SELECT * FROM users WHERE username = ?', (request.form.get('username'),)).fetchone()
        if u and bcrypt.check_password_hash(u['password'], request.form.get('password')):
            login_user(User(u['id'], u['username'], u['age']))
            return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/')
@login_required
def home():
    db = get_db()
    h = db.execute('SELECT * FROM history WHERE user_id = ?', (current_user.id,)).fetchall()
    return render_template('index.html', history=h, name=current_user.username, age=current_user.age)

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    msg = request.json.get('question')
    res = client.chat.completions.create(
        model="meta-llama/llama-3.2-3b-instruct:free",
        messages=[{"role": "system", "content": f"User is {current_user.age} years old. Give age-specific nutrition advice."}, {"role": "user", "content": msg}]
    )
    ans = res.choices[0].message.content
    db = get_db()
    db.execute('INSERT INTO history (user_id, user_msg, bot_msg) VALUES (?, ?, ?)', (current_user.id, msg, ans))
    db.commit()
    return jsonify({"answer": ans})

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)