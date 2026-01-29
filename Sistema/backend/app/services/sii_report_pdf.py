from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader


PURPLE = colors.HexColor("#5B2C83")
GRAY = colors.HexColor("#4B5563")
LIGHT_GRAY = colors.HexColor("#E5E7EB")


@dataclass
class ReportContext:
    company_id: str
    razon_social: str
    year: int
    month: int
    month_label: str  # "JULIO 2025"
    out_dir: Path


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _draw_header(c: canvas.Canvas, title: str, subtitle: str) -> None:
    w, h = A4
    header_h = 18 * mm
    c.setFillColor(PURPLE)
    c.rect(0, h - header_h, w, header_h, stroke=0, fill=1)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 11 * mm, title)

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(w / 2, h - 15 * mm, subtitle)


def _draw_footer(c: canvas.Canvas, page_num: int, total_pages: int) -> None:
    w, _ = A4
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawRightString(w - 12 * mm, 8 * mm, f"Página {page_num} de {total_pages}")


def _draw_company_name(c: canvas.Canvas, razon_social: str) -> None:
    w, h = A4
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawCentredString(w / 2, h - 28 * mm, razon_social)


def _table(c: canvas.Canvas, x: float, y: float, data: List[List[Any]], col_widths: List[float]) -> float:
    """
    Dibuja una tabla con estilo corporativo.
    Retorna el alto renderizado (para calcular layout).
    """
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
    ]))
    w, h = t.wrapOn(c, 0, 0)
    t.drawOn(c, x, y - h)
    return h


def _draw_section_title(c: canvas.Canvas, x: float, y: float, text: str) -> None:
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.black)
    c.drawString(x, y, text)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.line(x, y - 3, x + 170 * mm, y - 3)


def _money(n: Optional[float | int]) -> str:
    if n is None:
        return "-"
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except Exception:
        return str(n)


def _draw_image(c: canvas.Canvas, img_path: Path, x: float, y: float, w: float, h: float) -> None:
    if img_path and img_path.exists():
        c.drawImage(ImageReader(str(img_path)), x, y - h, width=w, height=h, preserveAspectRatio=True, mask="auto")


