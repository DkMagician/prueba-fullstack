import json
import sys
from typing import Optional

import httpx
from playwright.sync_api import sync_playwright


BACKEND_URL = "http://127.0.0.1:8000"


def extract_wikipedia_text(url: str, max_paragraphs: int = 3) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Wikipedia: contenido principal suele estar en #mw-content-text
        # Tomamos párrafos directos (evita sidebar/nav)
        paras = page.locator("#mw-content-text p")
        count = min(paras.count(), max_paragraphs)

        chunks: list[str] = []
        for i in range(count):
            t = paras.nth(i).inner_text().strip()
            # Filtra párrafos vacíos o de avisos
            if t and len(t.split()) > 5:
                chunks.append(t)

        browser.close()

    text = "\n\n".join(chunks).strip()
    return text


def post_summary(text: str, source: str = "web", idem_key: Optional[str] = None) -> dict:
    payload = {"source": source, "text": text}
    headers = {"Content-Type": "application/json"}
    if idem_key:
        headers["Idempotency-Key"] = idem_key

    with httpx.Client(timeout=30) as client:
        r = client.post(f"{BACKEND_URL}/summaries/async", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/rpa_wikipedia.py <wikipedia_url> [idempotency_key]")
        return 2

    url = sys.argv[1]
    idem_key = sys.argv[2] if len(sys.argv) >= 3 else None

    print(f"[RPA] Visitando: {url}")
    text = extract_wikipedia_text(url, max_paragraphs=4)

    if not text:
        print("[RPA] No se pudo extraer texto (vacío).")
        return 1

    print(f"[RPA] Extraído ~{len(text.split())} palabras. Enviando al backend...")

    resp = post_summary(text=text, source="web", idem_key=idem_key)

    print("[RPA] Backend respondió:")
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    print("\nTIP: Abre la UI y verás el summary cambiar a procesado por WS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
