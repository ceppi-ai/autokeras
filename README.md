# InnovaCoach App

Applicazione Flask con login Google OAuth e strumenti di coaching con storico personale.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configura variabili ambiente:

```bash
export FLASK_SECRET_KEY="una-chiave-forte"
export GOOGLE_CLIENT_ID="..."
export GOOGLE_CLIENT_SECRET="..."
```

Su Google Cloud Console aggiungi l'URI di redirect:

- `http://localhost:5000/authorize`

## Avvio

```bash
python app.py
```

Poi apri `http://localhost:5000`.
