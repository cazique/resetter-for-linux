"""Generador de informes PDF consolidados (ReportLab).

Estructura del informe:
  1. Portada: logo/título de empresa, rango de fechas, filtros aplicados,
     resumen ejecutivo (total gastos, total IVA, nº documentos) y desglose
     por categoría (tabla + gráfico de barras con el color de cada categoría).
  2. Tabla detallada de documentos ordenados por fecha.
  3. Anexo visual: imagen escaneada de cada documento (dos por página).

Todas las páginas llevan pie con fecha de generación y "Página X de Y".

El generador es independiente de Flask/SQLAlchemy: trabaja con `ReportItem`,
que se puede construir desde un modelo `Document` con `ReportItem.from_document`.
"""
from __future__ import annotations

import io
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO, Iterable, Sequence

from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:  # evita dependencia circular en tiempo de ejecución
    from app.models import Document

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Paleta corporativa
# --------------------------------------------------------------------------- #
PRIMARY = colors.HexColor("#0D3B66")       # azul corporativo
PRIMARY_LIGHT = colors.HexColor("#E8EEF5")
ACCENT = colors.HexColor("#F4A259")
TEXT_DARK = colors.HexColor("#1F2933")
TEXT_MUTED = colors.HexColor("#616E7C")
BORDER = colors.HexColor("#CBD2D9")
ZEBRA = colors.HexColor("#F5F7FA")
FALLBACK_CATEGORY_COLOR = "#607D8B"

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 2.0 * cm
MARGIN_TOP = 2.6 * cm
MARGIN_BOTTOM = 2.2 * cm
COVER_BAND_HEIGHT = 3.2 * cm
ANNEX_CAPTION_HEIGHT = 2.4 * cm  # título + metadatos (hasta 2 líneas) + espaciado

ANNEX_IMAGE_MAX_PX = 1600  # las imágenes se reducen antes de incrustarlas
TWO_PLACES = Decimal("0.01")


# --------------------------------------------------------------------------- #
# Modelos de datos del informe
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ReportItem:
    """Fila del informe, desacoplada del ORM."""

    id: str
    date: date
    title: str
    contact_name: str | None
    category_name: str
    category_color: str
    amount: Decimal
    tax_amount: Decimal
    status: str
    image_path: str | None  # relativa a upload_root
    notes: str | None = None

    @classmethod
    def from_document(cls, doc: "Document") -> "ReportItem":
        return cls(
            id=str(doc.id),
            date=doc.date,
            title=doc.title or "(sin título)",
            contact_name=doc.contact.name if doc.contact else None,
            category_name=doc.category.name if doc.category else "Sin categoría",
            category_color=(doc.category.color_hex if doc.category else None) or FALLBACK_CATEGORY_COLOR,
            amount=Decimal(doc.amount or 0),
            tax_amount=Decimal(doc.tax_amount or 0),
            status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
            image_path=doc.image_path,
            notes=doc.notes,
        )


@dataclass(frozen=True)
class ReportFilters:
    """Filtros aplicados (solo para mostrarlos en la portada)."""

    start_date: date | None = None
    end_date: date | None = None
    category_name: str | None = None
    contact_name: str | None = None
    status: str | None = None
    search: str | None = None


@dataclass
class CategorySummary:
    name: str
    color: str
    count: int = 0
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    tax_amount: Decimal = field(default_factory=lambda: Decimal("0"))


# --------------------------------------------------------------------------- #
# Utilidades de formato (locale es-ES sin depender de locale del sistema)
# --------------------------------------------------------------------------- #
def format_eur(value: Decimal | float | int) -> str:
    """Formatea 1234.5 como '1.234,50 €'."""
    quantized = Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    integer, _, fraction = f"{abs(quantized):.2f}".partition(".")
    groups: list[str] = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    return f"{sign}{'.'.join(groups)},{fraction} €"


def format_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else "—"


