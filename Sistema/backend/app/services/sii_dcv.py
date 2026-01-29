# backend/app/services/sii_dcv.py
from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote_to_bytes

from playwright.sync_api import Page, TimeoutError as PWTimeoutError

DCV_URL = "https://www4.sii.cl/consdcvinternetui/#/index"
MONTHS = {i: f"{i:02d}" for i in range(1, 13)}

# Códigos comunes en DCV (ampliable)
CODE_RE = re.compile(r"\((\d{1,3})\)")
BOLETA_CODE_RE = re.compile(r"\(39\)", re.IGNORECASE)  # boleta electrónica (39)

# Flags operativos
DEBUG = os.getenv("SII_DCV_DEBUG", "").strip().lower() in ("1", "true", "yes", "y")
FORCE_DOWNLOAD = os.getenv("SII_DCV_FORCE", "").strip().lower() in ("1", "true", "yes", "y")


class DCVDownloadError(RuntimeError):
    """Error controlado para descargas/capturas DCV."""


@dataclass
class DCVArtifact:
    year: int
    month: int
    section: str  # "compras" | "ventas_detalles" | "ventas_boletas_linea"
    saved_path: Path


# ----------------------------
# Manifest (para no reprocesar)
# ----------------------------
def _manifest_path(storage_dir: Path, company_id: str) -> Path:
    return storage_dir / "companies" / company_id / "dcv" / "manifest.json"


def _load_manifest(storage_dir: Path, company_id: str) -> Dict:
    mp = _manifest_path(storage_dir, company_id)
    if not mp.exists():
        return {"dcv": {}}
    return json.loads(mp.read_text(encoding="utf-8"))


def _save_manifest(storage_dir: Path, company_id: str, data: Dict) -> None:
    mp = _manifest_path(storage_dir, company_id)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _already(manifest: Dict, year: int, month: int, section: str) -> bool:
    y = str(year)
    m = MONTHS[month]
    return bool(manifest.get("dcv", {}).get(y, {}).get(m, {}).get(section))


def _mark(manifest: Dict, year: int, month: int, section: str, path: str) -> None:
    y = str(year)
    m = MONTHS[month]
    manifest.setdefault("dcv", {}).setdefault(y, {}).setdefault(m, {})[section] = path


def _month_dir(storage_dir: Path, company_id: str, year: int, month: int) -> Path:
    d = storage_dir / "companies" / company_id / "dcv" / str(year) / MONTHS[month]
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------
# UI helpers
# ----------------------------
def _set_select_value(page: Page, selector: str, value: str, timeout_ms: int = 12000) -> None:
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=timeout_ms)
    loc.select_option(value=value)


def _click(page: Page, selectors: List[str], timeout_ms: int = 10000) -> None:
    last = None
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout_ms)
            loc.click()
            return
        except Exception as e:
            last = e
    raise DCVDownloadError(f"No se pudo clickear ninguno de: {selectors}. Último error: {last}")


