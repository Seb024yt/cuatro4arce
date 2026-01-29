from __future__ import annotations

import csv
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

LOGGER = logging.getLogger(__name__)
SILENCE_INCONSISTENCIES = os.getenv("SII_PDF_SILENCE_INCONSISTENCIES", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "y",
)

PURPLE = colors.HexColor("#5B2C83")
GRAY = colors.HexColor("#4B5563")
LIGHT_GRAY = colors.HexColor("#E5E7EB")

MONTH_LABELS = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}

VENTAS_LABELS = {
    33: "Factura electronica",
    34: "Factura exenta / no afecta",
    61: "Nota de credito electronica",
    56: "Nota de debito electronica",
    51: "Nota de debito (compatibilidad)",
    39: "Boleta afecta electronica",
    48: "Boleta medio electronico",
    41: "Boleta exenta electronica",
    43: "Liquidacion de factura",
}

COMPRAS_LABELS = {
    33: "Factura electronica",
    34: "Factura exenta / no afecta",
    61: "Nota de credito electronica",
    56: "Nota de debito electronica",
    45: "Factura de compra",
}

NOTE_CREDITO_CODES = {60, 61}
NOTE_DEBITO_CODES = {55, 56, 51}


@dataclass
class SummaryItem:
    concepto: str
    neto: Optional[int]
    iva: Optional[int]
    total: Optional[int]
    code: Optional[int] = None


@dataclass
class PPMSummary:
    base: Optional[int]
    factor: Optional[float]
    pagado: Optional[int]


@dataclass
class HonorariosSummary:
    bruto: Optional[int]
    retenido: Optional[int]
    pagado: Optional[int]


def _normalize_col(name: str) -> str:
    if name is None:
        return ""
    name = str(name).strip().lower()
    name = "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    )
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name


def _alias_map() -> Dict[str, Tuple[str, ...]]:
    return {
        "codigo_tipo_documento": (
            "tipodoc",
            "tipodocumento",
            "tipodte",
            "codigotipo",
            "codigo",
            "tipodocum",
            "tipodocumentocompra",
            "tipodocumentoventa",
        ),
        "neto": (
            "neto",
            "mntneto",
            "montoneto",
            "montoafecto",
            "montonetoafecto",
            "montonetoaf",
        ),
        "iva": (
            "iva",
            "mntiva",
            "montoiva",
            "montoivarecuperable",
            "ivarecuperable",
            "ivacredito",
            "ivadebito",
        ),
        "total": (
            "total",
            "mnttotal",
            "montototal",
        ),
        "exento": (
            "exento",
            "mntexento",
            "montoexento",
            "montoexento_noafecto",
            "montoexentonoafecto",
            "montoexentoynoafecto",
        ),
        "fecha_emision": (
            "fchemis",
            "fechaemision",
            "fechadocto",
            "fechadocumento",
            "fecha",
        ),
    }


