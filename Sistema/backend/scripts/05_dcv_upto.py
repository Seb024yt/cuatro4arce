import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut
from backend.app.services.sii_dcv import download_month_all

def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"dcv": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"dcv": {}}


def _missing_months(storage_dir: Path, company_id: str, year: int, to_month: int) -> list[int]:
    mp = storage_dir / "companies" / company_id / "dcv" / "manifest.json"
    data = _load_manifest(mp).get("dcv", {})
    y = str(year)
    missing = []
    for m in range(1, to_month + 1):
        mm = f"{m:02d}"
        entry = data.get(y, {}).get(mm, {})
        if not entry.get("compras") or not entry.get("ventas_detalles"):
            missing.append(m)
    return missing

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rut", required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--to-month", type=int, required=True, help="1-12 (ej: 2 = Febrero)")
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

    missing_months = _missing_months(storage_dir, company_id, args.year, args.to_month)
    if missing_months:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
            page = context.new_page()

            nuevos = []
            for m in missing_months:
                artifacts = download_month_all(page, storage_dir, company_id, args.year, m)
                nuevos.extend([a.saved_path for a in artifacts])

            if nuevos:
                print("[OK] Archivos nuevos generados:")
                for f in nuevos:
                    print(" -", f)
            else:
                print("[OK] No hubo archivos nuevos (manifest ya cubría el rango).")

            context.close()
            browser.close()
    else:
        print("[OK] Todo el rango ya existe en manifest. Se omiten descargas y no se abre el SII.")

if __name__ == "__main__":
    main()
