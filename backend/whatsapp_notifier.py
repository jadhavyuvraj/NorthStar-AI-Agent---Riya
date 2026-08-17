"""Customer WhatsApp confirmation delivery through Meta's Cloud API."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def whatsapp_notifications_ready() -> bool:
    """Return True only when the Meta WhatsApp delivery settings are complete."""
    enabled = os.getenv("WHATSAPP_NOTIFICATION_ENABLED", "false").lower()
    return enabled in {"1", "true", "yes", "on"} and all(
        (os.getenv(name) or "").strip()
        for name in (
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_TEMPLATE_NAME",
        )
    )


def send_booking_confirmation(
    session_id: str,
    customer_whatsapp: str,
    booking_request: str,
) -> None:
    """Send one approved-template confirmation to the customer.

    The configured WhatsApp template must contain exactly one body variable
    ({{1}}). Meta requires a customer opt-in and an approved template when a
    business initiates a WhatsApp conversation.
    """
    if not whatsapp_notifications_ready():
        print("WhatsApp confirmation not sent: Meta WhatsApp is not configured.")
        return

    api_version = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v22.0").strip("/")
    phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"].strip()
    endpoint = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    details = (
        "Northstar One, Sector 79, Gurugram. "
        f"Your requested site-visit date and time: {booking_request}"
    )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": customer_whatsapp,
        "type": "template",
        "template": {
            "name": os.environ["WHATSAPP_TEMPLATE_NAME"].strip(),
            "language": {
                "code": os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en_US").strip(),
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": details}],
                }
            ],
        },
    }
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['WHATSAPP_ACCESS_TOKEN'].strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            response.read()
        print(f"WhatsApp booking confirmation queued for session {session_id}.")
    except HTTPError as exc:
        print(f"WhatsApp confirmation failed with HTTP {exc.code} for session {session_id}.")
    except (URLError, TimeoutError) as exc:
        print(f"WhatsApp confirmation network error for session {session_id}: {type(exc).__name__}.")
    except Exception as exc:
        print(f"WhatsApp confirmation failed for session {session_id}: {type(exc).__name__}: {exc}")
