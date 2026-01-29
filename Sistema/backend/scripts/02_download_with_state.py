import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut
from backend.app.services.sii_download import make_run_dir, download_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rut", required=True)
    parser.add_argument("--state-path", default=None, help="Opcional. Si no, se calcula desde storage/companies/<rut>/...")
    parser.add_argument("--target-url", required=True, help="URL objetivo ya autenticado (ej: pantalla que tenga el botón de descarga)")
    parser.add_argument("--click-selector", required=True, help="Selector CSS del botón/link que dispara la descarga")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--storage-dir", default="storage")
    args = parser.parse_args()

    company_id = company_id_from_rut(args.rut)
    legacy_company_id = company_id_legacy_from_rut(args.rut)

    if args.state_path:
        state_path = Path(args.state_path)
    else:
        state_path = Path(args.storage_dir) / "companies" / company_id / "playwright_state" / "state.json"
        legacy_state_path = Path(args.storage_dir) / "companies" / legacy_company_id / "playwright_state" / "state.json"
        if not state_path.exists() and legacy_state_path.exists():
            state_path = legacy_state_path

    if not state_path.exists():
        raise SystemExit(f"No existe state: {state_path}. Ejecute primero 01_login_save_state.py")

    base_dir = Path(args.storage_dir)
    run_dir = make_run_dir(base_dir, company_id)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
        page = context.new_page()

        result = download_file(page, args.target_url, args.click_selector, run_dir)
        print(f"[OK] Descarga guardada en: {result.saved_path}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()
