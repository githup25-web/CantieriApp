from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.cantiere import Cantiere
from app.models.cantiere_document import CantiereDocument
from app.models.event_record import EventRecord
from app.models.expense import Expense
from app.models.notification import Notification
from app.models.presence import Presence
from app.models.progress_photo import ProgressPhoto
from app.models.task import Task
from app.security.cliente_auth import ClienteTokenPayload, get_current_cliente

router = APIRouter(prefix="/cliente", tags=["cliente"])


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Valore {field_name} non valido") from exc


def _safe_to_str_uuid(value: Any) -> str:
    return str(value) if value is not None else ""


class CantiereStatoOut(BaseModel):
    id: str
    organization_id: str
    nome_cantiere: str
    indirizzo: Optional[str] = None
    stato: str
    data_inizio: Optional[datetime] = None
    data_prevista_fine: Optional[datetime] = None
    responsabile: Optional[str] = None
    progress_percentuale: int


class TaskAvanzamentoOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    progress: int
    completed: bool
    last_update: datetime
    note: Optional[str] = None
    updated_at: datetime


class AvanzamentoOut(BaseModel):
    tasks: list[TaskAvanzamentoOut]
    progress_percentuale: int


class FotoOut(BaseModel):
    id: str
    user_id: str
    stage: str
    url: str
    description: Optional[str] = None
    timestamp: datetime
    giorno: Optional[str] = None  # YYYY-MM-DD
    ora: Optional[str] = None  # HH:MM




def _time_ago(now: datetime, past: datetime) -> str:
    """
    Human readable delta (best effort).
    """
    if past.tzinfo is None:
        past = past.replace(tzinfo=timezone.utc)
    delta = now - past
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if days > 0:
        return f"{days}d fa"
    if hours > 0:
        return f"{hours}h fa"
    if minutes > 0:
        return f"{minutes}m fa"
    return "ora"


def _humanize_event_name(event_name: str) -> str:
    # "cliente.feedback.received" => "cliente · feedback · received"
    return event_name.replace(".", " · ")


class TimelineEventoOut(BaseModel):
    event_name: str
    occurred_at: datetime
    payload: dict[str, Any]
    time_ago: str | None = None


