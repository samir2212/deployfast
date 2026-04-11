from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "/tmp/tasks.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT NOT NULL,
                     done BOOLEAN DEFAULT FALSE)''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return '''
    <html>
    <head><title>Task Manager</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f0f4f8; }
        h1 { color: #2d3748; }
        form { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 10px; border: 1px solid #cbd5e0; border-radius: 6px; }
        button { padding: 10px 20px; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; }
        ul { list-style: none; padding: 0; }
        li { background: white; padding: 15px; margin-bottom: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .done { text-decoration: line-through; color: #a0aec0; }
        .badge { background: #48bb78; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; }
    </style>
    </head>
    <body>
        <h1>✅ Task Manager</h1>
        <p style="color:#718096">Deployed via Tutaia Platform</p>
        <form action="/tasks" method="post">
            <input name="title" placeholder="Add a new task..." required>
            <button type="submit">Add Task</button>
        </form>
        <ul id="tasks">
        {% for task in tasks %}
            <li>
                <span class="{{ "done" if task["done"] else "" }}">{{ task["title"] }}</span>
                <span class="badge">{{ "Done" if task["done"] else "Pending" }}</span>
            </li>
        {% endfor %}
        </ul>
    </body>
    </html>
    '''.replace('{% for task in tasks %}', '').replace('{% endfor %}', '')

@app.route('/')
def home():
    db = get_db()
    tasks = db.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    db.close()
    from flask import render_template_string
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head><title>Task Manager</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f0f4f8; }
        h1 { color: #2d3748; }
        form { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 10px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 16px; }
        button { padding: 10px 20px; background: #4299e1; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
        ul { list-style: none; padding: 0; }
        li { background: white; padding: 15px; margin-bottom: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    </style>
    </head>
    <body>
        <h1>✅ Task Manager</h1>
        <p style="color:#718096">Deployed via Tutaia Platform</p>
        <form action="/tasks" method="post">
            <input name="title" placeholder="Add a new task..." required>
            <button type="submit">Add Task</button>
        </form>
        <ul>
        {% for task in tasks %}
            <li>
                <span>{{ task["title"] }}</span>
                <span style="background:#48bb78;color:white;padding:4px 10px;border-radius:20px;font-size:12px;">Pending</span>
            </li>
        {% endfor %}
        {% if not tasks %}
            <li style="color:#a0aec0;justify-content:center;">No tasks yet. Add one above!</li>
        {% endif %}
        </ul>
    </body>
    </html>
    ''', tasks=tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    from flask import redirect
    title = request.form.get('title', '').strip()
    if title:
        db = get_db()
        db.execute('INSERT INTO tasks (title) VALUES (?)', (title,))
        db.commit()
        db.close()
    return redirect('/')

@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    db = get_db()
    tasks = db.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    db.close()
    return jsonify([dict(t) for t in tasks])

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

init_db()
