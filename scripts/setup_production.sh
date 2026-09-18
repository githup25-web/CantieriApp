#!/bin/bash
# ============================================
# CantieriApp — Setup Produzione
# ============================================

set -e

echo "============================================"
echo "  CantieriApp — Setup Ambiente Produzione"
echo "============================================"

# 1. Verifica .env
if [ ! -f ".env" ]; then
    echo "[1/6] Creazione .env da .env.example..."
    cp .env.example .env
    echo "      ATTENZIONE: Modifica le credenziali nel file .env prima di continuare!"
else
    echo "[1/6] File .env già presente, lo uso."
fi

# 2. Crea virtualenv e installa dipendenze
echo "[2/6] Creazione virtualenv e installazione dipendenze..."
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-prod.txt

# 3. Build Docker (backend + mongodb + minio + nginx)
echo "[3/6] Build Docker Compose..."
docker-compose build

# 4. Avvio servizi
echo "[4/6] Avvio servizi Docker..."
docker-compose up -d

# 5. Verifica health check
echo "[5/6] Verifica health check..."
sleep 10
curl -s http://localhost:8000/health || echo "      Health check fallito, controlla i log."

# 6. Build APK (opzionale)
echo "[6/6] Build APK (opzionale)..."
read -p "Vuoi buildare gli APK? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Build ClienteApp..."
    cd ClienteApp && flutter build apk --release && cd ..
    echo "Build WorkerApp..."
    cd WorkerApp && flutter build apk --release && cd ..
    echo "Build CantieriApp..."
    cd CantieriApp && flutter build apk --release && cd ..
fi

echo "============================================"
echo "  Setup completato!"
echo "  API:    http://localhost:8000"
echo "  Health: http://localhost:8000/health"
echo "============================================"
