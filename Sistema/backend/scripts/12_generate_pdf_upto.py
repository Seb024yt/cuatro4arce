import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from backend.app.services.monthly_tax_pdf import generate_monthly_tax_summary_pdf
from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut, normalize_rut
from backend.app.services.sii_bhe import fetch_bhe_month
from backend.app.services.sii_dcv import download_month_all
from backend.app.services.sii_f29_remanente import fetch_remanente_prev_month


def _pick_latest_file(folder: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(folder.glob(pattern))
        if matches:
            return matches[-1]
    return None


def _load_manifest(path: Path, root_key: str) -> dict:
    if not path.exists():
        return {root_key: {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {root_key: {}}


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
    p.add_argument(
        "--pdf-all-months",
        action="store_true",
        help="Generar PDF para todos los meses 1..to-month (por defecto solo el mes to-month).",
    )
    args = p.parse_args()

    if not (1 <= args.to_month <= 12):
        raise SystemExit("--to-month debe estar entre 1 y 12")

    storage_root = Path(args.storage_dir)
    company_id = company_id_from_rut(args.rut)
    legacy_company_id = company_id_legacy_from_rut(args.rut)

    state_path = storage_root / "companies" / company_id / "playwright_state" / "state.json"
    legacy_state_path = storage_root / "companies" / legacy_company_id / "playwright_state" / "state.json"
    if not state_path.exists() and legacy_state_path.exists():
        state_path = legacy_state_path
    if not state_path.exists():
        raise SystemExit(f"No existe state.json en: {state_path}")

    rut_norm = normalize_rut(args.rut)
    rut_sin_dv = rut_norm.split("-", 1)[0]

    missing_dcv = _missing_dcv(storage_root, company_id, args.year, args.to_month)
    missing_bhe = _missing_bhe(storage_root, company_id, args.year, args.to_month)
    missing_rem = _missing_remanente(storage_root, company_id, args.year, args.to_month)

    if missing_dcv or missing_bhe or missing_rem:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=args.headless)
            context = browser.new_context(storage_state=str(state_path), accept_downloads=True)
            page_dcv = context.new_page()
            page_bhe = context.new_page()
            page_rem = context.new_page()

            for m in missing_dcv:
                download_month_all(page_dcv, storage_root, company_id, args.year, m)

            for m in missing_bhe:
                fetch_bhe_month(page_bhe, storage_root, company_id, rut_sin_dv, args.year, m)

            for m in missing_rem:
                fetch_remanente_prev_month(page_rem, storage_root, company_id, args.year, m)

            context.close()
            browser.close()

    company_dir = storage_root / "companies" / company_id
    legacy_company_dir = storage_root / "companies" / legacy_company_id

    profile_path = company_dir / "profile.json"
    if not profile_path.exists():
        legacy_profile = legacy_company_dir / "profile.json"
        if legacy_profile.exists():
            profile_path = legacy_profile

    razon_social = company_id
    if profile_path.exists():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            razon_social = profile.get("razon_social") or profile.get("rut") or company_id
        except Exception:
            razon_social = company_id

    months = range(1, args.to_month + 1) if args.pdf_all_months else [args.to_month]
    for month in months:
        dcv_dir = storage_root / "companies" / company_id / "dcv" / str(args.year) / f"{month:02d}"
        ventas_path = _pick_latest_file(
            dcv_dir,
            [
                f"RCV_VENTA_*_{args.year}{month:02d}*.csv",
                f"VENTAS_{args.year}{month:02d}*.csv",
            ],
        )
        compras_path = _pick_latest_file(
            dcv_dir,
            [
                f"RCV_COMPRA_*_{args.year}{month:02d}*.csv",
                f"COMPRAS_{args.year}{month:02d}*.csv",
            ],
        )

        if not ventas_path or not compras_path:
            raise SystemExit(f"No se encontraron archivos DCV en {dcv_dir}")

        bhe_dir = storage_root / "companies" / company_id / "bhe" / str(args.year) / f"{month:02d}"
        bhe_path = _pick_latest_file(bhe_dir, ["*.html", "*.htm", "*.xls", "*.xlsx"])

        rem_dir = storage_root / "companies" / company_id / "f29_remanente" / str(args.year) / f"{month:02d}"
        rem_path = _pick_latest_file(rem_dir, ["*.json", "*.html", "*.pdf", "*.txt"])

        out_pdf = (
            storage_root
            / "companies"
            / company_id
            / "Resumen"
            / f"Resumen_{company_id}_{args.year}_{month:02d}.pdf"
        )

        summary = generate_monthly_tax_summary_pdf(
            company_name=str(razon_social),
            period_year=int(args.year),
            period_month=int(month),
            ventas_path=str(ventas_path),
            compras_path=str(compras_path),
            boletas_honorarios_path=str(bhe_path) if bhe_path else None,
            formulario_compacto_path=str(rem_path) if rem_path else None,
            out_pdf_path=str(out_pdf),
        )

        print("PDF generado:", out_pdf)
        print("Resumen:", json.dumps(summary.get("totales", {}), ensure_ascii=False))


if __name__ == "__main__":
    main()