def _goto_dcv(page: Page) -> None:
    page.goto(DCV_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(800)


def _select_period(page: Page, year: int, month: int) -> None:
    # Mes (confirmado: select#periodoMes)
    _set_select_value(page, "#periodoMes", MONTHS[month])

    # Año (típicos selectores)
    year_selectors = [
        "select[ng-model='periodoAnho']",
        "select[ng-model='periodoAno']",
        "#periodoAnho",
        "#periodoAno",
        # fallback: 2do select dentro del form
        "form select.form-control >> nth=1",
    ]

    ok = False
    for ys in year_selectors:
        try:
            _set_select_value(page, ys, str(year))
            ok = True
            break
        except Exception:
            continue

    if not ok:
        raise DCVDownloadError("No se pudo seleccionar el año. Confirma selector del <select> de año.")


def _consult(page: Page) -> None:
    _click(
        page,
        [
            "button:has-text('Consultar')",
            "input[type='button'][value*='Consultar' i]",
            "input[type='submit'][value*='Consultar' i]",
        ],
    )
    try:
        # SPA del SII puede quedar en "networkidle" tardísimo; espera algo útil.
        page.wait_for_selector("button:has-text('Descargar Detalles')", timeout=12000)
    except Exception:
        page.wait_for_timeout(1500)


def _ensure_section_loaded(page: Page, section: str) -> None:
    """
    Validación liviana (solo para esperar que el tab realmente cargó).
    NO valida el contenido del CSV; solo confirma el título de sección.
    """
    if section == "compras":
        locator = page.locator("text=/RESUMEN\\s+REGISTRO\\s+DE\\s+COMPRAS/i").first
    else:
        locator = page.locator("text=/RESUMEN\\s+REGISTRO\\s+DE\\s+VENTAS/i").first

    try:
        locator.wait_for(state="visible", timeout=12000)
    except Exception as exc:
        raise DCVDownloadError(f"No se detectó resumen de {section}. Revisa tabs/selectores.") from exc


def _go_tab_compra(page: Page) -> None:
    _click(
        page,
        [
            "#tabCompra",
            "a#tabCompra",
            "a[ui-sref='compra']",
            "a[href^='#compra']",
            "a[href^='#compra/']",
            "a[role='tab']:has-text('COMPRA')",
            "a[role='tab']:has-text('Compras')",
        ],
    )
    page.wait_for_timeout(500)
    _ensure_section_loaded(page, "compras")


def _go_tab_venta(page: Page) -> None:
    selectors = [
        "a[href^='#venta']",

    ]
    _click(page, selectors, timeout_ms=8000)
    page.wait_for_timeout(400)


def _clear_existing_csv_anchors(page: Page) -> None:
    """
    Control clave en SPA: evita capturar el CSV anterior si el SII deja el <a> viejo en el DOM.
    """
    page.evaluate(
        """() => {
          document.querySelectorAll("a[download][href^='data:text/csv']").forEach(a => a.remove());
        }"""
    )


def _click_descargar_detalles(page: Page, *, clear_existing: bool = True) -> None:
    """
    Paso operacional: limpiar anchors antiguos -> click "Descargar Detalles".
    """
    if clear_existing:
        _clear_existing_csv_anchors(page)
    _click(page, ["button:has-text('Descargar Detalles')"])


def _download_from_data_anchor_matching(
    page: Page, save_dir: Path, required_substrings: list[str]
) -> Path:
    """
    Espera un <a download> cuyo nombre contenga TODOS los substrings requeridos (case-insensitive).
    Útil para evitar confundir compras/ventas cuando hay múltiples anchors en DOM.
    """
    req = [s.lower() for s in required_substrings if s]

    def _finder_js() -> str:
        return (
            "() => {\n"
            "  const req = " + json.dumps(req) + ";\n"
            "  const anchors = Array.from(document.querySelectorAll(\"a[download][href^='data:text/csv']\"));\n"
            "  for (const a of anchors) {\n"
            "    const name = (a.getAttribute('download') || '').toLowerCase();\n"
            "    if (req.every(s => name.includes(s))) return true;\n"
            "  }\n"
            "  return false;\n"
            "}"
        )

    try:
        page.wait_for_function(_finder_js(), timeout=20000)
    except PWTimeoutError as exc:
        raise DCVDownloadError(
            f"No apareció el anchor de descarga con: {required_substrings}"
        ) from exc

    # Recuperar el anchor y guardarlo
    result = page.evaluate(
        """(req) => {
          const anchors = Array.from(document.querySelectorAll("a[download][href^='data:text/csv']"));
          for (const a of anchors) {
            const name = (a.getAttribute('download') || '').toLowerCase();
            if (req.every(s => name.includes(s))) {
              return { download: a.getAttribute('download'), href: a.getAttribute('href') };
            }
          }
          return null;
        }""",
        req,
    )
    if not result or not result.get("href"):
        raise DCVDownloadError("No se pudo leer el anchor de descarga esperado.")

    dl_name = result.get("download") or "dcv.csv"
    href = result.get("href") or ""
    if not href.startswith("data:text/csv") or "," not in href:
        raise DCVDownloadError("El href del <a download> no es data:text/csv válido.")

    data_part = href.split(",", 1)[1]
    raw = unquote_to_bytes(data_part)

    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / dl_name
    path.write_bytes(raw)

    if DEBUG:
        print(f"[DCV] Guardado: {path.name} ({path.stat().st_size} bytes)")

    return path


# ----------------------------
# Descarga tipo Data-URI (SIN validaciones)
# ----------------------------
def _download_from_data_anchor(page: Page, save_dir: Path) -> Path:
    """
    Captura el <a download ... href="data:text/csv,..."> generado por el SII,
    decodifica y guarda con el nombre exacto de 'download' (sin renombrar).
    """
    anchor = page.locator("a[download][href^='data:text/csv']").first
    try:
        anchor.wait_for(state="attached", timeout=20000)
    except PWTimeoutError as exc:
        raise DCVDownloadError("No apareció el anchor de descarga (data:text/csv).") from exc

    dl_name = anchor.get_attribute("download") or "dcv.csv"
    href = anchor.get_attribute("href") or ""

    if not href.startswith("data:text/csv") or "," not in href:
        raise DCVDownloadError("El href del <a download> no es data:text/csv válido (descarga distinta).")

    data_part = href.split(",", 1)[1]
    raw = unquote_to_bytes(data_part)

    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / dl_name
    path.write_bytes(raw)

    if DEBUG:
        print(f"[DCV] Guardado: {path.name} ({path.stat().st_size} bytes)")

    return path


# ----------------------------
# Boletas: capturar línea desde tabla (sin descargar detalle)
# ----------------------------
def _table_rows_text(page: Page) -> List[List[str]]:
    """
    Extrae filas (th/td) de la primera tabla visible.
    """
    table = page.locator("table:visible").first
    table.wait_for(state="visible", timeout=12000)

    rows = table.locator("tr")
    out: List[List[str]] = []
    for i in range(rows.count()):
        r = rows.nth(i)
        cells = r.locator("th, td")
        row_cells: List[str] = []
        for j in range(cells.count()):
            txt = (cells.nth(j).inner_text() or "").strip().replace("\n", " ")
            row_cells.append(txt)
        if any(c for c in row_cells):
            out.append(row_cells)
    return out


def _find_boletas_row(rows: List[List[str]]) -> Optional[List[str]]:
    for r in rows:
        joined = " ".join(r)
        if BOLETA_CODE_RE.search(joined) or ("BOLETA" in joined.upper()):
            return r
    return None


def save_boletas_summary_line(page: Page, save_path: Path) -> Optional[Path]:
    """
    Guarda en CSV la fila de boletas del resumen.
    Incluye encabezado si se detecta.
    """
    rows = _table_rows_text(page)
    if not rows:
        raise DCVDownloadError("No se encontró tabla de resumen visible para boletas.")

    header = None
    if rows and any(
        x.upper() in ("TIPO DOCUMENTO", "TOTAL DOCUMENTOS", "MONTO TOTAL", "MONTO NETO", "MONTO IVA")
        for x in rows[0]
    ):
        header = rows[0]

    boleta_row = _find_boletas_row(rows)
    if not boleta_row:
        if DEBUG:
            print("[DCV] No se encontró fila de boletas; se omite la captura.")
        return None

    save_path.parent.mkdir(parents=True, exist_ok=True)
    with save_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if header:
            w.writerow(header)
        w.writerow(boleta_row)

    if DEBUG:
        print(f"[DCV] Boletas resumen guardado: {save_path.name}")

    return save_path


# ----------------------------
# Public API: descargas/capturas por sección
# ----------------------------
def download_compras_detalles(
    page: Page, storage_dir: Path, company_id: str, year: int, month: int
) -> Optional[DCVArtifact]:
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)

    if not FORCE_DOWNLOAD and _already(manifest, year, month, "compras"):
        return None

    _goto_dcv(page)
    _select_period(page, year, month)
    _consult(page)

    # Por defecto queda en COMPRA; igual aseguramos.
    _go_tab_compra(page)

    _click_descargar_detalles(page)
    save_dir = _month_dir(storage_dir, company_id, year, month)
    saved = _download_from_data_anchor(page, save_dir)

    _mark(manifest, year, month, "compras", str(saved))
    _save_manifest(storage_dir, company_id, manifest)
    return DCVArtifact(year=year, month=month, section="compras", saved_path=saved)


