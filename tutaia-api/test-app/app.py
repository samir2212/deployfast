from flask import Flask
import os
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Tutaia Test App</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 48px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        h1 {{ font-size: 2.5rem; margin: 0 0 8px 0; }}
        p {{ opacity: 0.8; margin: 8px 0; }}
        .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>🚀 It works!</h1>
        <p>Deployed via Tutaia Platform</p>
        <p>Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        <p>Port: {os.environ.get('PORT', '8080')}</p>
        <div class="badge">ai-deploy.tutaia.com</div>
    </div>
</body>
</html>
"""

@app.route('/health')
def health():
    return {{"status": "healthy"}}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
