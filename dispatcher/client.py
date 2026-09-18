from __future__ import annotations

import time
import logging

import requests

BASE_URL = "http://localhost:8000"  # placeholder

logger = logging.getLogger(__name__)


def safe_request(method, url, **kwargs):
    backoff = [0.5, 1, 2]

    for delay in backoff:
        try:
            response = requests.request(method, url, **kwargs)

            # Errori HTTP 5xx → retry
            if response.status_code >= 500:
                logger.error(f"HTTP {response.status_code} su {url}, retry...")
                time.sleep(delay)
                continue

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Errore di rete su {url}: {e}, retry...")
            time.sleep(delay)

    # Dopo 3 tentativi falliti
    return None


def push_event(event_type: str, payload: dict):
    """
    Invia un evento al dispatcher (backend).
    """
    url = f"{BASE_URL}/events/push"
    data = {
        "event_type": event_type,
        "payload": payload,
    }
    response = safe_request("POST", url, json=data)
    if response is None:
        return {"status": "error", "error": "network_failure"}
    return response.json()


def fetch_event(worker_id: str):
    """
    Recupera un evento dal backend per questo worker.
    """
    url = f"{BASE_URL}/events/fetch/{worker_id}"
    response = safe_request("GET", url)
    if response is None:
        return {"status": "error", "error": "network_failure"}
    if response.status_code == 204:
        return None
    return response.json()


def ack(event_id: str):
    """
    Conferma l'elaborazione dell'evento.
    """
    url = f"{BASE_URL}/events/ack/{event_id}"
    response = safe_request("POST", url)
    if response is None:
        return {"status": "error", "error": "network_failure"}
    return response.json()


def fail(event_id: str, reason: str):
    """
    Segna l'evento come fallito.
    """
    url = f"{BASE_URL}/events/fail/{event_id}"
    data = {"reason": reason}
    response = safe_request("POST", url, json=data)
    if response is None:
        return {"status": "error", "error": "network_failure"}
    return response.json()


def requeue(event_id: str):
    """
    Rimette l'evento in coda.
    """
    url = f"{BASE_URL}/events/requeue/{event_id}"
    response = safe_request("POST", url)
    if response is None:
        return {"status": "error", "error": "network_failure"}
    return response.json()
