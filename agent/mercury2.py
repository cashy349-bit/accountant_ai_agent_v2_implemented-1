import json
import os
import urllib.request


class Mercury2Client:
    def __init__(self):
        self.api_key = os.getenv("INCEPTION_API_KEY", "")
        self.model = os.getenv("MERCURY_MODEL", "mercury-2")
        self.base_url = os.getenv(
            "MERCURY_BASE_URL",
            "https://api.inceptionlabs.ai/v1",
        ).rstrip("/")

    def extract_invoice(self, text, document_id):
        if not self.api_key:
            raise RuntimeError("INCEPTION_API_KEY is not configured")

        prompt = f"""
Extract the invoice information from the text below.

Return ONLY valid JSON with exactly these fields:
vendor_name, invoice_number, invoice_date, subtotal, tax, total, category, confidence

Use null when a value cannot be determined.
subtotal, tax, and total must be numbers or null.
confidence must be a number from 0 to 1.

Document ID: {document_id}

Invoice text:
{text}
"""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode())

        content = result["choices"][0]["message"]["content"].strip()

        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()

        return json.loads(content)
