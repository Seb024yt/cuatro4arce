# backend/scripts/01_login_save_state.py
from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.services.sii_auth import login_and_save_state


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="SII: Login y guardado de Playwright state + profile (razón social)."
    )
    p.add_argument("--rut", required=True, help="RUT empresa (ej: 77395729-0)")
    p.add_argument("--clave", required=True, help="Clave SII")
    p.add_argument(
        "--storage-dir",
        default="storage",
        help="Directorio raíz de storage (default: storage)",
    )

    # Flags operacionales
    p.add_argument("--headless", action="store_true", help="Ejecutar navegador en headless")
    p.add_argument("--headed", action="store_true", help="Ejecutar navegador visible (override headless)")
    p.add_argument("--evidence", action="store_true", help="Guardar evidencia (screenshots) en storage/companies/<id>/evidence")
    p.add_argument("--slow-mo", type=int, default=0, help="Slow motion en ms (debug)")
    p.add_argument("--timeout-ms", type=int, default=30000, help="Timeout por defecto en ms")
    p.add_argument(
        "--start-url",
        default=None,
        help="URL inicial (default: SII_AUTH_URL del .env, o https://www.sii.cl/)",
    )

    return p


def main() -> None:
    args = build_parser().parse_args()

    storage_root = Path(args.storage_dir)

    # Resolución modo headless/ headed
    headless = True
    if args.headed:
        headless = False
    elif args.headless:
        headless = True

    res = login_and_save_state(
        rut=args.rut,
        clave=args.clave,
        storage_root=storage_root,
        headless=headless,
        slow_mo_ms=int(args.slow_mo),
        timeout_ms=int(args.timeout_ms),
        evidence=bool(args.evidence),
        start_url=str(args.start_url) if args.start_url else None,
    )

    print("OK - Login y persistencia completados")
    print("company_id:", res.company_id)
    print("rut:", res.rut)
    print("razon_social:", res.razon_social)
    print("state_path:", res.state_path)
    print("profile_path:", res.profile_path)
    print("closed_modal_actualizar_datos:", res.closed_modal_actualizar_datos)
    print("final_url:", res.final_url)


if __name__ == "__main__":
    main()
