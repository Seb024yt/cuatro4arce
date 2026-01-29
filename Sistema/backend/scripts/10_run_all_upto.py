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
from backend.app.services.sii_dcv import download_month_all
from backend.app.services.sii_f29_remanente import fetch_remanente_prev_month

def _load_manifest(path: Path, root_key: str) -> dict:
    if not path.exists():
        return {root_key: {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {root_key: {}}


def _need_dcv(storage_dir: Path, company_id: str, year: int, to_month: int) -> bool:
    return bool(_missing_dcv(storage_dir, company_id, year, to_month))


def _need_bhe(storage_dir: Path, company_id: str, year: int, to_month: int) -> bool:
    return bool(_missing_bhe(storage_dir, company_id, year, to_month))


def _need_remanente(storage_dir: Path, company_id: str, year: int, to_month: int) -> bool:
    return bool(_missing_remanente(storage_dir, company_id, year, to_month))


def _missing_dcv(storage_dir: Path, company_id: str, year: int, to_month: int) -> list[int]:
    mp = storage_dir / "companies" / company_id / "dcv" / "manifest.json"
    data = _load_manifest(mp, "dcv").get("dcv", {})
    y = str(year)
    missing = []
    for m in range(1, to_month + 1):
        mm = f"{m:02d}"
        entry = data.get(y, {}).get(mm, {})
        if not entry.get("compras") or not entry.get("ventas_detalles"):
            missing.append(m)
    return missing


def _missing_bhe(storage_dir: Path, company_id: str, year: int, to_month: int) -> list[int]:
    mp = storage_dir / "companies" / company_id / "bhe" / "manifest.json"
    data = _load_manifest(mp, "bhe").get("bhe", {})
    y = str(year)
    missing = []
    for m in range(1, to_month + 1):
        mm = f"{m:02d}"
        entry = data.get(y, {}).get(mm, {})
        if not entry.get("html") and not entry.get("xls"):
            missing.append(m)
    return missing


def _missing_remanente(storage_dir: Path, company_id: str, year: int, to_month: int) -> list[int]:
    mp = storage_dir / "companies" / company_id / "f29_remanente" / "manifest.json"
    data = _load_manifest(mp, "remanente").get("remanente", {})
    y = str(year)
    missing = []
    for m in range(1, to_month + 1):
        mm = f"{m:02d}"
        if not data.get(y, {}).get(mm):
            missing.append(m)
    return missing


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

    rut_norm = normalize_rut(args.rut)
    rut_sin_dv = rut_norm.split("-", 1)[0]

    missing_dcv = _missing_dcv(storage_dir, company_id, args.year, args.to_month)
    missing_bhe = _missing_bhe(storage_dir, company_id, args.year, args.to_month)
    missing_rem = _missing_remanente(storage_dir, company_id, args.year, args.to_month)

    need_dcv = bool(missing_dcv)
    need_bhe = bool(missing_bhe)
    need_rem = bool(missing_rem)

    if need_dcv or need_bhe or need_rem:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
            page = context.new_page()

            # 1) DCV
            nuevos_dcv = []
            for m in missing_dcv:
                artifacts = download_month_all(page, storage_dir, company_id, args.year, m)
                nuevos_dcv.extend([a.saved_path for a in artifacts])
            if nuevos_dcv:
                print("[OK] Archivos DCV nuevos:")
                for f in nuevos_dcv:
                    print(" -", f)
            else:
                print("[OK] No hubo archivos DCV nuevos (manifest ya cubria el rango).")

            # 2) BHE (honorarios)
            nuevos_bhe = []
            for m in missing_bhe:
                art = fetch_bhe_month(page, storage_dir, company_id, rut_sin_dv, args.year, m)
                if art:
                    nuevos_bhe.append(art)
            if nuevos_bhe:
                print("[OK] BHE HTML descargados:")
                for a in nuevos_bhe:
                    print(f" - {a.year}-{a.month:02d} html={a.saved_html}")
            else:
                print("[OK] No hubo BHE nuevos (manifest ya cubria el rango).")

            # 3) F29 Remanente (codigo 77 del mes anterior)
            nuevos_rem = []
            for m in missing_rem:
                res = fetch_remanente_prev_month(page, storage_dir, company_id, args.year, m)
                if res:
                    nuevos_rem.append(res)
            if nuevos_rem:
                print("[OK] Remanentes (codigo 77) procesados:")
                for r in nuevos_rem:
                    tgt = f"{r.target_year}-{r.target_month:02d}"
                    prev = f"{r.prev_year}-{r.prev_month:02d}"
                    print(f" - target={tgt} prev={prev} folio={r.folio} codigo77={r.codigo_77} png77={r.saved_png_codigo77}")
            else:
                print("[OK] No hubo remanentes nuevos (manifest ya cubria el rango).")

            context.close()
            browser.close()
    else:
        print("[OK] Todo el rango ya existe en manifest. Se omiten descargas y no se abre el SII.")

    print("[OK] Descargas completadas.")


if __name__ == "__main__":
    main()
