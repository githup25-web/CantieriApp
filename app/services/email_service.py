from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("cantieriapp.email")


def _build_deep_link(email: str, otp: str) -> str:
    """Costruisce il deep link myapp://verify?email={email}&otp={otp}"""
    scheme = settings.app_deep_link_scheme
    enc_email = quote(email, safe="")
    return f"{scheme}://verify?email={enc_email}&otp={otp}"


def _build_html_email(full_name: str, otp: str, expires_minutes: int, deep_link: str) -> str:
    """Template HTML dell'email di verifica."""
    return f"""\
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verifica il tuo account CantieriApp</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f8;padding:20px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="background-color:#1e3a5f;padding:24px;text-align:center;">
              <h1 style="color:#ffffff;margin:0;font-size:24px;">CantieriApp</h1>
              <p style="color:#c7d5e0;margin:4px 0 0;font-size:14px;">Verifica del tuo account</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="color:#333333;font-size:16px;margin:0 0 16px;">Ciao {full_name or "utente"},</p>
              <p style="color:#555555;font-size:14px;line-height:1.6;margin:0 0 24px;">
                Grazie per esserti registrato su CantieriApp. Per completare la registrazione,
                inserisci il codice di verifica qui sotto. Il codice è valido per
                <strong>{expires_minutes} minuti</strong>.
              </p>
              <!-- OTP Box -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center" style="background-color:#f0f4f8;border-radius:8px;padding:24px;border:2px dashed #1e3a5f;">
                    <span style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1e3a5f;">{otp}</span>
                  </td>
                </tr>
              </table>
              <p style="color:#555555;font-size:14px;line-height:1.6;margin:0 0 16px;">
                Oppure tocca il pulsante qui sotto per completare la verifica automaticamente:
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{deep_link}" style="background-color:#1e3a5f;color:#ffffff;padding:14px 32px;border-radius:6px;text-decoration:none;font-size:16px;font-weight:bold;display:inline-block;">
                      Verifica il mio account
                    </a>
                  </td>
                </tr>
              </table>
              <p style="color:#888888;font-size:12px;line-height:1.6;margin:0;">
                Se non hai richiesto questa verifica, ignora questa email. Il codice non verrà
                utilizzato e scadrà automaticamente.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color:#f0f4f8;padding:16px;text-align:center;">
              <p style="color:#888888;font-size:12px;margin:0;">© 2025 CantieriApp. Tutti i diritti riservati.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _build_text_email(full_name: str, otp: str, expires_minutes: int, deep_link: str) -> str:
    """Versione testo semplice dell'email."""
    return f"""\
Ciao {full_name or "utente"},

Grazie per esserti registrato su CantieriApp. Per completare la registrazione,
inserisci il seguente codice di verifica:

  {otp}

Il codice è valido per {expires_minutes} minuti.

Oppure apri questo link per completare la verifica automaticamente:
{deep_link}

Se non hai richiesto questa verifica, ignora questa email.

— Il team di CantieriApp
"""


def _send_smtp_sync(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    """Invia l'email via SMTP (sincrono, eseguito in un thread)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, to_email, msg.as_string())


async def send_otp_email(email: str, otp: str, full_name: str | None, expires_minutes: int) -> None:
    """Invia l'email di verifica OTP in modo asincrono (nessun blocco del request handler)."""
    deep_link = _build_deep_link(email, otp)
    subject = "Verifica il tuo account CantieriApp"
    html_body = _build_html_email(full_name or "", otp, expires_minutes, deep_link)
    text_body = _build_text_email(full_name or "", otp, expires_minutes, deep_link)

    def _runner() -> None:
        try:
            _send_smtp_sync(email, subject, html_body, text_body)
            logger.info("OTP email sent successfully to %s", email)
        except Exception:
            logger.exception("Failed to send OTP email to %s", email)

    # Esegue l'invio in un thread pool per non bloccare l'event loop
    await asyncio.get_running_loop().run_in_executor(None, _runner)
