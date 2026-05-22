# HomeNet – Internet Monitor

A real-time internet monitoring dashboard built with Flask.

## Files
```
homenet/
├── app.py               # Flask backend + monitor
├── requirements.txt     # Python dependencies
├── render.yaml          # Render deployment config
└── templates/
    └── index.html       # Dark dashboard UI
```

## Run Locally
```bash
pip install flask
python app.py
```
Open http://localhost:5000

## Deploy to Render (free)

1. Push this folder to a GitHub repo
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects render.yaml and deploys
5. Your live link will be: https://homenet.onrender.com
