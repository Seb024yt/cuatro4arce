from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from backend.app.services.sii_auth import company_id_from_rut, company_id_legacy_from_rut, login_and_save_state


def _load_profile_password(profile_path: Path) -> str | None:
    if not profile_path.exists():
        return None
    try:
        data = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    password = data.get("password")
    if password:
        return str(password)
    return None


def _resolve_password(storage_dir: Path, company_id: str, legacy_company_id: str) -> str | None:
    profile_path = storage_dir / "companies" / company_id / "profile.json"
    password = _load_profile_password(profile_path)
    if password:
        return password

    legacy_profile = storage_dir / "companies" / legacy_company_id / "profile.json"
    return _load_profile_password(legacy_profile)


def _ensure_login_state(
    *,
    storage_dir: Path,
    rut: str,
    headless: bool,
) -> None:
    company_id = company_id_from_rut(rut)
    legacy_company_id = company_id_legacy_from_rut(rut)

    state_path = storage_dir / "companies" / company_id / "playwright_state" / "state.json"
    legacy_state_path = storage_dir / "companies" / legacy_company_id / "playwright_state" / "state.json"
    if state_path.exists() or legacy_state_path.exists():
        return

    password = _resolve_password(storage_dir, company_id, legacy_company_id)
    if not password:
        raise SystemExit(
            "No existe state.json ni password guardado en profile.json. "
            "Primero ejecuta 01_login_save_state.py con --rut y --clave."
        )

    login_and_save_state(
        rut=rut,
        clave=password,
        storage_root=storage_dir,
        headless=headless,
    )


def main() -> None:
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

    storage_dir = Path(args.storage_dir)
    _ensure_login_state(storage_dir=storage_dir, rut=args.rut, headless=bool(args.headless))

    script_path = Path(__file__).resolve().parent / "12_generate_pdf_upto.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--rut",
        args.rut,
        "--year",
        str(args.year),
        "--to-month",
        str(args.to_month),
        "--storage-dir",
        str(storage_dir),
    ]
    if args.headless:
        cmd.append("--headless")
    if args.pdf_all_months:
        cmd.append("--pdf-all-months")

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
