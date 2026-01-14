# Studio Medico — Gestione Appuntamenti (SQLite + SQLAlchemy + Streamlit)

Applicativo locale completo per:
- gestione **Pazienti**
- gestione **Medici**
- gestione **Appuntamenti** con controllo disponibilità (medico + sala)
- gestione **Agenda giornaliera**
- gestione **Lista d’attesa** (inserimento automatico se slot pieno)
- gestione **Notifiche** (simulate via CLI)

I diagrammi in `/progettazione` sono usati come base concettuale (dominio e relazioni).  
I file `.puml` contengono alcuni placeholder (`...`), quindi l’implementazione copre i casi d’uso principali in modo realistico.

---

## Requisiti
- Python 3
- Virtual environment già attivo: `venv_studio_medico`
- PowerShell su VSCode

---

## Installazione dipendenze

```powershell
pip install -r requirements.txt
