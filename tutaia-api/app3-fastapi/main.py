from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import os

app = FastAPI(title="Quote of the Day", version="1.0.0")

quotes = [
    {"id": 1, "text": "The best way to predict the future is to create it.", "author": "Peter Drucker"},
    {"id": 2, "text": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
    {"id": 3, "text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
]
next_id = 4

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <title>Quote Board</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 700px; margin: 50px auto; padding: 20px; background: #1a1a2e; color: #eee; }}
    h1 {{ color: #e94560; font-size: 2em; }}
    .subtitle {{ color: #a0aec0; margin-bottom: 30px; font-family: Arial; }}
    .quote-card {{ background: #16213e; border-left: 4px solid #e94560; padding: 20px; margin-bottom: 15px; border-radius: 0 8px 8px 0; }}
    .quote-text {{ font-size: 1.1em; line-height: 1.6; margin-bottom: 10px; }}
    .quote-author {{ color: #e94560; font-style: italic; font-family: Arial; font-size: 0.9em; }}
    form {{ display: flex; flex-direction: column; gap: 10px; background: #16213e; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
    input, textarea {{ padding: 10px; background: #0f3460; border: 1px solid #e94560; color: white; border-radius: 6px; font-size: 15px; }}
    button {{ padding: 12px; background: #e94560; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold; }}
    .count {{ color: #a0aec0; font-family: Arial; font-size: 14px; }}
  </style>
</head>
<body>
  <h1>💬 Quote Board</h1>
  <p class="subtitle">Deployed via Tutaia Platform &bull; FastAPI + Python</p>
  <form action="/add" method="post">
    <input name="text" placeholder="Enter a quote..." required>
    <input name="author" placeholder="Author name..." required>
    <button type="submit">Add Quote</button>
  </form>
  {quotes_html}
  <p class="count">{count} quote{plural} in the board</p>
</body>
</html>
"""

def render_quotes(quotes_list):
    html = ""
    for q in reversed(quotes_list):
        html += f'''
        <div class="quote-card">
          <div class="quote-text">"{q["text"]}"</div>
          <div class="quote-author">— {q["author"]}</div>
        </div>'''
    return html

@app.get("/", response_class=HTMLResponse)
async def home():
    count = len(quotes)
    return HTML_TEMPLATE.format(
        quotes_html=render_quotes(quotes),
        count=count,
        plural="s" if count != 1 else ""
    )

@app.post("/add")
async def add_quote(text: str = Form(...), author: str = Form(...)):
    global next_id
    quotes.append({"id": next_id, "text": text.strip(), "author": author.strip()})
    next_id += 1
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/quotes")
async def get_quotes():
    return {"count": len(quotes), "quotes": quotes}

@app.get("/health")
async def health():
    return {"status": "ok", "app": "quote-board", "quotes": len(quotes)}
