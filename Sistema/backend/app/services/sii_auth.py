# backend/app/services/sii_auth.py
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from playwright.sync_api import (
    Page,
    Browser,
    BrowserContext,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

# Carga variables desde .env aunque el script se ejecute desde otra carpeta
def _load_dotenv_from_ancestors() -> Optional[Path]:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for base in candidates:
        env_path = base / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            return env_path
    load_dotenv()
    return None


_ENV_PATH = _load_dotenv_from_ancestors()
DEFAULT_START_URL = os.getenv("SII_AUTH_URL", "https://www.sii.cl/")
DISMISS_ACTUALIZAR_DATOS_MODAL = True


# =========================
# Utilidades base
# =========================

def normalize_rut(rut: str) -> str:
    """
    Normaliza RUT a formato: 12345678-9 (sin puntos, con guion).
    Acepta entradas como: 12.345.678-9 / 123456789 / 12345678-9
    """
    if not rut:
        return rut
    r = rut.strip().upper().replace(".", "").replace(" ", "")
    if "-" in r:
        num, dv = r.split("-", 1)
        num = re.sub(r"\D", "", num)
        dv = re.sub(r"[^0-9K]", "", dv)
        return f"{num}-{dv}"
    # sin guion
    r = re.sub(r"[^0-9K]", "", r)
    if len(r) >= 2:
        return f"{r[:-1]}-{r[-1]}"
    return r


def company_id_from_rut(rut: str) -> str:
    """
    Company ID estable para storage. Por defecto: solo dÃ­gitos del RUT (sin DV),
    porque tu storage actual usa folders tipo: storage/companies/897528002
    (ejemplo de la captura).
    """
    r = normalize_rut(rut)
    if "-" not in r:
        return re.sub(r"[^0-9K-]", "", r)
    num, dv = r.split("-", 1)
    num = re.sub(r"\D", "", num)
    dv = re.sub(r"[^0-9K]", "", dv.upper())
    return f"{num}-{dv}"


def company_id_legacy_from_rut(rut: str) -> str:
    """
    Legacy company_id (solo dígitos sin DV). Se usa como fallback
    para leer estados ya guardados con el esquema anterior.
    """
    r = normalize_rut(rut)
    num = r.split("-", 1)[0] if "-" in r else r
    return re.sub(r"\D", "", num)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# Persistencia perfil empresa
# =========================

def save_company_profile(
    *,
    storage_root: Path,
    company_id: str,
    rut: str,
    razon_social: Optional[str],
    source_url: Optional[str],
    password: Optional[str] = None,
) -> Path:
    """
    Guarda perfil empresa en:
      storage/companies/<company_id>/profile.json
    """
    company_dir = storage_root / "companies" / str(company_id)
    ensure_dir(company_dir)

    profile_path = company_dir / "profile.json"
    payload = {
        "company_id": str(company_id),
        "rut": normalize_rut(rut),
        "razon_social": razon_social,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "password": password,
    }
    write_json(profile_path, payload)
    return profile_path


# =========================
# Modal "Actualizar datos"
# =========================

def dismiss_actualizar_datos_modal(page: Page, timeout_ms: int = 3500) -> bool:
    """
    Si aparece el modal "Antes de continuar" que pide actualizar datos,
    clickea "ACTUALIZAR MÃS TARDE" y espera a que desaparezca.
    Retorna True si lo cerrÃ³, False si no apareciÃ³.
    """
    btn = page.locator(
        "#btnActualizarMasTarde, button#btnActualizarMasTarde, button:has-text('ACTUALIZAR MÃS TARDE')"
    ).first

    try:
        btn.wait_for(state="visible", timeout=timeout_ms)
        btn.click(timeout=timeout_ms)

        # Espera razonable a que el dialog deje de interceptar
        # (no siempre el contenedor es el mismo, por eso fallback).
        modal = page.locator(".modal-dialog, .modal-content, #myModal, [role='dialog']").first
        try:
            modal.wait_for(state="hidden", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            btn.wait_for(state="hidden", timeout=timeout_ms)

        return True
    except PlaywrightTimeoutError:
        return False


# =========================
# Extractor RazÃ³n Social
# =========================

def extract_razon_social(page: Page, timeout_ms: int = 5000) -> Optional[str]:
    """
    Extrae RazÃ³n Social desde la pantalla Mi SII post-login y post-modal.

    Prioridad:
      1) #nameCntrInfo2 (segÃºn tu DOM)
      2) "Nombre o razÃ³n social" + siguiente <p class='info2'>
      3) Regex sobre body (fallback)
    """
    # 1) Selector directo (varía: #nameCntrInfo2 o #nameCntr)
    loc = page.locator("#nameCntrInfo2, p#nameCntrInfo2, #nameCntr, p#nameCntr").first
    try:
        loc.wait_for(state="visible", timeout=timeout_ms)
        txt = (loc.text_content() or "").strip()
        if txt:
            return _clean_one_line(txt)
    except PlaywrightTimeoutError:
        pass

    # 2) Fallback por label
    try:
        label = page.locator("text=/Nombre\\s+o\\s+raz[oÃ³]n\\s+social/i").first
        if label.count() > 0:
            value = label.locator("xpath=following::p[contains(@class,'info2')][1]").first
            value.wait_for(state="visible", timeout=timeout_ms)
            txt = (value.text_content() or "").strip()
            if txt:
                return _clean_one_line(txt)
    except Exception:
        pass

    # 3) Fallback regex en body
    try:
        body_text = page.locator("body").inner_text(timeout=timeout_ms)
        m = re.search(r"Nombre\s+o\s+raz[oÃ³]n\s+social\s*[:\-]?\s*(.+)", body_text, re.I)
        if m:
            line = _clean_one_line(m.group(1))
            if line and 3 <= len(line) <= 120:
                return line
    except Exception:
        pass

    return None


def _clean_one_line(txt: str) -> str:
    txt = re.sub(r"[\r\n\t]+", " ", txt).strip()
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt


# =========================
# Login + Save State
# =========================

@dataclass
class LoginResult:
    company_id: str
    rut: str
    razon_social: Optional[str]
    state_path: Path
    profile_path: Path
    closed_modal_actualizar_datos: bool
    final_url: str


class SiiLoginError(RuntimeError):
    pass


def login_and_save_state(
    *,
    rut: str,
    clave: str,
    storage_root: Path = Path("storage"),
    company_id: Optional[str] = None,
    headless: bool = True,
    slow_mo_ms: int = 0,
    timeout_ms: int = 30000,
    evidence: bool = False,
    start_url: Optional[str] = None,
) -> LoginResult:
    """
    Flujo corporativo:
      1) Navega a SII
      2) Login
      3) Si aparece modal "Actualizar datos", clic "Actualizar mÃ¡s tarde"
      4) Extrae RazÃ³n Social (Mi SII)
      5) Guarda storage_state (playwright_state/state.json)
      6) Guarda profile.json (incluye razÃ³n social)

    Persistencia:
      storage/companies/<company_id>/playwright_state/state.json
      storage/companies/<company_id>/profile.json
      storage/companies/<company_id>/evidence/* (si evidence=True)
    """
    rut_norm = normalize_rut(rut)
    cid = company_id or company_id_from_rut(rut_norm)

    company_dir = storage_root / "companies" / str(cid)
    state_dir = company_dir / "playwright_state"
    evidence_dir = company_dir / "evidence"

    ensure_dir(state_dir)
    if evidence:
        ensure_dir(evidence_dir)

    state_path = state_dir / "state.json"

    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=headless, slow_mo=slow_mo_ms)
        context: BrowserContext = browser.new_context()
        page: Page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            # 1) Entrada
            effective_start_url = start_url or DEFAULT_START_URL
            page.goto(effective_start_url, wait_until="domcontentloaded")

            # 2) Login (selectores tolerantes)
            _perform_login(page, rut_norm, clave)

            # Espera post-login
            page.wait_for_load_state("networkidle")

            # (Opcional) evidencia post-login antes del modal
            if evidence:
                page.screenshot(path=str(evidence_dir / "post_login_before_modal.png"), full_page=True)

            # 3) Modal "Actualizar datos" (si aparece)
            closed = False
            if DISMISS_ACTUALIZAR_DATOS_MODAL:
                closed = dismiss_actualizar_datos_modal(page)

            # (Opcional) evidencia post-modal
            if evidence:
                page.screenshot(path=str(evidence_dir / "post_login_after_modal.png"), full_page=True)

            # 4) Extraer razÃ³n social
            razon_social = extract_razon_social(page)

            # 5) Guardar estado Playwright
            context.storage_state(path=str(state_path))

            # 6) Guardar perfil empresa
            profile_path = save_company_profile(
                storage_root=storage_root,
                company_id=cid,
                rut=rut_norm,
                razon_social=razon_social,
                source_url=page.url,
                password=clave,
            )

            return LoginResult(
                company_id=cid,
                rut=rut_norm,
                razon_social=razon_social,
                state_path=state_path,
                profile_path=profile_path,
                closed_modal_actualizar_datos=closed,
                final_url=page.url,
            )

        except Exception as e:
            # Evidencia de falla para tuning
            if evidence:
                try:
                    page.screenshot(path=str(evidence_dir / "error.png"), full_page=True)
                except Exception:
                    pass
            raise

        finally:
            context.close()
            browser.close()


def _perform_login(page: Page, rut: str, clave: str) -> None:
    """
    Login tolerante a cambios menores de UI:
    - Busca input rut por name/id/placeholder conteniendo "rut"
    - Busca password por type=password o name/id conteniendo "clave"
    - Intenta click en botÃ³n Ingresar/Entrar/Continuar o submit por Enter
    """
    # Asegura que haya inputs (en algunos flujos el login estÃ¡ en otra URL/overlay)
    # Si tu login real navega a otra URL, aquÃ­ puedes insertar el paso de click "Mi SII" si aplica.

    # Input RUT
    rut_locator = page.locator(
        "input:not([type='hidden'])[name*=\"rut\" i], "
        "input:not([type='hidden'])[id*=\"rut\" i], "
        "input:not([type='hidden'])[placeholder*=\"rut\" i]"
    ).first
    try:
        rut_locator.wait_for(state="visible", timeout=8000)
    except PlaywrightTimeoutError as e:
        raise SiiLoginError("No se encontrÃ³ input de RUT visible para login.") from e

    rut_locator.fill(rut)

    # Input clave
    pw_locator = page.locator(
        'input[type="password"], input[name*="clave" i], input[id*="clave" i], input[placeholder*="clave" i]'
    ).first
    try:
        pw_locator.wait_for(state="visible", timeout=8000)
    except PlaywrightTimeoutError as e:
        raise SiiLoginError("No se encontrÃ³ input de clave (password) visible para login.") from e

    pw_locator.fill(clave)

    # BotÃ³n submit
    btn = page.locator(
        "button:has-text('Ingresar'), button:has-text('Entrar'), button:has-text('Continuar'), "
        "input[type='submit'], button[type='submit']"
    ).first

    # Estrategia: click si existe, sino Enter
    try:
        if btn.count() > 0:
            btn.click()
        else:
            pw_locator.press("Enter")
    except Exception:
        # fallback: Enter
        pw_locator.press("Enter")

    # SeÃ±al bÃ¡sica de navegaciÃ³n/cambio de estado
    # (si tu portal no navega, igual esperamos carga de red)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except PlaywrightTimeoutError:
        # No siempre navega; no lo tratamos como fatal
        pass