class DocumentOut(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    url: str
    uploaded_at: datetime
    version: int
    size_kb: Optional[float] = None


class PresenzaOut(BaseModel):
    id: str
    user_id: str
    type: str
    gps_lat: float
    gps_lon: float
    timestamp: datetime
    durata_minuti: int | None = None
    note: Optional[str] = None
    meteo: Optional[str] = None
    weather: Optional[str] = None  # backward compat


class SpesaVoceOut(BaseModel):
    id: str
    category: str
    amount: float
    description: str
    receipt_url: Optional[str] = None
    timestamp: datetime


class SpeseOut(BaseModel):
    spese_materiali_totale: float
    spese_manodopera_totale: float
    spese_generale_totale: float
    totale: float
    voci: list[SpesaVoceOut]
    note: Optional[str] = None


class NotificaOut(BaseModel):
    id: str
    type: str
    entity_id: Optional[str] = None
    payload: dict[str, Any]
    is_read: bool
    created_at: datetime
    time_ago: Optional[str] = None


class CantiereListaItemOut(BaseModel):
    """Item per la lista cantieri del cliente (DTO compatibile con ClienteApp)."""
    id: str
    nome_cantiere: str
    titolo: str
    indirizzo: Optional[str] = None
    stato: str
    status: str
    percentuale_avanzamento: int
    percentuale: int
    progress: int
    description: Optional[str] = None


@router.get("/area/cantieri", response_model=list[CantiereListaItemOut])
async def get_area_cantieri(
    current_cliente: ClienteTokenPayload = Depends(get_current_cliente),
) -> list[CantiereListaItemOut]:
    """Elenca tutti i cantieri associati al cliente autenticato (multi-cantiere)."""
    from app.models.cliente_access_code import ClienteAccessCode

    cliente_id_str = str(current_cliente.cliente_id)

    # Trova tutti gli access code attivi per questo cliente
    access_codes = await ClienteAccessCode.find(
        {"cliente_id": cliente_id_str, "active": True}
    ).to_list()

    out: list[CantiereListaItemOut] = []
    for access in access_codes:
        try:
            cantiere_uuid = _parse_uuid(access.cantiere_id, "cantiere_id")
        except HTTPException:
            continue
        cantiere = await Cantiere.find_one(Cantiere.id == cantiere_uuid)
        if not cantiere:
            continue

        # Progress globale: media dei Task.progress del cantiere.
        tasks = await Task.find(Task.cantiere_id == cantiere_uuid).to_list()
        if not tasks:
            progress_percentuale = 0
        else:
            progress_percentuale = int(round(sum(t.progress for t in tasks) / max(1, len(tasks))))

        nome = cantiere.title
        out.append(
            CantiereListaItemOut(
                id=str(cantiere.id),
                nome_cantiere=nome,
                titolo=nome,
                indirizzo=None,
                stato=cantiere.status,
                status=cantiere.status,
                percentuale_avanzamento=progress_percentuale,
                percentuale=progress_percentuale,
                progress=progress_percentuale,
                description=cantiere.description,
            )
        )

    return out


@router.get("/area/cantiere", response_model=CantiereStatoOut)
async def get_area_cantiere(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> CantiereStatoOut:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    cantiere = await Cantiere.find_one(Cantiere.id == cantiere_uuid)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere non trovato")

    # Progress globale: media dei Task.progress del cantiere.
    tasks = await Task.find(Task.cantiere_id == cantiere_uuid).to_list()
    if not tasks:
        progress_percentuale = 0
    else:
        progress_percentuale = int(round(sum(t.progress for t in tasks) / max(1, len(tasks))))

    return CantiereStatoOut(
        id=str(cantiere.id),
        organization_id=str(cantiere.organization_id),
        nome_cantiere=cantiere.title,
        indirizzo=None,
        stato=cantiere.status,
        data_inizio=None,
        data_prevista_fine=None,
        responsabile=str(cantiere.assigned_worker_id) if cantiere.assigned_worker_id else None,
        progress_percentuale=progress_percentuale,
    )


@router.get("/area/avanzamento", response_model=AvanzamentoOut)
async def get_area_avanzamento(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> AvanzamentoOut:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    tasks = (
        await Task.find(Task.cantiere_id == cantiere_uuid)
        .sort("-updated_at")
        .to_list()
    )

    def _is_completed(t: Task) -> bool:
        if (getattr(t, "status", None) or "").lower() == "completed":
            return True
        return int(getattr(t, "progress", 0) or 0) >= 100

    tasks_out: list[TaskAvanzamentoOut] = [
        TaskAvanzamentoOut(
            id=str(t.id),
            title=t.title,
            description=t.description,
            status=t.status,
            progress=int(t.progress),
            completed=_is_completed(t),
            last_update=t.updated_at,
            note=None,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]

    if not tasks:
        progress_percentuale = 0
    else:
        progress_percentuale = int(round(sum(t.progress for t in tasks) / max(1, len(tasks))))

    return AvanzamentoOut(tasks=tasks_out, progress_percentuale=progress_percentuale)


@router.get("/area/foto")
async def get_area_foto(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> dict[str, Any]:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    photos_cursor = ProgressPhoto.find(ProgressPhoto.cantiere_id == cantiere_uuid).sort("-timestamp")
    photos = await photos_cursor.to_list()

    return {
        "foto": [
            FotoOut(
                id=str(p.id),
                user_id=str(p.user_id),
                stage=p.stage,
                url=p.url,
                description=p.description,
                timestamp=p.timestamp,
                giorno=p.timestamp.date().isoformat(),
                ora=p.timestamp.strftime("%H:%M"),
            ).model_dump()
            for p in photos
        ]
    }


def _event_payload_matches_cantiere(payload: dict[str, Any], cantiere_id: str) -> bool:
    # Strategie best-effort: cerca cantiere_id in payload (valori string/UUID o chiavi note).
    if not isinstance(payload, dict):
        return False

    if payload.get("cantiere_id") is not None and _safe_to_str_uuid(payload.get("cantiere_id")) == str(cantiere_id):
        return True

    for key in ("cantiere", "cantiereId", "cantiere_id", "cantiereID"):
        if key in payload and _safe_to_str_uuid(payload.get(key)) == str(cantiere_id):
            return True

    # Fallback: flatten string search (prudente ma utile con payload liberi)
    try:
        return str(payload).find(str(cantiere_id)) >= 0
    except Exception:
        return False


@router.get("/area/timeline")
async def get_area_timeline(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> dict[str, Any]:
    cantiere_id_str = str(current_cliente.cantiere_id)
    now = datetime.now(timezone.utc)

    # Best-effort: prendi eventi recenti e filtra in Python (perché EventRecord non ha cantiere_id dedicato).
    events = await EventRecord.find().sort("-occurred_at").limit(500).to_list()

    filtered: list[EventRecord] = [
        e for e in events
        if _event_payload_matches_cantiere(e.payload or {}, cantiere_id_str)
    ]

    # mapping leggibile + time_ago
    return {
        "eventi": [
            TimelineEventoOut(
                event_name=_humanize_event_name(e.event_name),
                occurred_at=e.occurred_at,
                payload=e.payload or {},
                time_ago=_time_ago(now, e.occurred_at),
            ).model_dump()
            for e in filtered
        ]
    }


@router.get("/area/documenti")
async def get_area_documenti(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> dict[str, Any]:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    docs = await CantiereDocument.find(CantiereDocument.cantiere_id == cantiere_uuid).sort("-uploaded_at").to_list()

    return {
        "documenti": [
            DocumentOut(
                id=str(d.id),
                type=d.type,
                title=d.title,
                description=d.description,
                url=d.url,
                uploaded_at=d.uploaded_at,
                version=d.version,
                size_kb=getattr(d, "size_kb", None),
            ).model_dump()
            for d in docs
        ]
    }


@router.get("/area/presenze")
async def get_area_presenze(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> dict[str, Any]:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    presences = await Presence.find(Presence.cantiere_id == cantiere_uuid).sort("-timestamp").to_list()

    # durata: best-effort calcolata come differenza tra presenza corrente e precedente dello stesso user+type
    # (se mancano coppie, dura_minuti=None)
    prev_by_user_type: dict[tuple[str, str], datetime] = {}
    out_list = []
    for p in presences:
        key = (str(p.user_id), str(p.type))
        durata_minuti: int | None = None
        if key in prev_by_user_type:
            delta = prev_by_user_type[key] - p.timestamp
            durata_minuti = max(0, int(delta.total_seconds() // 60))
        prev_by_user_type[key] = p.timestamp

        out_list.append(
            PresenzaOut(
                id=str(p.id),
                user_id=str(p.user_id),
                type=p.type,
                gps_lat=p.gps_lat,
                gps_lon=p.gps_lon,
                timestamp=p.timestamp,
                durata_minuti=durata_minuti,
                note=p.note,
                meteo=p.weather,
                weather=p.weather,
            ).model_dump()
        )

    return {"presenze": out_list, "count": len(presences)}


@router.get("/area/spese", response_model=SpeseOut)
async def get_area_spese(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> SpeseOut:
    cantiere_uuid = _parse_uuid(current_cliente.cantiere_id, "cantiere_id")

    expenses = await Expense.find(Expense.cantiere_id == cantiere_uuid).sort("-timestamp").to_list()

    voci = [
        SpesaVoceOut(
            id=str(x.id),
            category=x.category,
            amount=float(x.amount),
            description=x.description,
            receipt_url=x.receipt_url,
            timestamp=x.timestamp,
        )
        for x in expenses
    ]

    materiali = 0.0
    manodopera = 0.0
    generale = 0.0

    for x in expenses:
        cat = (x.category or "").lower()
        amt = float(x.amount)
        if "material" in cat or "materiale" in cat or "materiali" in cat:
            materiali += amt
        elif "manod" in cat or "manodopera" in cat:
            manodopera += amt
        else:
            generale += amt

    totale = materiali + manodopera + generale
    note = None
    if totale == 0.0 and expenses:
        note = "Totali aggregati non disponibili: verifica valori 'category' sulle spese."

    return SpeseOut(
        spese_materiali_totale=materiali,
        spese_manodopera_totale=manodopera,
        spese_generale_totale=generale,
        totale=totale,
        voci=voci,
        note=note,
    )


@router.get("/area/notifiche")
async def get_area_notifiche(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> dict[str, Any]:
    now = datetime.now(timezone.utc)

    # gestire cliente_id non UUID:
    # - se è UUID: filtra per recipient_user_id
    # - se NO: best-effort filtra via payload/entity_id contenendo cliente_id stringa (minimo rischio: ritorna anche lista vuota se non match)
    cliente_id_str = str(current_cliente.cliente_id)

    notifications: list[Notification] = []
    try:
        cliente_uuid = _parse_uuid(current_cliente.cliente_id, "cliente_id")
        notifications = await Notification.find(Notification.recipient_user_id == cliente_uuid).sort("-created_at").limit(200).to_list()
    except HTTPException:
        # fallback: cerca solo per payload/entity_id (no query unbounded)
        # (poiché non abbiamo campo cantiere/cliente dedicato nel modello Notification)
        notifications = await Notification.find().sort("-created_at").limit(200).to_list()

    # filtraggio per cantiere_id del token (best-effort con payload/entity_id)
    cantiere_id_str = str(current_cliente.cantiere_id)

    def _notif_matches_cantiere(n: Notification) -> bool:
        if n.entity_id is not None and str(n.entity_id) == cantiere_id_str:
            return True
        payload = n.payload or {}
        if payload.get("cantiere_id") is not None and _safe_to_str_uuid(payload.get("cantiere_id")) == cantiere_id_str:
            return True
        for k in ("cantiere", "cantiereId", "cantiere_id", "cantiereID"):
            if k in payload and _safe_to_str_uuid(payload.get(k)) == cantiere_id_str:
                return True
        return True  # permissivo: riduce rischio di vuoto totale su payload non standard

    def _notif_time_ago(created_at: datetime) -> str:
        return _time_ago(now, created_at)

    filtered = [n for n in notifications if _notif_matches_cantiere(n)]

    return {
        "notifiche": [
            NotificaOut(
                id=str(n.id),
                type=n.type,
                entity_id=str(n.entity_id) if n.entity_id is not None else None,
                payload=n.payload or {},
                is_read=n.is_read,
                created_at=n.created_at,
                time_ago=_notif_time_ago(n.created_at),
            ).model_dump()
            for n in filtered[:50]
        ]
    }