def _escape(text: str | None) -> str:
    """Escapa caracteres especiales para el mini-markup de Paragraph."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _safe_color(hex_value: str | None) -> colors.Color:
    try:
        return colors.HexColor(hex_value or FALLBACK_CATEGORY_COLOR)
    except (ValueError, TypeError):
        return colors.HexColor(FALLBACK_CATEGORY_COLOR)


# --------------------------------------------------------------------------- #
# Canvas con numeración "Página X de Y"
# --------------------------------------------------------------------------- #
def _make_numbered_canvas(company_name: str, generated_at: datetime) -> type[rl_canvas.Canvas]:
    """Crea una clase Canvas que difiere el pie hasta conocer el total de páginas."""

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_page_states: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 (API de ReportLab)
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total_pages: int) -> None:
            self.saveState()
            y = MARGIN_BOTTOM - 0.9 * cm
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.5)
            self.line(MARGIN_X, y + 0.45 * cm, PAGE_WIDTH - MARGIN_X, y + 0.45 * cm)
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(
                MARGIN_X,
                y,
                f"{company_name}  ·  Generado el {generated_at:%d/%m/%Y %H:%M}",
            )
            self.drawRightString(
                PAGE_WIDTH - MARGIN_X, y, f"Página {self._pageNumber} de {total_pages}"
            )
            self.restoreState()

    return NumberedCanvas


# --------------------------------------------------------------------------- #
# Flowables auxiliares
# --------------------------------------------------------------------------- #
class ColorSwatch(Flowable):
    """Pequeño cuadrado de color para la leyenda de categorías."""

    def __init__(self, color: colors.Color, size: float = 3.2 * mm) -> None:
        super().__init__()
        self.color = color
        self.size = size
        self.width = self.height = size

    def draw(self) -> None:
        self.canv.setFillColor(self.color)
        self.canv.setStrokeColor(self.color)
        self.canv.roundRect(0, 0, self.size, self.size, 0.6 * mm, stroke=0, fill=1)


# --------------------------------------------------------------------------- #
# Generador
# --------------------------------------------------------------------------- #
class PdfReportGenerator:
    """Construye el informe ejecutivo corporativo."""

    def __init__(
        self,
        company_name: str,
        upload_root: str | Path,
        logo_path: str | Path | None = None,
        report_title: str = "Informe de Documentos y Gastos",
    ) -> None:
        self.company_name = company_name or "Gestor Documental"
        self.upload_root = Path(upload_root).resolve()
        self.logo_path = Path(logo_path) if logo_path else None
        self.report_title = report_title
        self.styles = self._build_styles()
        self.content_width = PAGE_WIDTH - 2 * MARGIN_X
        self.content_height = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def generate(
        self,
        items: Sequence[ReportItem],
        filters: ReportFilters,
        output: str | Path | BinaryIO,
        include_images: bool = True,
    ) -> None:
        """Genera el PDF en `output` (ruta o stream binario)."""
        generated_at = datetime.now()
        ordered = sorted(items, key=lambda it: (it.date, it.title.lower()))

        doc = BaseDocTemplate(
            output if not isinstance(output, Path) else str(output),
            pagesize=A4,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title=self.report_title,
            author=self.company_name,
            subject=self._range_label(filters),
            creator="Gestor Documental API",
        )
        cover_frame = Frame(
            MARGIN_X, MARGIN_BOTTOM, self.content_width, PAGE_HEIGHT - MARGIN_BOTTOM - COVER_BAND_HEIGHT - 1.4 * cm,
            id="cover", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        content_frame = Frame(
            MARGIN_X, MARGIN_BOTTOM, self.content_width,
            self.content_height,
            id="content", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        doc.addPageTemplates(
            [
                PageTemplate(id="Cover", frames=[cover_frame], onPage=self._draw_cover_band),
                PageTemplate(id="Content", frames=[content_frame], onPage=self._draw_header),
            ]
        )

        story: list[Flowable] = []
        story += self._build_cover(ordered, filters, generated_at)
        story += [NextPageTemplate("Content"), PageBreak()]
        story += self._build_detail_table(ordered)
        if include_images and ordered:
            story += [PageBreak()]
            story += self._build_annex(ordered)

        doc.build(story, canvasmaker=_make_numbered_canvas(self.company_name, generated_at))

    def generate_bytes(
        self, items: Sequence[ReportItem], filters: ReportFilters, include_images: bool = True
    ) -> bytes:
        buffer = io.BytesIO()
        self.generate(items, filters, buffer, include_images=include_images)
        return buffer.getvalue()

    # ------------------------------------------------------------------ #
    # Estilos
    # ------------------------------------------------------------------ #
    @staticmethod
    def _build_styles() -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "company": ParagraphStyle(
                "company", parent=base["Title"], fontName="Helvetica-Bold", fontSize=13,
                textColor=colors.white, alignment=TA_LEFT, leading=16,
            ),
            "title": ParagraphStyle(
                "title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24,
                textColor=PRIMARY, alignment=TA_LEFT, leading=29, spaceAfter=4,
            ),
            "subtitle": ParagraphStyle(
                "subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=12,
                textColor=TEXT_MUTED, leading=16, spaceAfter=2,
            ),
            "h2": ParagraphStyle(
                "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=13,
                textColor=PRIMARY, spaceBefore=14, spaceAfter=8, leading=16,
            ),
            "body": ParagraphStyle(
                "body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
                textColor=TEXT_DARK, leading=13,
            ),
            "muted": ParagraphStyle(
                "muted", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
                textColor=TEXT_MUTED, leading=11,
            ),
            "cell": ParagraphStyle(
                "cell", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
                textColor=TEXT_DARK, leading=10.5,
            ),
            "cell_right": ParagraphStyle(
                "cell_right", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
                textColor=TEXT_DARK, leading=10.5, alignment=TA_RIGHT,
            ),
            "kpi_label": ParagraphStyle(
                "kpi_label", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
                textColor=TEXT_MUTED, alignment=TA_CENTER, leading=11,
            ),
            "kpi_value": ParagraphStyle(
                "kpi_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=16,
                textColor=PRIMARY, alignment=TA_CENTER, leading=20,
            ),
            "annex_title": ParagraphStyle(
                "annex_title", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
                textColor=PRIMARY, leading=13, spaceAfter=2,
            ),
        }

    # ------------------------------------------------------------------ #
    # Decoración de página
    # ------------------------------------------------------------------ #
    def _draw_cover_band(self, canv: rl_canvas.Canvas, _doc: BaseDocTemplate) -> None:
        """Banda superior de color en la portada con logo/nombre de empresa."""
        canv.saveState()
        band_h = COVER_BAND_HEIGHT
        canv.setFillColor(PRIMARY)
        canv.rect(0, PAGE_HEIGHT - band_h, PAGE_WIDTH, band_h, stroke=0, fill=1)
        canv.setFillColor(ACCENT)
        canv.rect(0, PAGE_HEIGHT - band_h - 0.15 * cm, PAGE_WIDTH, 0.15 * cm, stroke=0, fill=1)

        text_x = MARGIN_X
        logo = self._logo_path_if_valid()
        if logo:
            try:
                logo_h = 1.6 * cm
                with PILImage.open(logo) as img:
                    ratio = img.width / img.height
                logo_w = min(logo_h * ratio, 5 * cm)
                canv.drawImage(
                    str(logo), MARGIN_X, PAGE_HEIGHT - band_h / 2 - logo_h / 2,
                    width=logo_w, height=logo_h, preserveAspectRatio=True, mask="auto",
                )
                text_x = MARGIN_X + logo_w + 0.5 * cm
            except (OSError, UnidentifiedImageError, ZeroDivisionError):
                logger.warning("No se pudo dibujar el logo %s", logo)

        canv.setFillColor(colors.white)
        canv.setFont("Helvetica-Bold", 16)
        canv.drawString(text_x, PAGE_HEIGHT - band_h / 2 + 1, self.company_name)
        canv.setFont("Helvetica", 9)
        canv.drawString(text_x, PAGE_HEIGHT - band_h / 2 - 13, "Gestión Documental · Informe ejecutivo")
        canv.restoreState()

    def _draw_header(self, canv: rl_canvas.Canvas, _doc: BaseDocTemplate) -> None:
        """Cabecera discreta en las páginas de contenido."""
        canv.saveState()
        y = PAGE_HEIGHT - MARGIN_TOP + 0.55 * cm
        canv.setFillColor(PRIMARY)
        canv.rect(MARGIN_X, y + 0.42 * cm, 1.2 * cm, 0.12 * cm, stroke=0, fill=1)
        canv.setFont("Helvetica-Bold", 9)
        canv.drawString(MARGIN_X, y, self.company_name)
        canv.setFont("Helvetica", 9)
        canv.setFillColor(TEXT_MUTED)
        canv.drawRightString(PAGE_WIDTH - MARGIN_X, y, self.report_title)
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.5)
        canv.line(MARGIN_X, y - 0.25 * cm, PAGE_WIDTH - MARGIN_X, y - 0.25 * cm)
        canv.restoreState()

    def _logo_path_if_valid(self) -> Path | None:
        if self.logo_path and self.logo_path.is_file():
            return self.logo_path
        return None

    # ------------------------------------------------------------------ #
    # 1. Portada
    # ------------------------------------------------------------------ #
    def _build_cover(
        self, items: Sequence[ReportItem], filters: ReportFilters, generated_at: datetime
    ) -> list[Flowable]:
        s = self.styles
        total_amount = sum((it.amount for it in items), Decimal("0"))
        total_tax = sum((it.tax_amount for it in items), Decimal("0"))
        summaries = self._summarize_by_category(items)

        story: list[Flowable] = [
            Paragraph(_escape(self.report_title), s["title"]),
            Paragraph(f"Periodo: <b>{_escape(self._range_label(filters))}</b>", s["subtitle"]),
            Paragraph(f"Fecha de generación: {generated_at:%d/%m/%Y %H:%M}", s["muted"]),
            Spacer(1, 0.4 * cm),
        ]

        applied = self._filters_description(filters)
        if applied:
            story.append(Paragraph(f"Filtros aplicados: {applied}", s["muted"]))
            story.append(Spacer(1, 0.2 * cm))

        # Resumen ejecutivo (tarjetas KPI)
        story.append(Paragraph("Resumen ejecutivo", s["h2"]))
        story.append(self._kpi_cards(total_amount, total_tax, len(items)))

        # Desglose por categoría
        story.append(Paragraph("Desglose por categoría", s["h2"]))
        if summaries:
            story.append(self._category_table(summaries, total_amount))
            story.append(Spacer(1, 0.5 * cm))
            story.append(self._category_bar_chart(summaries))
        else:
            story.append(Paragraph("No hay documentos que cumplan los filtros indicados.", s["body"]))
        return story

    def _kpi_cards(self, total_amount: Decimal, total_tax: Decimal, count: int) -> Table:
        s = self.styles
        base_amount = total_amount - total_tax
        cards = [
            [Paragraph("TOTAL GASTOS", s["kpi_label"]), Paragraph("TOTAL IVA", s["kpi_label"]),
             Paragraph("BASE IMPONIBLE", s["kpi_label"]), Paragraph("DOCUMENTOS", s["kpi_label"])],
            [Paragraph(format_eur(total_amount), s["kpi_value"]),
             Paragraph(format_eur(total_tax), s["kpi_value"]),
             Paragraph(format_eur(base_amount), s["kpi_value"]),
             Paragraph(str(count), s["kpi_value"])],
        ]
        col_w = self.content_width / 4
        table = Table(cards, colWidths=[col_w] * 4, rowHeights=[0.8 * cm, 1.1 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_LIGHT),
                    ("LINEABOVE", (0, 0), (-1, 0), 2.5, PRIMARY),
                    ("LINEAFTER", (0, 0), (-2, -1), 1.5, colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    @staticmethod
    def _summarize_by_category(items: Iterable[ReportItem]) -> list[CategorySummary]:
        buckets: "OrderedDict[str, CategorySummary]" = OrderedDict()
        for it in items:
            summary = buckets.setdefault(
                it.category_name, CategorySummary(name=it.category_name, color=it.category_color)
            )
            summary.count += 1
            summary.amount += it.amount
            summary.tax_amount += it.tax_amount
        return sorted(buckets.values(), key=lambda c: c.amount, reverse=True)

    def _category_table(self, summaries: Sequence[CategorySummary], total: Decimal) -> Table:
        s = self.styles
        header = ["", "Categoría", "Docs.", "Importe", "IVA", "% total"]
        rows: list[list[Any]] = [header]
        for c in summaries:
            pct = (c.amount / total * 100) if total else Decimal("0")
            rows.append(
                [
                    ColorSwatch(_safe_color(c.color)),
                    Paragraph(_escape(c.name), s["cell"]),
                    str(c.count),
                    format_eur(c.amount),
                    format_eur(c.tax_amount),
                    f"{pct.quantize(Decimal('0.1'))} %".replace(".", ","),
                ]
            )
        rows.append(
            ["", Paragraph("<b>Total</b>", s["cell"]), str(sum(c.count for c in summaries)),
             format_eur(total), format_eur(sum((c.tax_amount for c in summaries), Decimal("0"))),
             "100,0 %" if total else "0,0 %"]
        )
        w = self.content_width
        table = Table(
            rows,
            colWidths=[0.7 * cm, w - 0.7 * cm - 1.5 * cm - 3.2 * cm - 2.8 * cm - 2 * cm,
                       1.5 * cm, 3.2 * cm, 2.8 * cm, 2 * cm],
            repeatRows=1,
        )
        style = self._base_table_style()
        style.add("ALIGN", (2, 0), (-1, -1), "RIGHT")
        style.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
        style.add("LINEABOVE", (0, -1), (-1, -1), 1, PRIMARY)
        style.add("BACKGROUND", (0, -1), (-1, -1), PRIMARY_LIGHT)
        table.setStyle(style)
        return table

    def _category_bar_chart(self, summaries: Sequence[CategorySummary]) -> Drawing:
        """Gráfico de barras horizontal con el color de cada categoría."""
        bar_h, gap, label_w, value_w = 14, 8, 4.2 * cm, 2.8 * cm
        chart_w = self.content_width
        height = len(summaries) * (bar_h + gap) + gap
        drawing = Drawing(chart_w, height)
        max_amount = max((c.amount for c in summaries), default=Decimal("0"))
        bar_area = chart_w - label_w - value_w

        # Eje vertical
        drawing.add(Line(label_w, 0, label_w, height, strokeColor=BORDER, strokeWidth=0.6))
        for idx, c in enumerate(summaries):
            y = height - (idx + 1) * (bar_h + gap)
            ratio = float(c.amount / max_amount) if max_amount > 0 else 0.0
            width = max(bar_area * ratio, 1.5)
            label = c.name if len(c.name) <= 28 else c.name[:27] + "…"
            drawing.add(String(label_w - 6, y + 4, label, fontName="Helvetica", fontSize=8.5,
                               fillColor=TEXT_DARK, textAnchor="end"))
            drawing.add(Rect(label_w, y, width, bar_h, fillColor=_safe_color(c.color),
                             strokeColor=None, rx=2, ry=2))
            drawing.add(String(label_w + width + 6, y + 4, format_eur(c.amount),
                               fontName="Helvetica-Bold", fontSize=8.5, fillColor=TEXT_DARK))
        return drawing

    # ------------------------------------------------------------------ #
    # 2. Tabla detallada
    # ------------------------------------------------------------------ #
    def _build_detail_table(self, items: Sequence[ReportItem]) -> list[Flowable]:
        s = self.styles
        story: list[Flowable] = [Paragraph("Detalle de documentos", s["h2"])]
        if not items:
            story.append(Paragraph("No hay documentos en el periodo seleccionado.", s["body"]))
            return story

        header = ["Fecha", "Título", "Contacto", "Categoría", "Importe", "IVA", "Estado"]
        rows: list[list[Any]] = [header]
        for it in items:
            rows.append(
                [
                    format_date(it.date),
                    Paragraph(_escape(it.title), s["cell"]),
                    Paragraph(_escape(it.contact_name) or "—", s["cell"]),
                    Paragraph(_escape(it.category_name), s["cell"]),
                    Paragraph(format_eur(it.amount), s["cell_right"]),
                    Paragraph(format_eur(it.tax_amount), s["cell_right"]),
                    it.status,
                ]
            )
        total_amount = sum((it.amount for it in items), Decimal("0"))
        total_tax = sum((it.tax_amount for it in items), Decimal("0"))
        rows.append(
            ["", Paragraph(f"<b>Total ({len(items)} documentos)</b>", s["cell"]), "", "",
             Paragraph(f"<b>{format_eur(total_amount)}</b>", s["cell_right"]),
             Paragraph(f"<b>{format_eur(total_tax)}</b>", s["cell_right"]), ""]
        )

        fixed = 1.9 * cm + 2.6 * cm + 2.4 * cm + 2.2 * cm + 1.9 * cm
        flexible = self.content_width - fixed
        col_widths = [1.9 * cm, flexible * 0.55, flexible * 0.45, 2.6 * cm, 2.4 * cm, 2.2 * cm, 1.9 * cm]
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        style = self._base_table_style(zebra_rows=len(rows) - 1)
        style.add("LINEABOVE", (0, -1), (-1, -1), 1, PRIMARY)
        style.add("BACKGROUND", (0, -1), (-1, -1), PRIMARY_LIGHT)
        style.add("FONTSIZE", (0, 1), (-1, -1), 8.5)
        table.setStyle(style)
        story.append(table)
        return story

    @staticmethod
    def _base_table_style(zebra_rows: int = 0) -> TableStyle:
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDER),
            ]
        )
        for row in range(1, zebra_rows):
            if row % 2 == 0:
                style.add("BACKGROUND", (0, row), (-1, row), ZEBRA)
        return style

    # ------------------------------------------------------------------ #
    # 3. Anexo visual
    # ------------------------------------------------------------------ #
    def _build_annex(self, items: Sequence[ReportItem]) -> list[Flowable]:
        s = self.styles
        story: list[Flowable] = [
            Paragraph("Anexo visual de documentos", s["h2"]),
            Paragraph(
                "Imágenes procesadas (auto-rotación, corrección de contraste y limpieza de sombras) "
                "de cada documento incluido en el informe.",
                s["muted"],
            ),
            Spacer(1, 0.3 * cm),
        ]
        # Dos documentos por página: cada bloque ocupa algo menos de media página.
        block_h = (self.content_height - 1.6 * cm) / 2
        for item in items:
            story.append(CondPageBreak(block_h))
            story.append(self._annex_block(item, block_h))
        return story

    def _annex_block(self, item: ReportItem, block_h: float) -> KeepTogether:
        s = self.styles
        meta = (
            f"{format_date(item.date)}  ·  {_escape(item.category_name)}  ·  "
            f"{_escape(item.contact_name) or 'Sin contacto'}  ·  "
            f"Importe: <b>{format_eur(item.amount)}</b> (IVA {format_eur(item.tax_amount)})  ·  "
            f"{_escape(item.status)}"
        )
        image_flowable = self._load_annex_image(
            item.image_path, self.content_width, block_h - ANNEX_CAPTION_HEIGHT
        )
        parts: list[Flowable] = [
            Paragraph(_escape(item.title), s["annex_title"]),
            Paragraph(meta, s["muted"]),
            Spacer(1, 0.2 * cm),
            image_flowable,
            Spacer(1, 0.4 * cm),
        ]
        return KeepTogether(parts)

    def _load_annex_image(self, relative_path: str | None, max_w: float, max_h: float) -> Flowable:
        """Carga, reduce y encuadra la imagen; si falla, muestra un aviso."""
        path = self._resolve_upload(relative_path)
        if path is None:
            return self._missing_image_box(max_w, "Imagen no disponible")
        try:
            with PILImage.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((ANNEX_IMAGE_MAX_PX, ANNEX_IMAGE_MAX_PX), PILImage.Resampling.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=82, optimize=True)
                width_px, height_px = img.size
        except (OSError, UnidentifiedImageError) as exc:
            logger.warning("No se pudo cargar la imagen %s: %s", path, exc)
            return self._missing_image_box(max_w, "Imagen dañada o ilegible")

        buffer.seek(0)
        scale = min(max_w / width_px, max_h / height_px)
        flowable = Image(buffer, width=width_px * scale, height=height_px * scale)
        flowable.hAlign = "CENTER"
        return flowable

    def _missing_image_box(self, width: float, message: str) -> Table:
        table = Table([[message]], colWidths=[width], rowHeights=[2 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                    ("BACKGROUND", (0, 0), (-1, -1), ZEBRA),
                    ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_MUTED),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Oblique"),
                ]
            )
        )
        return table

    def _resolve_upload(self, relative_path: str | None) -> Path | None:
        if not relative_path:
            return None
        candidate = (self.upload_root / relative_path).resolve()
        if self.upload_root not in candidate.parents or not candidate.is_file():
            return None
        return candidate

    # ------------------------------------------------------------------ #
    # Textos auxiliares
    # ------------------------------------------------------------------ #
    @staticmethod
    def _range_label(filters: ReportFilters) -> str:
        if filters.start_date and filters.end_date:
            return f"{format_date(filters.start_date)} – {format_date(filters.end_date)}"
        if filters.start_date:
            return f"Desde {format_date(filters.start_date)}"
        if filters.end_date:
            return f"Hasta {format_date(filters.end_date)}"
        return "Todo el histórico"

    @staticmethod
    def _filters_description(filters: ReportFilters) -> str:
        parts: list[str] = []
        if filters.category_name:
            parts.append(f"categoría <b>{_escape(filters.category_name)}</b>")
        if filters.contact_name:
            parts.append(f"contacto <b>{_escape(filters.contact_name)}</b>")
        if filters.status:
            parts.append(f"estado <b>{_escape(filters.status)}</b>")
        if filters.search:
            parts.append(f"búsqueda «{_escape(filters.search)}»")
        return ", ".join(parts)