def download_ventas_detalles(
    page: Page, storage_dir: Path, company_id: str, year: int, month: int
) -> Optional[DCVArtifact]:
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)

    if not FORCE_DOWNLOAD and _already(manifest, year, month, "ventas_detalles"):
        return None

    _goto_dcv(page)
    _select_period(page, year, month)
    _consult(page)

    _go_tab_venta(page)

    _click_descargar_detalles(page)
    save_dir = _month_dir(storage_dir, company_id, year, month)
    saved = _download_from_data_anchor(page, save_dir)

    _mark(manifest, year, month, "ventas_detalles", str(saved))
    _save_manifest(storage_dir, company_id, manifest)
    return DCVArtifact(year=year, month=month, section="ventas_detalles", saved_path=saved)


def capture_ventas_boletas_line(
    page: Page, storage_dir: Path, company_id: str, year: int, month: int
) -> Optional[DCVArtifact]:
    """
    Boletas: NO se descarga detalle.
    Se captura la línea del resumen y se guarda como CSV.
    """
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)

    if not FORCE_DOWNLOAD and _already(manifest, year, month, "ventas_boletas_linea"):
        return None

    _goto_dcv(page)
    _select_period(page, year, month)
    _consult(page)

    _go_tab_venta(page)

    save_dir = _month_dir(storage_dir, company_id, year, month)
    save_path = save_dir / f"VENTAS_BOLETAS_RESUMEN_{year}{MONTHS[month]}.csv"
    saved = save_boletas_summary_line(page, save_path)
    if not saved:
        return None

    _mark(manifest, year, month, "ventas_boletas_linea", str(saved))
    _save_manifest(storage_dir, company_id, manifest)
    return DCVArtifact(year=year, month=month, section="ventas_boletas_linea", saved_path=saved)


