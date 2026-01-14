# Studio Medico - Gestione Appuntamenti

Sistema completo per la gestione di uno studio medico con prenotazioni online, agenda medici, gestione pazienti e notifiche automatiche.

**Stack tecnologico:**
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: Streamlit
- Autenticazione: JWT
- Database: SQLite (locale)

## Funzionalità principali

- ✅ **Gestione Pazienti**: anagrafica completa con dati di contatto
- ✅ **Gestione Medici**: profili medici e disponibilità
- ✅ **Prenotazione Appuntamenti**: controllo disponibilità medico e sala con durata dinamica per tipo visita
- ✅ **Agenda Giornaliera**: visualizzazione appuntamenti per medico e giorno
- ✅ **Lista d'Attesa**: inserimento automatico quando lo slot è occupato
- ✅ **Notifiche**: sistema di notifiche per conferme e promemoria
- ✅ **Autenticazione JWT**: protezione delle sezioni sensibili

---

## Requisiti

- Python 3.8+
- PowerShell (per Windows)
- Git

---

## Installazione

### 1. Clona il repository

```powershell
git clone https://github.com/Robert0Falcon1/studio_medico.git
cd studio_medico
```

### 2. Crea ambiente virtuale

```powershell
python -m venv venv_studio_medico
.\venv_studio_medico\Scripts\Activate.ps1
```

### 3. Installa le dipendenze

```powershell
pip install -r requirements.txt
```

### 4. Configura le variabili d'ambiente

Rinomina file `.env-example` in `.env` e imposta una chiave segreta sicura per JWT:

### 5. Inizializza il database

```powershell
# Crea schema e dati base
python -m backend.cli init

# (Opzionale) Popola con dati realistici degli ultimi 90 giorni
python -m backend.genera_db_ultimi_3_mesi
```

---

## Avvio dell'applicazione

Avvia backend e frontend in **due terminali separati**:

### Terminale 1 - Backend API

```powershell
uvicorn backend.api_main:app --reload --host 127.0.0.1 --port 8000
```

### Terminale 2 - Frontend Streamlit

```powershell
streamlit run .\streamlit_app.py
```

### URL principali

**Frontend:**
- Streamlit: http://localhost:8501

**Backend:**
- API base: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## Guida all'uso

### Registrazione e Login

#### 1. Registra un nuovo utente (API)

```powershell
$body = @{ username = "admin"; password = "Password123!" } | ConvertTo-Json -Compress
Set-Content -Encoding ascii .\register.json $body

curl.exe -s -X POST "http://127.0.0.1:8000/api/auth/register" `
  -H "Content-Type: application/json" `
  --data-binary "@register.json"
```

Risposta attesa:
```json
{"ok": true, "user_id": "..."}
```

#### 2. Effettua login e ottieni token JWT

```powershell
$login = curl.exe -s -X POST "http://127.0.0.1:8000/api/auth/login" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=admin&password=Password123!"

$token = (($login | ConvertFrom-Json).access_token).Trim()
$token.Length
```

#### 3. Testa endpoint protetto

```powershell
curl.exe -s -X GET "http://127.0.0.1:8000/api/protected/ping" `
  -H "Authorization: Bearer $token"
