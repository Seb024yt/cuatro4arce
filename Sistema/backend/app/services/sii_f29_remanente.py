from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from playwright.sync_api import Page

MONTH_LABELS = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

F29_RFI_URL = "https://www4.sii.cl/rfiInternet/consulta/index.html#rfiSelFormularioPeriodo"


@dataclass
class RemanenteResult:
    target_year: int
    target_month: int
    prev_year: int
    prev_month: int
    folio: Optional[str]
    codigo_77: Optional[int]
    saved_json: Path
    saved_png_results: Optional[Path] = None
    saved_png_codigo77: Optional[Path] = None
    saved_html_results: Optional[Path] = None
    saved_html_compacto: Optional[Path] = None
    compacto_url: Optional[str] = None


# ----------------------------
# Manifest
# ----------------------------
def _manifest_path(storage_dir: Path, company_id: str) -> Path:
    return storage_dir / "companies" / company_id / "f29_remanente" / "manifest.json"

def _load_manifest(storage_dir: Path, company_id: str) -> Dict:
    mp = _manifest_path(storage_dir, company_id)
    if not mp.exists():
        return {"remanente": {}}
    return json.loads(mp.read_text(encoding="utf-8"))

def _save_manifest(storage_dir: Path, company_id: str, data: Dict) -> None:
    mp = _manifest_path(storage_dir, company_id)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _already(manifest: Dict, target_year: int, target_month: int) -> bool:
    y = str(target_year)
    m = f"{target_month:02d}"
    return bool(manifest.get("remanente", {}).get(y, {}).get(m))

def _mark(manifest: Dict, target_year: int, target_month: int, payload: Dict) -> None:
    y = str(target_year)
    m = f"{target_month:02d}"
    manifest.setdefault("remanente", {}).setdefault(y, {})[m] = payload

def _out_dir(storage_dir: Path, company_id: str, target_year: int, target_month: int) -> Path:
    d = storage_dir / "companies" / company_id / "f29_remanente" / str(target_year) / f"{target_month:02d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ----------------------------
# Helpers
# ----------------------------
def _prev_period(year: int, month: int) -> Tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1

def _to_int_money(s: str) -> Optional[int]:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None

def _select_by_label(page: Page, select_locator: str, label: str) -> None:
    sel = page.locator(select_locator).first
    sel.wait_for(state="visible", timeout=20000)
    sel.select_option(label=label)

def _click(page: Page, selector: str, timeout_ms: int = 20000) -> None:
    loc = page.locator(selector).first
    loc.wait_for(state="visible", timeout=timeout_ms)
    loc.click()

def _wait_results_loaded(page: Page) -> None:
    page.locator("text=RESULTADOS DE LA BÚSQUEDA").first.wait_for(timeout=25000)

def _find_folio_link(page: Page) -> Optional[str]:
    a = page.locator("a", has_text=re.compile(r"^\d{6,}$")).first
    if a.count() == 0:
        return None
    try:
        if not a.is_visible():
            return None
        return (a.inner_text() or "").strip()
    except Exception:
        return None

def _open_folio_options(page: Page) -> None:
    a = page.locator("a", has_text=re.compile(r"^\d{6,}$")).first
    a.wait_for(state="visible", timeout=20000)
    a.click()
    page.wait_for_timeout(800)

def _open_compacto_popup(page: Page) -> Page:
    """
    Click en 'Formulario Compacto' y captura la página que se abre (popup/tab).
    Si no se abre popup y navega en la misma página, retorna page.
    """
    btn = page.locator("button:has-text('Formulario Compacto')").first
    btn.wait_for(state="visible", timeout=20000)

    # Intento 1: popup (lo que tú describes)
    try:
        with page.expect_popup(timeout=15000) as pop:
            btn.click()
        new_page = pop.value
        new_page.wait_for_load_state("domcontentloaded", timeout=30000)
        return new_page
    except Exception:
        # Intento 2: navegación en misma página
        btn.click()
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        return page

def _compacto_has_codigo_77(compacto_page: Page) -> bool:
    frame = compacto_page.frame_locator("#printingFrame")
    # si no existe iframe todavía, fallará el wait_for -> lo capturamos arriba
    loc = frame.locator("td.celda-codigo", has_text=re.compile(r"^\s*77\s*$"))
    if loc.count() > 0:
        return True
    loc2 = frame.locator("td", has_text=re.compile(r"^\s*77\s*$"))
    return loc2.count() > 0

def _scroll_to_codigo_77_in_compacto(compacto_page: Page) -> None:
    frame = compacto_page.frame_locator("#printingFrame")

    # Esperar el iframe/render inicial
    # (el locator interno fuerza el acceso al frame)
    target = frame.locator("td.celda-codigo", has_text=re.compile(r"^\s*77\s*$")).first
    if target.count() == 0:
        target = frame.locator("td", has_text=re.compile(r"^\s*77\s*$")).first

    # Si no existe, no hacemos scroll (remanente no presente)
    if target.count() == 0:
        return

    target.wait_for(state="visible", timeout=30000)
    target.scroll_into_view_if_needed(timeout=30000)
    compacto_page.wait_for_timeout(700)

