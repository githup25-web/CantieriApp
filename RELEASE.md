# CantieriApp — Guida al Rilascio (FASE 9)

## 1. Panoramica

Questo documento descrive i passi per il rilascio in produzione del sistema CantieriApp, composto da:

- **Backend**: FastAPI + MongoDB (Beanie) + MinIO (S3) + nginx (reverse proxy)
- **3 App Flutter** (Android APK):
  - `ClienteApp` — per i clienti
  - `WorkerApp` — per gli operai/worker
  - `CantieriApp` — per la gestione (admin/PM)

---

## 2. Prerequisiti

| Tool | Versione consigliata |
|------|---------------------|
| Python | 3.11+ |
| Flutter | 3.x (con Android SDK) |
| Java | Android Studio JBR (JAVA_HOME) |
| Docker | 20+ (con docker-compose) |
| MongoDB Tools | Ultima (per `mongodump`) |

---

## 3. Build Backend

### 3.1 Configurazione variabili ambiente

Copia `.env.example` in `.env` e modifica le credenziali:

```
bash
cp .env.example .env
```

Variabili principali:
```
APP_ENVIRONMENT=production
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=cantieriapp
JWT_SECRET_KEY=<genera-un-secret-forte>
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=<access-key>
MINIO_SECRET_KEY=<secret-key>
MINIO_PUBLIC_URL=https://s3.tuodominio.com
FIREBASE_CREDENTIALS_PATH=/path/to/firebase.json
CORS_ORIGINS=["https://app.tuodominio.com"]
LOG_LEVEL=INFO
```

### 3.2 Installazione dipendenze

```
bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-prod.txt
```

### 3.3 Avvio locale

```
bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health`

---

## 4. Build APK (Android)

Per ogni app, il build usa `--dart-define` per l'URL dell'API:

```
bash
# ClienteApp
cd ClienteApp
flutter build apk --release --dart-define=API_BASE_URL=https://api.tuodominio.com

# WorkerApp
cd ../WorkerApp
flutter build apk --release --dart-define=API_BASE_URL=https://api.tuodominio.com

# CantieriApp
cd ../CantieriApp
flutter build apk --release --dart-define=API_BASE_URL=https://api.tuodominio.com
```

APK generati in:
```
<App>/build/app/outputs/flutter-apk/app-release.apk
```

---

## 5. Deploy con Docker Compose

### 5.1 Configurazione

1. Crea `.env` (come al punto 3.1)
2. Modifica `nginx.conf` con il tuo dominio

### 5.2 Avvio

```
bash
docker-compose build
docker-compose up -d
```

Servizi:
- MongoDB: `localhost:27017`
- MinIO: `localhost:9000` (console: `9001`)
- Backend: `localhost:8000`
- Nginx: `localhost:80` / `443`

### 5.3 Verifica

```
bash
curl http://localhost:8000/health
```

---

## 6. Backup

### Backup MongoDB

```
bash
python scripts/backup_mongo.py --db cantieriapp --uri mongodb://localhost:27017 --output ./backups
```

I backup vengono salvati in `./backups/cantieriapp_<timestamp>/`.

### Setup automatico

```bash
./scripts/setup_production.sh
```

Lo script:
1. Crea `.env` da `.env.example`
2. Crea virtualenv e installa dipendenze
3. Build Docker Compose
4. Avvia i servizi
5. Verifica health check
6. (Opzionale) Builda gli APK

---

## 7. Test

### Backend (pytest)

```
bash
python -m pytest
```

Risultato atteso: **42 test passati**.

### Flutter analyze (3 app)

```bash
cd ClienteApp && flutter analyze
cd WorkerApp && flutter analyze
cd CantieriApp && flutter analyze
```

Tutte e 3 devono avere **0 errori** (solo info-level lint).

### Flusso E2E

Il flusso **create cliente → assign cantiere → login → view data** è coperto dai test in `app/tests/test_cliente.py`:
- `TestCreateCliente` — creazione cliente
- `TestAssignCantiere` — assegnazione cantiere
- `TestClientLogin` — login con codice
- `TestGetCantieri` / `TestAreaCantieri` — visualizzazione dati

---

## 8. Riepilogo Artefatti di Rilascio

| Componente | Artefatto |
|------------|-----------|
| Backend | `Dockerfile`, `docker-compose.yml`, `requirements-prod.txt` |
| Reverse Proxy | `nginx.conf` |
| Config | `.env.example`, `app/core/config.py` |
| Backup | `scripts/backup_mongo.py` |
| Setup | `scripts/setup_production.sh` |
| ClienteApp APK | `ClienteApp/build/app/outputs/flutter-apk/app-release.apk` |
| WorkerApp APK | `WorkerApp/build/app/outputs/flutter-apk/app-release.apk` |
| CantieriApp APK | `CantieriApp/build/app/outputs/flutter-apk/app-release.apk` |

---

## 9. Note di Rilascio

- Le build APK sono state generate con successo (release mode).
- `flutter analyze` per le 3 app: **0 errori** (solo lint informative non bloccanti).
- 42 test pytest passati.
- Il flusso E2E cliente è verificato dai test automatici.
- La configurazione di produzione usa `--dart-define` per l'URL API nelle app Flutter, e variabili d'ambiente `.env` per il backend.