def _to_int_money(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(round(value))
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
    if "-" in s:
        negative = True
    digits = re.sub(r"[^\d]", "", s)
    if not digits:
        return None
    try:
        n = int(digits)
    except Exception:
        return None
    return -n if negative else n


def _apply_sign(value: Optional[int], sign: int) -> Optional[int]:
    if value is None:
        return None
    if value < 0:
        return value
    return value * sign


def _sign_for_code(code: int) -> int:
    if code in NOTE_CREDITO_CODES:
        return -1
    if code in NOTE_DEBITO_CODES:
        return 1
    return 1


def _read_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe archivo: {path}")
    suffix = path.suffix.lower()
    if suffix in (".csv", ".txt"):
        # Algunos CSV del SII traen una columna extra vacía al final de cada fila.
        # Pandas desplaza los datos cuando el número de campos no coincide.
        if _csv_needs_loose_read(path):
            df = _read_csv_loose(path)
        else:
            try:
                df = pd.read_csv(path, dtype=str, sep=None, engine="python")
            except Exception:
                try:
                    df = pd.read_csv(path, dtype=str, sep=";")
                except Exception:
                    df = pd.read_csv(path, dtype=str, sep=",")
    else:
        df = pd.read_excel(path, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _csv_needs_loose_read(path: Path, sample_lines: int = 200) -> bool:
    """
    Detecta filas con más campos que el header (por delimitadores extra al final).
    """
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            first_line = f.readline()
            if not first_line:
                return False
            delim = ";" if ";" in first_line else ("," if "," in first_line else None)
            if not delim:
                return False
            header = first_line.rstrip("\n").split(delim)
            header_len = len(header)
            if header_len == 0:
                return False
            for i, line in enumerate(f):
                if i >= sample_lines:
                    break
                row_len = len(line.rstrip("\n").split(delim))
                if row_len > header_len:
                    return True
        return False
    except Exception:
        return False


def _read_csv_loose(path: Path) -> pd.DataFrame:
    """
    Lee CSV recortando/paddeando filas al largo del header.
    """
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        first_line = f.readline()
        delim = ";" if ";" in first_line else ("," if "," in first_line else ",")
        header = first_line.rstrip("\n").split(delim)
        rows: list[list[str]] = []
        reader = csv.reader(f, delimiter=delim)
        for row in reader:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            elif len(row) > len(header):
                row = row[: len(header)]
            rows.append(row)
    return pd.DataFrame(rows, columns=header)


def _resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    aliases = _alias_map()
    normalized = {_normalize_col(c): c for c in df.columns}
    resolved: Dict[str, str] = {}
    for key, names in aliases.items():
        for name in names:
            if name in normalized:
                resolved[key] = normalized[name]
                break
    return resolved


def _parse_period_filter(df: pd.DataFrame, col: str, year: int, month: int) -> pd.DataFrame:
    if col not in df.columns:
        return df
    try:
        dates = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
    except Exception:
        return df
    mask = (dates.dt.year == year) & (dates.dt.month == month)
    return df.loc[mask].copy()


def _summarize_dcv(
    path: Path,
    year: Optional[int] = None,
    month: Optional[int] = None,
    include_exento_in_neto: bool = False,
) -> Tuple[Dict[int, Dict[str, Optional[int]]], Dict[str, Optional[int]]]:
    df = _read_dataframe(path)
    cols = _resolve_columns(df)
    missing = [k for k in ("codigo_tipo_documento", "neto") if k not in cols]
    if missing:
        raise ValueError(f"Columnas requeridas no encontradas en {path}: {missing}")

    if "fecha_emision" in cols and year and month:
        # Si el archivo ya es mensual (nombre contiene AAAAMM), no filtramos por fecha.
        # El SII puede incluir documentos de otros meses que igual cuentan en el período.
        period_tag = f"{year}{month:02d}"
        if period_tag not in path.name:
            df = _parse_period_filter(df, cols["fecha_emision"], year, month)

    code_col = cols["codigo_tipo_documento"]
    neto_col = cols.get("neto")
    iva_col = cols.get("iva")
    total_col = cols.get("total")
    exento_col = cols.get("exento")

    summary: Dict[int, Dict[str, Optional[int]]] = {}
    for _, row in df.iterrows():
        code_raw = row.get(code_col)
        try:
            code = int(re.sub(r"[^\d]", "", str(code_raw)))
        except Exception:
            continue
        sign = _sign_for_code(code)
        neto = _apply_sign(_to_int_money(row.get(neto_col)), sign) if neto_col else None
        iva = _apply_sign(_to_int_money(row.get(iva_col)), sign) if iva_col else None
        total = _apply_sign(_to_int_money(row.get(total_col)), sign) if total_col else None
        exento = _apply_sign(_to_int_money(row.get(exento_col)), sign) if exento_col else None

        if include_exento_in_neto and exento is not None:
            neto = (neto or 0) + exento

        if total is None and neto is not None and iva is not None:
            total = neto + iva
        if total is not None and neto is not None and iva is not None:
            if abs(total - (neto + iva)) > 1:
                if not SILENCE_INCONSISTENCIES:
                    LOGGER.warning("Total inconsistente en %s: %s", path.name, row.to_dict())

        bucket = summary.setdefault(code, {"neto": 0, "iva": 0, "total": 0})
        if neto is not None:
            bucket["neto"] = (bucket["neto"] or 0) + neto
        if iva is not None:
            bucket["iva"] = (bucket["iva"] or 0) + iva
        if total is not None:
            bucket["total"] = (bucket["total"] or 0) + total

    totals = {
        "neto": sum((v["neto"] or 0) for v in summary.values()) if summary else 0,
        "iva": sum((v["iva"] or 0) for v in summary.values()) if summary else 0,
        "total": sum((v["total"] or 0) for v in summary.values()) if summary else 0,
    }
    return summary, totals


def _detect_boletas_path(ventas_path: Path) -> Optional[Path]:
    if ventas_path.is_dir():
        matches = sorted(ventas_path.glob("VENTAS_BOLETAS_RESUMEN_*.csv"))
        return matches[-1] if matches else None
    if "BOLETAS" in ventas_path.name.upper():
        return ventas_path
    matches = sorted(ventas_path.parent.glob("VENTAS_BOLETAS_RESUMEN_*.csv"))
    return matches[-1] if matches else None


def _read_boletas_summary(boletas_path: Path) -> Optional[Dict[str, int]]:
    if not boletas_path or not boletas_path.exists():
        return None
    df = _read_dataframe(boletas_path)
    cols = _resolve_columns(df)
    if "neto" not in cols or "iva" not in cols or "total" not in cols:
        return None
    neto = _to_int_money(df[cols["neto"]].iloc[0])
    iva = _to_int_money(df[cols["iva"]].iloc[0])
    total = _to_int_money(df[cols["total"]].iloc[0])
    return {"neto": neto or 0, "iva": iva or 0, "total": total or 0}


def _read_bhe_summary(path: Optional[Path]) -> HonorariosSummary:
    if not path or not path.exists():
        return HonorariosSummary(bruto=None, retenido=None, pagado=None)
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm", ".txt"):
        text = path.read_text(encoding="latin-1", errors="ignore")
        bruto = _to_int_money(_extract_hidden_value(text, "liquido1"))
        retenido = _to_int_money(_extract_hidden_value(text, "liquido3"))
        pagado = _to_int_money(_extract_hidden_value(text, "liquido4"))
        if bruto is None or retenido is None or pagado is None:
            totals = _extract_bhe_totals_row(text)
            if totals:
                return totals
        return HonorariosSummary(bruto=bruto, retenido=retenido, pagado=pagado)

    # Algunos .xls del SII en realidad son HTML. Parsearlos directo evita problemas con pandas.
    try:
        text = path.read_text(encoding="latin-1", errors="ignore")
    except Exception:
        text = None
    if text and "<table" in text.lower():
        totals = _extract_bhe_totals_row(text)
        if totals:
            return totals

    try:
        df = _read_dataframe(path)
    except Exception:
        df = None

    def _fallback_from_html(text: str) -> Optional[HonorariosSummary]:
        bruto = _to_int_money(_extract_hidden_value(text, "liquido1"))
        retenido = _to_int_money(_extract_hidden_value(text, "liquido3"))
        pagado = _to_int_money(_extract_hidden_value(text, "liquido4"))
        if bruto or retenido or pagado:
            return HonorariosSummary(bruto=bruto, retenido=retenido, pagado=pagado)
        totals = _extract_bhe_totals_row(text)
        if totals:
            return totals
        try:
            tables = pd.read_html(text)
        except Exception:
            return None
        if not tables:
            return None
        df_html = None
        for tbl in tables:
            tbl = _flatten_columns(tbl)
            if _find_alt_column_relaxed(tbl, ("brutos", "bruto")) and _find_alt_column_relaxed(
                tbl, ("retenido", "retencion", "retenciones")
            ):
                df_html = tbl
                break
        if df_html is None:
            df_html = _flatten_columns(tables[1] if len(tables) > 1 else tables[0])
        bruto_col = _find_alt_column_relaxed(df_html, ("brutos", "bruto"))
        retenido_col = _find_alt_column_relaxed(df_html, ("retenido", "retencion", "retenciones"))
        pagado_col = _find_alt_column_relaxed(df_html, ("pagado", "liquido", "liquidoapagar", "liquidoapago"))
        if not (bruto_col or retenido_col or pagado_col):
            return None

        estado_col = _find_alt_column_relaxed(df_html, ("estado",))
        if estado_col:
            estado = df_html[estado_col].astype(str).str.strip().str.upper()
            df_html = df_html[estado == "VIGENTE"]

        return HonorariosSummary(
            bruto=_sum_column(df_html, bruto_col),
            retenido=_sum_column(df_html, retenido_col),
            pagado=_sum_column(df_html, pagado_col),
        )

    if df is None:
        text = path.read_text(encoding="latin-1", errors="ignore")
        fallback = _fallback_from_html(text)
        return fallback or HonorariosSummary(bruto=None, retenido=None, pagado=None)

    cols = _resolve_columns(df)
    bruto_col = cols.get("neto") or _find_alt_column(df, ("brutos", "bruto"))
    retenido_col = _find_alt_column(df, ("retenido", "retencion", "retenciones"))
    pagado_col = _find_alt_column(df, ("pagado", "liquido", "liquidoapagar", "liquidoapago"))

    if not (bruto_col or retenido_col or pagado_col):
        # Algunas planillas .xls del SII son HTML disfrazado y pandas no falla.
        text = path.read_text(encoding="latin-1", errors="ignore")
        fallback = _fallback_from_html(text)
        if fallback:
            return fallback

    bruto = _sum_column(df, bruto_col)
    retenido = _sum_column(df, retenido_col)
    pagado = _sum_column(df, pagado_col)
    return HonorariosSummary(bruto=bruto, retenido=retenido, pagado=pagado)


def _extract_bhe_totals_row(text: str) -> Optional[HonorariosSummary]:
    row_match = re.search(r"<tr[^>]*>.*?Totales.*?</tr>", text, flags=re.IGNORECASE | re.DOTALL)
    if not row_match:
        return None
    row = row_match.group(0)
    pattern = r"<td[^>]*>\s*(?:<div[^>]*>)?\s*([0-9\.,]+)\s*(?:</div>)?\s*</td>"
    nums = re.findall(pattern, row, flags=re.IGNORECASE | re.DOTALL)
    if len(nums) < 3:
        return None
    bruto = _to_int_money(nums[-3])
    retenido = _to_int_money(nums[-2])
    pagado = _to_int_money(nums[-1])
    if bruto is None and retenido is None and pagado is None:
        return None
    return HonorariosSummary(bruto=bruto, retenido=retenido, pagado=pagado)


def _find_alt_column(df: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in df.columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    return None


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [
            " ".join(str(x) for x in col if x and str(x).lower() != "nan").strip()
            for col in df.columns
        ]
    return df


def _find_alt_column_relaxed(df: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    normalized = {_normalize_col(c): c for c in df.columns}
    for alias in aliases:
        key = _normalize_col(alias)
        if key in normalized:
            return normalized[key]
    for alias in aliases:
        key = _normalize_col(alias)
        if not key:
            continue
        for norm, orig in normalized.items():
            if key in norm:
                return orig
    return None


def _sum_column(df: pd.DataFrame, col: Optional[str]) -> Optional[int]:
    if not col or col not in df.columns:
        return None
    total = 0
    for val in df[col].tolist():
        amt = _to_int_money(val)
        if amt is not None:
            total += amt
    return total


def _extract_hidden_value(text: str, name: str) -> Optional[str]:
    pattern = rf'name=["\']{re.escape(name)}["\']\s+value=["\']([^"\']+)["\']'
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_remanente(path: Optional[Path]) -> Optional[int]:
    if not path or not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            value = data.get("codigo_77_remanente")
            if value is None:
                value = data.get("codigo_77")
            return _to_int_money(value)
        except Exception:
            return None

    if suffix == ".pdf":
        try:
            import pdfplumber  # optional
        except Exception:
            return None
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return None
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")

    for regex in (
        r"remanente[^0-9]*([0-9\.\,]+)",
        r"codigo\s*77[^0-9]*([0-9\.\,]+)",
    ):
        match = re.search(regex, text, flags=re.IGNORECASE)
        if match:
            return _to_int_money(match.group(1))
    return None


def _format_money(value: Optional[int], *, blank_if_none: bool = False) -> str:
    if value is None:
        return "" if blank_if_none else "-"
    if value == 0:
        return "-"
    return f"{int(value):,}".replace(",", ".")


def _sort_codes(codes: Iterable[int], preferred: Iterable[int]) -> list[int]:
    preferred_list = [c for c in preferred if c in codes]
    remainder = sorted([c for c in codes if c not in preferred_list])
    return preferred_list + remainder


def _build_items(
    summary_by_code: Dict[int, Dict[str, Optional[int]]],
    labels: Dict[int, str],
    preferred_order: Iterable[int],
) -> list[SummaryItem]:
    items: list[SummaryItem] = []
    for code in _sort_codes(summary_by_code.keys(), preferred_order):
        bucket = summary_by_code[code]
        items.append(
            SummaryItem(
                concepto=labels.get(code, f"Codigo {code}"),
                neto=bucket.get("neto"),
                iva=bucket.get("iva"),
                total=bucket.get("total"),
                code=code,
            )
        )
    return items


def build_monthly_tax_summary(
    *,
    company_name: str,
    period_year: int,
    period_month: int,
    ventas_path: str,
    compras_path: str,
    boletas_honorarios_path: Optional[str] = None,
    formulario_compacto_path: Optional[str] = None,
    ppm_factor: Optional[float] = None,
    remanente_override: Optional[int] = None,
    impuesto_unico: Optional[int] = None,
) -> Dict[str, Any]:
    ventas_path_obj = Path(ventas_path)
    compras_path_obj = Path(compras_path)

    ventas_by_code, ventas_totals = _summarize_dcv(ventas_path_obj, period_year, period_month)
    compras_by_code, compras_totals = _summarize_dcv(
        compras_path_obj,
        period_year,
        period_month,
        include_exento_in_neto=True,
    )

    boletas_path = _detect_boletas_path(ventas_path_obj)
    boletas_summary = _read_boletas_summary(boletas_path) if boletas_path else None
    if boletas_summary:
        ventas_by_code[39] = {
            "neto": (ventas_by_code.get(39, {}).get("neto") or 0) + boletas_summary["neto"],
            "iva": (ventas_by_code.get(39, {}).get("iva") or 0) + boletas_summary["iva"],
            "total": (ventas_by_code.get(39, {}).get("total") or 0) + boletas_summary["total"],
        }
        ventas_totals["neto"] = (ventas_totals["neto"] or 0) + boletas_summary["neto"]
        ventas_totals["iva"] = (ventas_totals["iva"] or 0) + boletas_summary["iva"]
        ventas_totals["total"] = (ventas_totals["total"] or 0) + boletas_summary["total"]

    # En ventas exentas/no afecta, el neto debe reflejar el total (sin IVA).
    for exento_code in (34, 41):
        bucket = ventas_by_code.get(exento_code)
        if not bucket:
            continue
        iva_val = bucket.get("iva") or 0
        total_val = bucket.get("total") or 0
        neto_val = bucket.get("neto") or 0
        if total_val and iva_val == 0 and neto_val != total_val:
            bucket["neto"] = total_val
            ventas_totals["neto"] = (ventas_totals.get("neto") or 0) + (total_val - neto_val)

    # En compras exentas/no afecta, el neto debe reflejar el total (sin IVA).
    for exento_code in (34,):
        bucket = compras_by_code.get(exento_code)
        if not bucket:
            continue
        iva_val = bucket.get("iva") or 0
        total_val = bucket.get("total") or 0
        neto_val = bucket.get("neto") or 0
        if total_val and iva_val == 0 and neto_val != total_val:
            bucket["neto"] = total_val
            compras_totals["neto"] = (compras_totals.get("neto") or 0) + (total_val - neto_val)

    remanente = remanente_override
    if remanente is None:
        remanente = _extract_remanente(Path(formulario_compacto_path)) if formulario_compacto_path else None

    honorarios = _read_bhe_summary(Path(boletas_honorarios_path)) if boletas_honorarios_path else HonorariosSummary(
        bruto=None, retenido=None, pagado=None
    )

    ventas_items = _build_items(
        ventas_by_code,
        VENTAS_LABELS,
        preferred_order=[33, 34, 61, 56, 51, 39, 48, 41, 43],
    )
    compras_items = _build_items(
        compras_by_code,
        COMPRAS_LABELS,
        preferred_order=[33, 34, 61, 56, 45],
    )

    iva_debito = ventas_totals.get("iva") or 0
    iva_credito = (compras_totals.get("iva") or 0) + (remanente or 0)
    iva_pagar_determinado = iva_debito - iva_credito

    ppm_factor = ppm_factor if ppm_factor is not None else 0.00125
    # PPM debe usar ventas netas del mes (afectas + exentas; sin IVA).
    ppm_base = ventas_totals.get("neto") or 0
    ppm_pagado = int(round(ppm_base * ppm_factor)) if ppm_factor is not None else None

    retencion_honorarios = honorarios.retenido or 0
    impuesto_unico = impuesto_unico or 0
    total_pagar = max(0, iva_pagar_determinado) + (ppm_pagado or 0) + retencion_honorarios + impuesto_unico

    summary = {
        "company": company_name,
        "period": {"year": period_year, "month": period_month},
        "ventas": {"items": [item.__dict__ for item in ventas_items], "total": ventas_totals},
        "compras": {
            "items": [item.__dict__ for item in compras_items],
            "total": compras_totals,
            "remanente": remanente,
        },
        "ppm": {"base": ppm_base, "factor": ppm_factor, "pagado": ppm_pagado},
        "honorarios": honorarios.__dict__,
        "impuesto_unico": impuesto_unico,
        "totales": {
            "iva_debito": iva_debito,
            "iva_credito": iva_credito,
            "iva_pagar_determinado": iva_pagar_determinado,
            "total_a_pagar": total_pagar,
        },
    }

    LOGGER.info(
        "Resumen periodo %s-%02d ventas=%s compras=%s remanente=%s ppm=%s honorarios=%s total=%s",
        period_year,
        period_month,
        ventas_totals,
        compras_totals,
        remanente,
        ppm_pagado,
        honorarios.retenido,
        total_pagar,
    )

    return summary


def generate_monthly_tax_summary_pdf(
    *,
    company_name: str,
    period_year: int,
    period_month: int,
    ventas_path: str,
    compras_path: str,
    boletas_honorarios_path: Optional[str],
    formulario_compacto_path: Optional[str],
    out_pdf_path: str,
    ppm_factor: Optional[float] = None,
    remanente_override: Optional[int] = None,
) -> Dict[str, Any]:
    summary = build_monthly_tax_summary(
        company_name=company_name,
        period_year=period_year,
        period_month=period_month,
        ventas_path=ventas_path,
        compras_path=compras_path,
        boletas_honorarios_path=boletas_honorarios_path,
        formulario_compacto_path=formulario_compacto_path,
        ppm_factor=ppm_factor,
        remanente_override=remanente_override,
    )

    out_path = Path(out_pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    month_label = f"{MONTH_LABELS.get(period_month, str(period_month))} {period_year}"
    _render_pdf(summary, out_path, month_label)

    summary_json_path = out_path.with_suffix(".json")
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return summary


def _render_pdf(summary: Dict[str, Any], out_path: Path, month_label: str) -> None:
    c = canvas.Canvas(str(out_path), pagesize=A4)
    w, h = A4
    margin_left = 16 * mm
    margin_right = 16 * mm
    content_w = w - margin_left - margin_right
    section_gap = 5 * mm
    table_gap = 6 * mm
    y = h - 18 * mm

    # Header
    c.setFillColor(PURPLE)
    c.rect(0, h - 18 * mm, w, 18 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 11 * mm, "RESUMEN DECLARACION DE IMPUESTOS MENSUALES")
    c.drawCentredString(w / 2, h - 15 * mm, month_label)

    # Company
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w / 2, h - 28 * mm, str(summary.get("company", "")))

    y = h - 40 * mm

    def section_title(title: str, y_pos: float) -> float:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawString(margin_left, y_pos, title)
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)
        c.line(margin_left, y_pos - 3, w - margin_right, y_pos - 3)
        return y_pos - section_gap

    def col_widths(*ratios: float) -> list[float]:
        return [content_w * r for r in ratios]

    def render_table(rows: list[list[str]], col_widths: list[float], y_pos: float, total_row_index: Optional[int] = None) -> float:
        tbl = Table(rows, colWidths=col_widths)
        style = [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, LIGHT_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
        if total_row_index is not None:
            style += [
                ("BACKGROUND", (0, total_row_index), (-1, total_row_index), PURPLE),
                ("TEXTCOLOR", (0, total_row_index), (-1, total_row_index), colors.white),
                ("FONTNAME", (0, total_row_index), (-1, total_row_index), "Helvetica-Bold"),
            ]
        tbl.setStyle(TableStyle(style))
        _, tbl_h = tbl.wrapOn(c, 0, 0)
        tbl.drawOn(c, margin_left, y_pos - tbl_h)
        return y_pos - tbl_h - table_gap

    # Ventas section
    y = section_title("Ventas", y)
    ventas_rows = [["Concepto", "Neto", "IVA Debito", "Total"]]
    for item in summary.get("ventas", {}).get("items", []):
        ventas_rows.append([
            item.get("concepto", ""),
            _format_money(item.get("neto")),
            _format_money(item.get("iva")),
            _format_money(item.get("total")),
        ])
    ventas_total = summary.get("ventas", {}).get("total", {})
    ventas_rows.append([
        "TOTAL VENTAS",
        _format_money(ventas_total.get("neto")),
        _format_money(ventas_total.get("iva")),
        _format_money(ventas_total.get("total")),
    ])
    y = render_table(ventas_rows, col_widths(0.55, 0.15, 0.15, 0.15), y, total_row_index=len(ventas_rows) - 1)

    # Compras section
    y = section_title("Compras", y)
    compras_rows = [["Concepto", "Neto", "IVA Credito", "Total"]]
    for item in summary.get("compras", {}).get("items", []):
        compras_rows.append([
            item.get("concepto", ""),
            _format_money(item.get("neto")),
            _format_money(item.get("iva")),
            _format_money(item.get("total")),
        ])
    remanente = summary.get("compras", {}).get("remanente")
    compras_rows.append([
        "Remanente IVA periodo anterior",
        "",
        _format_money(remanente, blank_if_none=True),
        "",
    ])
    compras_total = summary.get("compras", {}).get("total", {})
    compras_rows.append([
        "TOTAL COMPRAS",
        _format_money(compras_total.get("neto")),
        _format_money(compras_total.get("iva")),
        _format_money(compras_total.get("total")),
    ])
    y = render_table(compras_rows, col_widths(0.55, 0.15, 0.15, 0.15), y, total_row_index=len(compras_rows) - 1)

    # PPM section
    y = section_title("Pago Provisional Mensual (PPM)", y)
    ppm = summary.get("ppm", {})
    factor = ppm.get("factor")
    factor_label = f"{float(factor) * 100:.3f}%" if factor is not None else "-"
    ppm_rows = [
        ["Ventas Netas", "Factor", "PPM Pagado"],
        [
            _format_money(ppm.get("base")),
            factor_label,
            _format_money(ppm.get("pagado")),
        ],
    ]
    y = render_table(ppm_rows, col_widths(0.50, 0.25, 0.25), y)

    # Honorarios section
    y = section_title("Boletas de Honorarios", y)
    hon = summary.get("honorarios", {})
    hon_rows = [
        ["Bruto", "Retenido", "Pagado"],
        [
            _format_money(hon.get("bruto")),
            _format_money(hon.get("retenido")),
            _format_money(hon.get("pagado")),
        ],
    ]
    y = render_table(hon_rows, col_widths(0.34, 0.33, 0.33), y)

    # Impuesto unico
    y = section_title("Impuesto Unico", y)
    impuesto_unico = summary.get("impuesto_unico")
    impuesto_rows = [["Monto", _format_money(impuesto_unico)]]
    y = render_table(impuesto_rows, col_widths(0.65, 0.35), y)

    # Total a pagar
    y = section_title("Total a Pagar Formulario", y)
    tot = summary.get("totales", {})
    total_rows = [
        ["IVA a pagar determinado", _format_money(tot.get("iva_pagar_determinado"))],
        ["Pago Provisional Mensual (PPM)", _format_money(summary.get("ppm", {}).get("pagado"))],
        ["Retencion Boletas Honorarios", _format_money(summary.get("honorarios", {}).get("retenido"))],
        ["Impuesto Unico Trabajadores", _format_money(summary.get("impuesto_unico"))],
        ["TOTAL A PAGAR", _format_money(tot.get("total_a_pagar"))],
    ]
    y = render_table(total_rows, col_widths(0.67, 0.33), y, total_row_index=len(total_rows) - 1)

    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawRightString(w - margin_right, 8 * mm, f"Generado {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.save()
