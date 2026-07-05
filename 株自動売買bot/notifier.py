import requests


def send_slack(webhook_url: str, text: str, *, session=None) -> bool:
    client = session or requests
    try:
        resp = client.post(webhook_url, json={"text": text}, timeout=10)
        return getattr(resp, "status_code", 200) == 200
    except Exception:
        return False
