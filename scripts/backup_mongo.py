"""Script di backup MongoDB per CantieriApp.

Esegue un dump del database MongoDB in una directory timestamped.
Usage:
    python scripts/backup_mongo.py [--db cantieriapp] [--uri mongodb://localhost:27017] [--output ./backups]
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup MongoDB per CantieriApp")
    parser.add_argument("--db", default="cantieriapp", help="Nome del database")
    parser.add_argument("--uri", default="mongodb://localhost:27017", help="URI MongoDB")
    parser.add_argument("--output", default="./backups", help="Directory di output")
    args = parser.parse_args()

    # Crea directory di output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp per il backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = output_dir / f"{args.db}_{timestamp}"

    print(f"Avvio backup del database '{args.db}'...")
    print(f"Output: {backup_path}")

    # Esegui mongodump
    cmd = [
        "mongodump",
        f"--uri={args.uri}",
        f"--db={args.db}",
        f"--out={str(backup_path)}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERRORE: {result.stderr}", file=sys.stderr)
            return 1
        print("Backup completato con successo!")
        print(result.stdout)
        return 0
    except FileNotFoundError:
        print(
            "ERRORE: 'mongodump' non trovato. Assicurati che MongoDB Tools sia installato.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