```

---

## Funzionalità Frontend (Streamlit)

### Tab 1: Prenotazioni (Pubblico)

Permette a chiunque di prenotare un appuntamento:

1. Seleziona **Medico**, **Sala**, **Tipo visita**, **Data** e **Ora**
2. Scegli il **Paziente** dall'elenco
3. Aggiungi eventuali **Note**
4. Abilita "**Lista d'attesa**" se desiderato (in caso di slot occupato)
5. Clicca **Conferma prenotazione**

**Comportamento:**
- Se lo slot è **disponibile**: crea appuntamento CONFERMATO + notifica CONFERMA
- Se lo slot è **occupato** e lista d'attesa abilitata: inserisce in lista d'attesa + notifica PROMEMORIA

### Tab 2: Agenda Medico (Protetto 🔒)

Visualizza l'agenda giornaliera di un medico:

1. Effettua il **login** (se richiesto)
2. Seleziona il **Medico**
3. Seleziona il **Giorno**
4. Visualizza gli appuntamenti con:
   - Orario inizio/fine
   - Tipo visita
   - Sala
   - Stato
   - Note

### Tab 3: Pazienti (Protetto 🔒)

Gestione dell'anagrafica pazienti:

1. Effettua il **login** (se richiesto)
2. Clicca **"Crea nuovo paziente"**
3. Inserisci:
   - Nome e Cognome (obbligatori)
   - Email (opzionale)
   - Telefono (opzionale)
4. Visualizza l'elenco completo dei pazienti registrati

### Tab 4: Notifiche (Protetto 🔒)

Visualizza le notifiche pendenti:

1. Effettua il **login** (se richiesto)
2. Visualizza tutte le notifiche non ancora inviate

Formato: `[ID] TIPO | Paziente: Cognome Nome - messaggio`

Le notifiche vengono create automaticamente per:
- Conferme prenotazioni
- Inserimenti in lista d'attesa
- Eventuali annullamenti/promozioni

---

## API REST

### Documentazione interattiva

Accedi a **Swagger UI** per testare le API: http://127.0.0.1:8000/docs

### Endpoint principali

#### Autenticazione
- `POST /api/auth/register` - Registrazione utente (JSON)
- `POST /api/auth/login` - Login utente (form-urlencoded)

#### Protetti (richiedono JWT)
- `GET /api/protected/ping` - Test autenticazione
- `GET /api/notifiche/pendenti?limit=10` - Lista notifiche pendenti

---

## Comandi CLI

### Inizializzazione database

```powershell
python -m backend.cli init
```

### Popolamento dati realistici (ultimi 90 giorni)

```powershell
python -m backend.genera_db_ultimi_3_mesi
```

### Visualizza percorso database

```powershell
python -m backend.tools.show_db_path
```

### Simulazione invio notifiche (marca come inviate)

```powershell
python -m backend.cli notifications --mark-sent
```

---

## Reset Database

Per ripartire da zero:

```powershell
Remove-Item .\studio_medico.sqlite
python -m backend.cli init
python -m backend.genera_db_ultimi_3_mesi
```

⚠️ **Attenzione**: Questa operazione elimina tutti i dati, inclusi gli utenti registrati.

---

## Troubleshooting

### Token JWT non valido in PowerShell

Verifica che `$token` non sia vuoto:

```powershell
$token.Length
```

Se il risultato è 0, ripeti la procedura di login.

### "Credenziali non valide" dopo reset DB

Dopo aver cancellato `studio_medico.sqlite`, devi registrare nuovamente gli utenti.

### Dati mancanti nella sezione Prenotazioni

Se non ci sono pazienti disponibili:
- Crea un paziente dal tab "Pazienti" (richiede login)
- Oppure esegui: `python -m backend.genera_db_ultimi_3_mesi`

### Cambio JWT_SECRET

Se modifichi `JWT_SECRET` in `.env`, tutti i token precedentemente emessi diventano invalidi (comportamento normale per sicurezza).

---

## Struttura del Progetto

```
studio_medico/
├── backend/
│   ├── __init__.py              
│   ├── api_main.py                 # FastAPI: auth JWT + endpoints
│   ├── auth_models.py              # Modelli autenticazione
│   ├── auth_security.py            # Utility sicurezza JWT
│   ├── auth_service.py             # Servizi autenticazione
│   ├── cli.py                      # Comandi CLI
│   ├── db.py                       # Engine + session
│   ├── genera_db_ultimi_3_mesi.py  # Popolamento realistico
│   ├── models.py                   # ORM SQLAlchemy
│   ├── seed.py                     # Dati iniziali
│   └── services.py                 # Logica applicativa
├── progettazione/                  # Diagrammi .puml e .bpmn
├── streamlit_app.py                # Frontend Streamlit
├── requirements.txt                # Dipendenze Python
├── .env.example                    # Template configurazione
├── .gitignore                      # File esclusi da Git
└── README.md                       # Questa guida
```

---

## Tecnologie Utilizzate

- **FastAPI** - Framework web asincrono per API REST
- **SQLAlchemy** - ORM per gestione database
- **SQLite** - Database embedded
- **Streamlit** - Framework per interfacce web interattive
- **JWT** - JSON Web Tokens per autenticazione
- **Pydantic** - Validazione dati
- **python-jose** - Gestione JWT
- **passlib** - Hashing password
- **bcrypt** - Algoritmo di hashing sicuro

---

## Contributi

I contributi sono benvenuti! Per segnalare bug o proporre miglioramenti, apri una issue su GitHub.

---

## Licenza

Questo progetto è distribuito sotto licenza MIT.

---

## Autore

- GitHub: [@Robert0Falcon1](https://github.com/Robert0Falcon1)

---

## Note di Sicurezza

- ⚠️ **Mai committare `.env`** su repository pubblici
- 🔒 Usa password complesse per gli utenti
- 🔑 Cambia `JWT_SECRET` in produzione con una chiave casuale di almeno 32 caratteri
- 💾 Effettua backup regolari del database `studio_medico.sqlite`