from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlencode

from playwright.sync_api import Page

MONTHS = {i: f"{i:02d}" for i in range(1, 13)}
BHE_MENU_URL = "https://loa.sii.cl/cgi_IMT/TMBCOC_MenuConsultasContribRec.cgi"


@dataclass
class BHEArtifact:
    year: int
    month: int
    saved_html: Optional[Path] = None
    saved_xls: Optional[Path] = None
    saved_png: Optional[Path] = None


# ----------------------------
# Manifest
# ----------------------------
def _manifest_path(storage_dir: Path, company_id: str) -> Path:
    return storage_dir / "companies" / company_id / "bhe" / "manifest.json"


def _load_manifest(storage_dir: Path, company_id: str) -> Dict:
    mp = _manifest_path(storage_dir, company_id)
    if not mp.exists():
        return {"bhe": {}}
    return json.loads(mp.read_text(encoding="utf-8"))


def _save_manifest(storage_dir: Path, company_id: str, data: Dict) -> None:
    mp = _manifest_path(storage_dir, company_id)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _already(manifest: Dict, year: int, month: int) -> bool:
    """Considera 'descargado' si ya existe HTML (fuente única recomendada) o XLS."""
    y = str(year)
    m = MONTHS[month]
    entry = manifest.get("bhe", {}).get(y, {}).get(m, {})
    return bool(entry.get("html") or entry.get("xls"))


def _mark(manifest: Dict, year: int, month: int, payload: Dict) -> None:
    y = str(year)
    m = MONTHS[month]
    manifest.setdefault("bhe", {}).setdefault(y, {})[m] = payload


def _month_dir(storage_dir: Path, company_id: str, year: int, month: int) -> Path:
    d = storage_dir / "companies" / company_id / "bhe" / str(year) / MONTHS[month]
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------
# URL builder (la que tú diste)
# ----------------------------
def bhe_url(rut_sin_dv: str, year: int, month: int, dv_arrastre: int = 2, pagina: int = 0) -> str:
    base = "https://loa.sii.cl/cgi_IMT/TMBCOC_InformeMensualBheRec.cgi"
    qs = {
        "cbanoinformemensual": str(year),
        "cbmesinformemensual": MONTHS[month],
        "dv_arrastre": str(dv_arrastre),
        "pagina_solicitada": str(pagina),
        "rut_arrastre": str(rut_sin_dv),
    }
    return f"{base}?{urlencode(qs)}"


def _is_bhe_error(html: str) -> bool:
    text = (html or "").lower()
    return "host no definido" in text or "no ha sido posible completar su solicitud" in text


def _open_bhe_report_from_menu(page: Page, year: int, month: int) -> None:
    """
    Navega al menú de BHE y consulta el informe mensual.
    Esto asegura la redirección/session requerida por el SII.
    """
    page.goto(BHE_MENU_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    month_sel = page.locator("select[name='cbmesinformemensual']").first
    year_sel = page.locator("select[name='cbanoinformemensual']").first

    month_sel.wait_for(state="visible", timeout=15000)
    month_sel.select_option(value=MONTHS[month])
    if year_sel.count():
        year_sel.select_option(value=str(year))

    btn = page.locator(
        "#cmdconsultar1, input#cmdconsultar1, input[name='cmdconsultar1'], input[type='button'][value*='consultar' i]"
    ).first
    btn.wait_for(state="visible", timeout=15000)
    btn.click()
    page.wait_for_timeout(800)


# ----------------------------
# (Opcional) bajar XLS
# ----------------------------
def _click_planilla_and_download_xls(page: Page, out_dir: Path, year: int, month: int) -> Path:
    """
    Click en: <input type="button" name="planilla" value="Ver informe como planilla electrónica"...>
    y captura el archivo .xls descargado.
    """
    btn = page.locator(
        "input[type='button'][name='planilla'][value*='planilla' i], "
        "input[type='button'][value*='planilla electr' i]"
    ).first
    btn.wait_for(state="visible", timeout=15000)

    out_dir.mkdir(parents=True, exist_ok=True)

    with page.expect_download(timeout=60000) as dl_info:
        btn.click()

    dl = dl_info.value
    suggested = dl.suggested_filename or f"BHE_{year}{MONTHS[month]}.xls"
    if not suggested.lower().endswith((".xls", ".xlsx")):
        suggested += ".xls"

    save_path = out_dir / suggested
    dl.save_as(str(save_path))
    return save_path


def fetch_bhe_month(
    page: Page,
    storage_dir: Path,
    company_id: str,
    rut_sin_dv: str,
    year: int,
    month: int,
    evidence: bool = False,
    download_xls: bool = False,
) -> Optional[BHEArtifact]:
    """
    Abre el informe mensual de Boletas de Honorarios Electrónicas (RECIBIDAS).

    ✅ Recomendación operativa (para minimizar carga y fallas):
    - Guardar y procesar SOLO el HTML (trae totales 'liquido1/liquido3/liquido4').
    - Descargar XLS solo si realmente lo necesitas (download_xls=True).

    Guarda HTML (siempre), opcional PNG (evidence=True) y opcional XLS (download_xls=True).
    Registra manifest para evitar descargas repetidas.
    """
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)
    if _already(manifest, year, month):
        return None

    out_dir = _month_dir(storage_dir, company_id, year, month)

    # URL directa (requiere sesión activa)
    url = bhe_url(rut_sin_dv=rut_sin_dv, year=year, month=month, dv_arrastre=1)
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(500)

    art = BHEArtifact(year=year, month=month)

    # HTML (fuente única)
    try:
        html_path = out_dir / f"BHE_{year}{MONTHS[month]}.html"
        html_path.write_text(page.content(), encoding="utf-8")
        art.saved_html = html_path
    except Exception:
        art.saved_html = None

    # Evidencia opcional
    if evidence:
        try:
            png = out_dir / "bhe_page.png"
            page.screenshot(path=str(png), full_page=True)
            art.saved_png = png
        except Exception:
            art.saved_png = None

    # XLS opcional (no recomendado por defecto)
    if download_xls:
        art.saved_xls = _click_planilla_and_download_xls(page, out_dir, year, month)

    payload = {
        "url": page.url or url,
        "html": str(art.saved_html) if art.saved_html else None,
        "xls": str(art.saved_xls) if art.saved_xls else None,
        "png": str(art.saved_png) if art.saved_png else None,
    }
    _mark(manifest, year, month, payload)
    _save_manifest(storage_dir, company_id, manifest)

    return art