def _extract_codigo_77_from_compacto(compacto_page: Page) -> Optional[int]:
    frame = compacto_page.frame_locator("#printingFrame")

    codigo_cell = frame.locator("td.celda-codigo", has_text=re.compile(r"^\s*77\s*$")).first
    if codigo_cell.count() == 0:
        codigo_cell = frame.locator("td", has_text=re.compile(r"^\s*77\s*$")).first

    if codigo_cell.count() == 0:
        return None

    row = codigo_cell.locator("xpath=ancestor::tr[1]")

    # Monto suele estar en tabla_td_fixed_b_right
    value_cell = row.locator("td.tabla_td_fixed_b_right").first
    txt = None
    if value_cell.count() > 0:
        try:
            txt = (value_cell.inner_text() or "").strip()
        except Exception:
            txt = None

    # fallback: último td
    if not txt:
        try:
            tds = row.locator("td")
            if tds.count() > 0:
                txt = (tds.nth(tds.count() - 1).inner_text() or "").strip()
        except Exception:
            txt = None

    return _to_int_money(txt or "")


# ----------------------------
# Main
# ----------------------------
def fetch_remanente_prev_month(
    page: Page,
    storage_dir: Path,
    company_id: str,
    target_year: int,
    target_month: int
) -> Optional[RemanenteResult]:
    """
    Para un periodo objetivo (target_year/target_month), busca el remanente (código 77)
    del periodo anterior (prev_year/prev_month) vía rfiInternet.
    """
    storage_dir = Path(storage_dir)
    manifest = _load_manifest(storage_dir, company_id)
    if _already(manifest, target_year, target_month):
        return None

    prev_year, prev_month = _prev_period(target_year, target_month)
    out_dir = _out_dir(storage_dir, company_id, target_year, target_month)

    # 0) Entrar a la consulta
    page.goto(F29_RFI_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1200)

    # 1) Seleccionar Formulario 29 / Año / Mes por LABEL visible
    # Orden observado (por tus capturas):
    #   nth=0 formulario
    #   nth=1 año
    #   nth=2 mes
    _select_by_label(page, "select.gwt-ListBox >> nth=0", "Formulario 29")
    _select_by_label(page, "select.gwt-ListBox >> nth=1", str(prev_year))
    _select_by_label(page, "select.gwt-ListBox >> nth=2", MONTH_LABELS[prev_month])

    # 2) Buscar
    _click(page, "button:has-text('Buscar Datos Ingresados')", timeout_ms=25000)
    _wait_results_loaded(page)

    # Evidencia resultados
    saved_html_results = None
    try:
        saved_html_results = out_dir / f"RESULTADOS_{prev_year}{prev_month:02d}.html"
        saved_html_results.write_text(page.content(), encoding="utf-8")
    except Exception:
        pass

    folio = _find_folio_link(page)
    codigo_77 = None
    saved_html_compacto = None
    compacto_url = None

    # 3) Si hay folio -> opciones -> Formulario Compacto (popup)
    if folio:
        _open_folio_options(page)

        compacto_page = _open_compacto_popup(page)
        compacto_url = compacto_page.url

        # 4) Esperar que cargue printingFrame (o al menos el DOM del compacto)
        compacto_page.wait_for_timeout(1500)

        # Guardar HTML compacto (útil para auditoría y ajustes futuros)
        try:
            saved_html_compacto = out_dir / f"F29_COMPACTO_{prev_year}{prev_month:02d}.html"
            saved_html_compacto.write_text(compacto_page.content(), encoding="utf-8")
        except Exception:
            pass

        # 5) Scroll al código 77 (si existe) y extracción
        _scroll_to_codigo_77_in_compacto(compacto_page)
        codigo_77 = _extract_codigo_77_from_compacto(compacto_page)

        # Si se abrió popup, lo cerramos para no acumular pestañas
        try:
            if compacto_page is not page:
                compacto_page.close()
        except Exception:
            pass

    # 7) Guardar resultado JSON
    result_payload = {
        "target_period": {"year": target_year, "month": target_month},
        "prev_period": {"year": prev_year, "month": prev_month},
        "folio": folio,
        "codigo_77_remanente": codigo_77,
        "results_url": page.url,
        "compacto_url": compacto_url,
        "evidence": {
            "html_results": str(saved_html_results) if saved_html_results else None,
            "html_compacto": str(saved_html_compacto) if saved_html_compacto else None,
        },
    }

    saved_json = out_dir / f"remanente_prev_{prev_year}{prev_month:02d}_para_{target_year}{target_month:02d}.json"
    saved_json.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8) Marcar manifest (aunque no haya folio o no exista 77)
    _mark(manifest, target_year, target_month, {
        "prev": f"{prev_year}{prev_month:02d}",
        "folio": folio,
        "codigo_77": codigo_77,
        "json": str(saved_json),
    })
    _save_manifest(storage_dir, company_id, manifest)

    return RemanenteResult(
        target_year=target_year,
        target_month=target_month,
        prev_year=prev_year,
        prev_month=prev_month,
        folio=folio,
        codigo_77=codigo_77,
        saved_json=saved_json,
        saved_html_results=saved_html_results,
        saved_html_compacto=saved_html_compacto,
        compacto_url=compacto_url,
    )
