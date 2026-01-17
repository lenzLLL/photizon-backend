import random
import requests
from django.utils import timezone
from django.conf import settings
import logging
import os
from api.models import OTP

logger = logging.getLogger(__name__)

# Load environment variables
WHATSAPP_PHONE_ID = os.getenv('WHATSAPP_PHONE_ID', '863349426864550')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_TEST_PHONE = os.getenv('WHATSAPP_TEST_PHONE', '237671434007')

def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_whatsapp(phone):
    otp_entry, created = OTP.objects.get_or_create(phone=phone)

    # Anti spam (cooldown)
    if not otp_entry.can_resend() and not created:
        return {"status": "error", "message": "Attendez quelques secondes avant de renvoyer un OTP"}

    otp_value = generate_otp()
    otp_entry.otp = otp_value
    otp_entry.last_sent_at = timezone.now()
    otp_entry.save()

    # Requête API Meta WhatsApp
    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_TEST_PHONE,
        "type": "template",
        "template": {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    }

    res = requests.post(url, json=payload, headers=headers)
    print(otp_value)
    if res.status_code >= 400:
        return {"status": "error", "message": "Erreur WhatsApp", "details": res.json()}
    
    return {"status": "success"}


def verify_otp(phone, otp):
    try:
        otp_entry = OTP.objects.get(phone=phone)
    except OTP.DoesNotExist:
        return {"status": "error", "message": "OTP non trouvé"}

    if otp_entry.is_expired():
        return {"status": "error", "message": "OTP expiré"}

    if otp_entry.otp != otp:
        return {"status": "error", "message": "OTP incorrect"}

    # Si tout est bon
    otp_entry.delete()
    return {"status": "success"}




def send_whatsapp_template(to_phone: str, template_name: str, parameters: list, language="fr_FR"):
    """
    Send a template message. parameters is list of strings (text parameters).
    Returns dict (response json) or raises request exception.
    """

    url = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language.split("_")[0] + "_" + language.split("_")[-1]},
        }
    }

    # Build components for template body parameters
    components = []
    if parameters:
        components = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(p)} for p in parameters]
        }]
    
    payload["template"]["components"] = components

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()
    #         "name": template_name,
    #         "language": {"code": language.split("_")[0] + "_" + language.split("_")[-1]},
    #         "components": components
    #     }
    # }

    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()