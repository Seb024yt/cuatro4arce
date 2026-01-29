import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut
from backend.app.services.sii_f29_remanente import fetch_remanente_prev_month


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rut", required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--to-month", type=int, required=True)
    p.add_argument("--storage-dir", default="storage")
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()

    if not (1 <= args.to_month <= 12):
        raise SystemExit("--to-month debe estar entre 1 y 12")

    storage_dir = Path(args.storage_dir)
    company_id = company_id_from_rut(args.rut)
    legacy_company_id = company_id_legacy_from_rut(args.rut)

    state_path = storage_dir / "companies" / company_id / "playwright_state" / "state.json"
    legacy_state_path = storage_dir / "companies" / legacy_company_id / "playwright_state" / "state.json"
    if not state_path.exists() and legacy_state_path.exists():
        state_path = legacy_state_path
    if not state_path.exists():
        raise SystemExit(f"No existe state.json en: {state_path}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
        page = context.new_page()

        nuevos = []
        for m in range(1, args.to_month + 1):
            res = fetch_remanente_prev_month(page, storage_dir, company_id, args.year, m)
            if res:
                nuevos.append(res)

        if nuevos:
            print("[OK] Remanentes (código 77) procesados:")
            for r in nuevos:
                tgt = f"{r.target_year}-{r.target_month:02d}"
                prev = f"{r.prev_year}-{r.prev_month:02d}"
                print(f" - target={tgt} prev={prev} folio={r.folio} codigo77={r.codigo_77} png77={r.saved_png_codigo77}")
        else:
            print("[OK] No hubo nuevos (manifest ya cubría el rango).")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
