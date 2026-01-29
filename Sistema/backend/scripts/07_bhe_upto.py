import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from backend.app.services.sii_auth import (
    company_id_from_rut,
    company_id_legacy_from_rut,
    normalize_rut,
)
from backend.app.services.sii_bhe import fetch_bhe_month

def _load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"bhe": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"bhe": {}}


def _missing_months(storage_dir: Path, company_id: str, year: int, to_month: int) -> list[int]:
    mp = storage_dir / "companies" / company_id / "bhe" / "manifest.json"
    data = _load_manifest(mp).get("bhe", {})
    y = str(year)
    missing = []
    for m in range(1, to_month + 1):
        mm = f"{m:02d}"
        entry = data.get(y, {}).get(mm, {})
        if not entry.get("html") and not entry.get("xls"):
            missing.append(m)
    return missing


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rut", required=True)  # con DV
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--to-month", type=int, required=True)
    p.add_argument("--storage-dir", default="storage")
    p.add_argument("--headless", action="store_true")

    # ✅ Por defecto NO bajamos XLS (se procesa HTML)
    p.add_argument("--download-xls", action="store_true", help="Descargar también la planilla XLS (no recomendado).")
    p.add_argument("--evidence", action="store_true", help="Guardar PNG como evidencia (opcional).")

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

    rut_norm = normalize_rut(args.rut)
    rut_sin_dv = rut_norm.split("-", 1)[0]

    missing_months = _missing_months(storage_dir, company_id, args.year, args.to_month)
    if missing_months:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
            page = context.new_page()

            nuevos = []
            for m in missing_months:
                art = fetch_bhe_month(
                    page=page,
                    storage_dir=storage_dir,
                    company_id=company_id,
                    rut_sin_dv=rut_sin_dv,
                    year=args.year,
                    month=m,
                    evidence=args.evidence,
                    download_xls=args.download_xls,
                )
                if art:
                    nuevos.append(art)

            if nuevos:
                print("[OK] BHE procesados (HTML fuente única):")
                for a in nuevos:
                    print(f" - {a.year}-{a.month:02d} html={a.saved_html} xls={a.saved_xls}")
            else:
                print("[OK] No hubo BHE nuevos (manifest ya cubría el rango).")

            context.close()
            browser.close()
    else:
        print("[OK] Todo el rango ya existe en manifest. Se omiten descargas y no se abre el SII.")


if __name__ == "__main__":
    main()
