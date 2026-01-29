import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rut", required=True)
    p.add_argument("--storage-dir", default="storage")
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    company_id = company_id_from_rut(args.rut)
    legacy_company_id = company_id_legacy_from_rut(args.rut)
    state_path = Path(args.storage_dir) / "companies" / company_id / "playwright_state" / "state.json"
    legacy_state_path = Path(args.storage_dir) / "companies" / legacy_company_id / "playwright_state" / "state.json"
    if not state_path.exists() and legacy_state_path.exists():
        state_path = legacy_state_path
    if not state_path.exists():
        raise SystemExit(f"No existe state: {state_path}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()

        # Página simple de SII para ver si ya quedas autenticado (redirige si no)
        page.goto("https://www.sii.cl", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        print("URL actual:", page.url)

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
