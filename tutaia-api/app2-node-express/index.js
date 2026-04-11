const express = require('express');
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// In-memory store
const notes = [
  { id: 1, text: "Welcome to your notes app!", createdAt: new Date().toISOString() }
];
let nextId = 2;

app.get('/', (req, res) => {
  const notesList = notes.map(n => `
    <li style="background:white;padding:15px;margin-bottom:10px;border-radius:6px;box-shadow:0 1px 3px rgba(0,0,0,0.1);display:flex;justify-content:space-between;align-items:center;">
      <span>${n.text}</span>
      <small style="color:#a0aec0">${new Date(n.createdAt).toLocaleTimeString()}</small>
    </li>`).join('');

  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Notes App</title>
      <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; background: #f7fafc; }
        h1 { color: #2d3748; }
        form { display: flex; gap: 10px; margin-bottom: 20px; }
        input { flex: 1; padding: 10px; border: 1px solid #cbd5e0; border-radius: 6px; font-size: 16px; }
        button { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; }
        ul { list-style: none; padding: 0; }
        .badge { background: #667eea; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; }
      </style>
    </head>
    <body>
      <h1>📝 Notes App</h1>
      <p style="color:#718096">Deployed via Tutaia Platform &bull; Node.js + Express</p>
      <form action="/notes" method="POST">
        <input name="text" placeholder="Write a note..." required>
        <button type="submit">Save</button>
      </form>
      <ul>${notesList}</ul>
      <p style="color:#a0aec0;font-size:14px">${notes.length} note${notes.length !== 1 ? 's' : ''} total</p>
    </body>
    </html>
  `);
});

app.post('/notes', (req, res) => {
  const text = (req.body.text || '').trim();
  if (text) {
    notes.unshift({ id: nextId++, text, createdAt: new Date().toISOString() });
  }
  res.redirect('/');
});

app.get('/api/notes', (req, res) => {
  res.json({ count: notes.length, notes });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Notes app running on port ${PORT}`);
});