def download_month_all(page: Page, storage_dir: Path, company_id: str, year: int, month: int) -> list[DCVArtifact]:
    """
    Flujo simple (tu operación estándar):
    1) Seleccionar mes/año
    2) Consultar
    3) Descargar Detalles (COMPRA, tab por defecto)
    4) Ir a VENTA
    5) Descargar Detalles (VENTA)
    6) Capturar boletas (si corresponde)

    Nota: no valida si el CSV es compras/ventas; solo ejecuta y guarda lo que entregue el SII.
    """
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)

    have_compras = (not FORCE_DOWNLOAD) and _already(manifest, year, month, "compras")
    have_ventas = (not FORCE_DOWNLOAD) and _already(manifest, year, month, "ventas_detalles")
    have_boletas = (not FORCE_DOWNLOAD) and _already(manifest, year, month, "ventas_boletas_linea")

    if have_compras and have_ventas and have_boletas:
        return []

    _goto_dcv(page)
    _select_period(page, year, month)
    _consult(page)

    artifacts: list[DCVArtifact] = []
    save_dir = _month_dir(storage_dir, company_id, year, month)

    # 1) COMPRAS (por defecto)
    if not have_compras:
        _go_tab_compra(page)
        _click_descargar_detalles(page)
        page.wait_for_timeout(1000)

    # 2) VENTAS (cambiar al tab apenas se dispara compras)
    if not have_ventas:
        _go_tab_venta(page)
        _click_descargar_detalles(page, clear_existing=False)
        page.wait_for_timeout(1000)
    else:
        _go_tab_venta(page)

    # Guardar archivos DCV con filtrado por nombre para evitar confusiones.
    if not have_compras:
        saved = _download_from_data_anchor_matching(
            page,
            save_dir,
            ["compra", f"{year}{MONTHS[month]}"],
        )
        _mark(manifest, year, month, "compras", str(saved))
        artifacts.append(DCVArtifact(year=year, month=month, section="compras", saved_path=saved))

    if not have_ventas:
        saved = _download_from_data_anchor_matching(
            page,
            save_dir,
            ["venta", f"{year}{MONTHS[month]}"],
        )
        _mark(manifest, year, month, "ventas_detalles", str(saved))
        artifacts.append(DCVArtifact(year=year, month=month, section="ventas_detalles", saved_path=saved))

    # 3) BOLETAS (resumen)
    if not have_boletas:
        save_path = save_dir / f"VENTAS_BOLETAS_RESUMEN_{year}{MONTHS[month]}.csv"
        saved = save_boletas_summary_line(page, save_path)
        if saved:
            _mark(manifest, year, month, "ventas_boletas_linea", str(saved))
            artifacts.append(DCVArtifact(year=year, month=month, section="ventas_boletas_linea", saved_path=saved))

    _save_manifest(storage_dir, company_id, manifest)
    return artifacts
