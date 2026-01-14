# Studio Medico — Gestione Appuntamenti (SQLite + SQLAlchemy + Streamlit)

Applicativo locale completo per:
- gestione **Pazienti**
- gestione **Medici**
- gestione **Appuntamenti** con controllo disponibilità (medico + sala)
- gestione **Agenda giornaliera**
- gestione **Lista d’attesa** (inserimento automatico se slot pieno)
- gestione **Notifiche** (simulate via CLI)

I diagrammi in `/progettazione` sono usati come base concettuale (dominio e relazioni).  
I file `.puml` contengono alcuni placeholder, l’implementazione copre i casi d’uso principali in modo realistico.

---

## Requisiti
- Python 3
- Virtual environment da attivare: `venv_studio_medico`
- PowerShell su VSCode

---

## Come far partire l'Applicativo

```powershell

cd studio_medico

# Ambiente virtuale + dipendenze
python -m venv venv_studio_medico
.\venv_studio_medico\Scripts\Activate.ps1
pip install -r requirements.txt

# configura JWT_SECRET
Copy-Item .env.example .env

# Popola DB
python -m backend.cli init
python -m backend.genera_db_ultimi_3_mesi

# Da terminale 1 - Backend
uvicorn backend.api_main:app --reload --host 127.0.0.1 --port 8000

# Da terminale 2 - Frontend
streamlit run .\streamlit_app.py