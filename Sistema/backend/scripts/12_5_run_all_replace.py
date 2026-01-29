import argparse
import json
import shutil
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


def _save_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _purge_month_dir(base_dir: Path) -> bool:
    if base_dir.exists():
        shutil.rmtree(base_dir)
        return True
    return False


def _purge_dcv(storage_dir: Path, company_id: str, year: int, month: int) -> list[str]:
    removed = []
    mp = storage_dir / "companies" / company_id / "dcv" / "manifest.json"
    data = _load_manifest(mp, "dcv")
    y = str(year)
    mm = f"{month:02d}"
    data.get("dcv", {}).get(y, {}).pop(mm, None)
    month_dir = storage_dir / "companies" / company_id / "dcv" / y / mm
    if _purge_month_dir(month_dir):
        removed.append(str(month_dir))
    if y in data.get("dcv", {}) and not data["dcv"][y]:
        data["dcv"].pop(y, None)
    _save_manifest(mp, data)
    return removed


def _purge_bhe(storage_dir: Path, company_id: str, year: int, month: int) -> list[str]:
    removed = []
    mp = storage_dir / "companies" / company_id / "bhe" / "manifest.json"
    data = _load_manifest(mp, "bhe")
    y = str(year)
    mm = f"{month:02d}"
    data.get("bhe", {}).get(y, {}).pop(mm, None)
    month_dir = storage_dir / "companies" / company_id / "bhe" / y / mm
    if _purge_month_dir(month_dir):
        removed.append(str(month_dir))
    if y in data.get("bhe", {}) and not data["bhe"][y]:
        data["bhe"].pop(y, None)
    _save_manifest(mp, data)
    return removed


def _purge_remanente(storage_dir: Path, company_id: str, year: int, month: int) -> list[str]:
    removed = []
    mp = storage_dir / "companies" / company_id / "f29_remanente" / "manifest.json"
    data = _load_manifest(mp, "remanente")
    y = str(year)
    mm = f"{month:02d}"
    data.get("remanente", {}).get(y, {}).pop(mm, None)
    month_dir = storage_dir / "companies" / company_id / "f29_remanente" / y / mm
    if _purge_month_dir(month_dir):
        removed.append(str(month_dir))
    if y in data.get("remanente", {}) and not data["remanente"][y]:
        data["remanente"].pop(y, None)
    _save_manifest(mp, data)
    return removed


def main() -> None:
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

    removed_dcv = _purge_dcv(storage_dir, company_id, args.year, args.to_month)
    removed_bhe = _purge_bhe(storage_dir, company_id, args.year, args.to_month)
    removed_rem = _purge_remanente(storage_dir, company_id, args.year, args.to_month)

    print("[OK] Purga completa para pruebas de administracion.")
    if removed_dcv:
        print("[OK] DCV borrado:")
        for pth in removed_dcv:
            print(" -", pth)
    if removed_bhe:
        print("[OK] BHE borrado:")
        for pth in removed_bhe:
            print(" -", pth)
    if removed_rem:
        print("[OK] Remanente borrado:")
        for pth in removed_rem:
            print(" -", pth)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
        page = context.new_page()

        # 1) DCV (compras, ventas, boletas)
        nuevos_dcv = []
        artifacts = download_month_all(page, storage_dir, company_id, args.year, args.to_month)
        nuevos_dcv.extend([a.saved_path for a in artifacts])
        if nuevos_dcv:
            print("[OK] Archivos DCV nuevos:")
            for f in nuevos_dcv:
                print(" -", f)
        else:
            print("[OK] No hubo archivos DCV nuevos.")

        # 2) BHE (honorarios)
        nuevos_bhe = []
        art = fetch_bhe_month(page, storage_dir, company_id, rut_sin_dv, args.year, args.to_month)
        if art:
            nuevos_bhe.append(art)
        if nuevos_bhe:
            print("[OK] BHE HTML descargados:")
            for a in nuevos_bhe:
                print(f" - {a.year}-{a.month:02d} html={a.saved_html}")
        else:
            print("[OK] No hubo BHE nuevos.")

        # 3) F29 Remanente (codigo 77 del mes anterior)
        nuevos_rem = []
        res = fetch_remanente_prev_month(page, storage_dir, company_id, args.year, args.to_month)
        if res:
            nuevos_rem.append(res)
        if nuevos_rem:
            print("[OK] Remanentes (codigo 77) procesados:")
            for r in nuevos_rem:
                tgt = f"{r.target_year}-{r.target_month:02d}"
                prev = f"{r.prev_year}-{r.prev_month:02d}"
                print(
                    f" - target={tgt} prev={prev} folio={r.folio} codigo77={r.codigo_77} png77={r.saved_png_codigo77}"
                )
        else:
            print("[OK] No hubo remanentes nuevos.")

        context.close()
        browser.close()

    print("[OK] Descargas completadas.")


if __name__ == "__main__":
    main()