def build_tax_report_pdf(
    *,
    company_id: str,
    razon_social: str,
    year: int,
    month: int,
    month_label: str,
    report_data: Dict[str, Any],
    storage_root: Path,
) -> Path:
    """
    Genera el PDF y deja artefactos persistidos en:
      storage/companies/<id>/Resumen/
    report_data: dict consolidado (resumen/compras/ventas/honorarios).
    """
    ctx = ReportContext(
        company_id=company_id,
        razon_social=razon_social,
        year=year,
        month=month,
        month_label=month_label,
        out_dir=storage_root / "companies" / str(company_id) / "Resumen",
    )
    _ensure_dir(ctx.out_dir)

    pdf_path = ctx.out_dir / f"Resumen_{company_id}_{year}_{month:02d}.pdf"
    json_path = ctx.out_dir / f"report_data_{company_id}_{year}_{month:02d}.json"
    manifest_path = ctx.out_dir / "manifest.json"

    # Persistencia de insumos (trazabilidad)
    _save_json(json_path, report_data)

    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    total_pages = 4  # (Resumen, Compras, Ventas, Honorarios). Impuesto Único se suma cuando exista.

    # -----------------------------
    # Página 1: Resumen
    # -----------------------------
    _draw_header(
        c,
        "RESUMEN DECLARACIÓN DE IMPUESTOS",
        f"MENSUALES {ctx.month_label}",
    )
    _draw_company_name(c, ctx.razon_social)

    x0 = 15 * mm
    y = A4[1] - 40 * mm

    resumen = report_data.get("resumen", {})

    # Ventas
    _draw_section_title(c, x0, y, "Ventas")
    ventas_rows = [["Concepto", "Neto", "IVA Débito", "Total"]]
    for r in resumen.get("ventas_items", []):
        ventas_rows.append([r.get("concepto", ""), _money(r.get("neto")), _money(r.get("iva")), _money(r.get("total"))])
    y -= 6 * mm
    h_tbl = _table(c, x0, y, ventas_rows, [90*mm, 25*mm, 25*mm, 25*mm])
    y -= (h_tbl + 10 * mm)

    # Compras
    _draw_section_title(c, x0, y, "Compras")
    compras_rows = [["Concepto", "Neto", "IVA Crédito", "Total"]]
    for r in resumen.get("compras_items", []):
        compras_rows.append([r.get("concepto", ""), _money(r.get("neto")), _money(r.get("iva")), _money(r.get("total"))])
    y -= 6 * mm
    h_tbl = _table(c, x0, y, compras_rows, [90*mm, 25*mm, 25*mm, 25*mm])
    y -= (h_tbl + 8 * mm)

    # PPM (bloque compacto)
    ppm = resumen.get("ppm", {})
    _draw_section_title(c, x0, y, "Pago Provisional Mensual (PPM)")
    ppm_rows = [["Base imponible", "Factor", "PPM Pagado"], [_money(ppm.get("base")), ppm.get("factor", "-"), _money(ppm.get("pagado"))]]
    y -= 6 * mm
    h_tbl = _table(c, x0, y, ppm_rows, [90*mm, 40*mm, 35*mm])
    y -= (h_tbl + 8 * mm)

    # Honorarios (resumen)
    hon = resumen.get("honorarios", {})
    _draw_section_title(c, x0, y, "Boletas de Honorarios")
    hon_rows = [["Bruto", "Retenido", "Pagado"], [_money(hon.get("bruto")), _money(hon.get("retenido")), _money(hon.get("pagado"))]]
    y -= 6 * mm
    h_tbl = _table(c, x0, y, hon_rows, [55*mm, 55*mm, 55*mm])
    y -= (h_tbl + 10 * mm)

    # Total a pagar (barra)
    total_pagar = resumen.get("total_a_pagar")
    w, _ = A4
    bar_h = 9 * mm
    c.setFillColor(PURPLE)
    c.rect(x0, 20 * mm, w - 2 * x0, bar_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0 + 4 * mm, 22.2 * mm, "Total a Pagar Formulario")
    c.drawRightString(w - x0 - 4 * mm, 22.2 * mm, _money(total_pagar))

    _draw_footer(c, 1, total_pages)
    c.showPage()

    # -----------------------------
    # Página 2: Compras
    # -----------------------------
    _draw_header(c, "COMPRAS", f"DESDE ENERO A {ctx.month_label}")
    _draw_company_name(c, ctx.razon_social)

    compras = report_data.get("compras", {})
    chart_path = Path(compras.get("chart_path", "")) if compras.get("chart_path") else None
    _draw_image(c, chart_path, 15*mm, A4[1] - 45*mm, A4[0] - 30*mm, 85*mm)

    y2 = A4[1] - 140 * mm
    top_annual = [["TOP 5 COMPRAS ANUALES", "", ""]] + [["Razón Social", "RUT", "Monto"]] + [
        [r.get("razon_social",""), r.get("rut",""), _money(r.get("monto"))]
        for r in compras.get("top5_anual", [])
    ]
    top_month = [["TOP 5 COMPRAS MENSUALES", "", ""]] + [["Razón Social", "RUT", "Monto"]] + [
        [r.get("razon_social",""), r.get("rut",""), _money(r.get("monto"))]
        for r in compras.get("top5_mes", [])
    ]
    _table(c, 15*mm, y2, top_annual, [70*mm, 25*mm, 25*mm])
    _table(c, 110*mm, y2, top_month, [70*mm, 25*mm, 25*mm])

    _draw_footer(c, 2, total_pages)
    c.showPage()

    # -----------------------------
    # Página 3: Ventas
    # -----------------------------
    _draw_header(c, "VENTAS", f"DESDE ENERO A {ctx.month_label}")
    _draw_company_name(c, ctx.razon_social)

    ventas = report_data.get("ventas", {})
    chart_path = Path(ventas.get("chart_path", "")) if ventas.get("chart_path") else None
    _draw_image(c, chart_path, 15*mm, A4[1] - 45*mm, A4[0] - 30*mm, 85*mm)

    y3 = A4[1] - 140 * mm
    top_annual = [["TOP 5 VENTAS ANUALES", "", ""]] + [["Razón Social", "RUT", "Monto"]] + [
        [r.get("razon_social",""), r.get("rut",""), _money(r.get("monto"))]
        for r in ventas.get("top5_anual", [])
    ]
    top_month = [["TOP 5 VENTAS MENSUALES", "", ""]] + [["Razón Social", "RUT", "Monto"]] + [
        [r.get("razon_social",""), r.get("rut",""), _money(r.get("monto"))]
        for r in ventas.get("top5_mes", [])
    ]
    _table(c, 15*mm, y3, top_annual, [70*mm, 25*mm, 25*mm])
    _table(c, 110*mm, y3, top_month, [70*mm, 25*mm, 25*mm])

    _draw_footer(c, 3, total_pages)
    c.showPage()

    # -----------------------------
    # Página 4: Honorarios
    # -----------------------------
    _draw_header(c, "HONORARIOS", f"{ctx.month_label}")
    _draw_company_name(c, ctx.razon_social)

    honor = report_data.get("honorarios", {})
    y4 = A4[1] - 50 * mm
    _draw_section_title(c, 15*mm, y4, "Resumen")
    y4 -= 6 * mm
    h_rows = [["Bruto", "Retenido", "Pagado"], [_money(honor.get("bruto")), _money(honor.get("retenido")), _money(honor.get("pagado"))]]
    _table(c, 15*mm, y4, h_rows, [55*mm, 55*mm, 55*mm])

    _draw_footer(c, 4, total_pages)
    c.showPage()

    c.save()

    # Manifest local de reportes
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {"year": year, "month": month},
        "pdf_path": str(pdf_path),
        "data_path": str(json_path),
    }
    _save_json(manifest_path, manifest)

    return pdf_path
