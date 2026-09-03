from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.models import Estimate

FONT_NAME = "EstimateKorean"
FONT_BOLD_NAME = "EstimateKoreanBold"
_registered_font_paths: tuple[str, str | None] | None = None


class PdfFontConfigurationError(Exception):
    pass


class PdfGenerationError(Exception):
    pass


@dataclass(frozen=True)
class PdfRenderOptions:
    public: bool = False


def _candidate_font_paths() -> list[str]:
    candidates: list[str] = []
    if settings.pdf_font_path:
        candidates.append(settings.pdf_font_path)
    candidates.extend(
        [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\gulim.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        ]
    )
    return candidates


def _candidate_bold_font_paths() -> list[str]:
    candidates: list[str] = []
    if settings.pdf_font_bold_path:
        candidates.append(settings.pdf_font_bold_path)
    candidates.extend(
        [
            r"C:\Windows\Fonts\malgunbd.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        ]
    )
    return candidates


def _first_existing_path(candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def register_pdf_fonts() -> tuple[str, str]:
    global _registered_font_paths
    font_path = _first_existing_path(_candidate_font_paths())
    bold_path = _first_existing_path(_candidate_bold_font_paths())
    if font_path is None:
        raise PdfFontConfigurationError("PDF Korean font is not configured")
    if _registered_font_paths != (font_path, bold_path):
        pdfmetrics.registerFont(TTFont(FONT_NAME, font_path))
        if bold_path is not None:
            pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, bold_path))
        else:
            pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, font_path))
        _registered_font_paths = (font_path, bold_path)
    return FONT_NAME, FONT_BOLD_NAME


def format_money(value: Decimal) -> str:
    amount = value.quantize(Decimal("1")) if value == value.to_integral_value() else value.quantize(Decimal("0.01"))
    return f"{amount:,.0f}원" if amount == amount.to_integral_value() else f"{amount:,.2f}원"


def format_quantity(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def format_rate(value: Decimal) -> str:
    percent = value * Decimal("100")
    return f"{format_quantity(percent)}%"


def sanitize_pdf_filename(estimate_number: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", estimate_number.strip())
    safe = safe.strip("._") or "estimate"
    return f"estimate_{safe}.pdf"


def _display(value: object | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _build_styles(font_name: str, bold_font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=bold_font_name, fontSize=18, leading=24, alignment=TA_CENTER, spaceAfter=8),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName=bold_font_name, fontSize=11, leading=15, spaceBefore=8, spaceAfter=6),
        "normal": ParagraphStyle("normal", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=11),
        "right": ParagraphStyle("right", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=13, alignment=TA_RIGHT),
        "header": ParagraphStyle("header", parent=base["BodyText"], fontName=bold_font_name, fontSize=8, leading=10, alignment=TA_CENTER),
    }


def _paragraph(text: object | None, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_display(text).replace("\n", "<br />"), style)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _customer_rows(estimate: Estimate, options: PdfRenderOptions) -> list[list[object]]:
    if options.public:
        from app.crud.estimate_share import mask_customer_name

        return [["고객명", mask_customer_name(estimate.customer_name)]]
    rows = [["고객명", estimate.customer_name]]
    if estimate.customer_phone:
        rows.append(["연락처", estimate.customer_phone])
    if estimate.project_address:
        rows.append(["현장 주소", estimate.project_address])
    if estimate.notes:
        rows.append(["메모", estimate.notes])
    return rows


def _info_table(rows: list[list[object]], styles: dict[str, ParagraphStyle]) -> Table:
    table = Table([[_paragraph(label, styles["header"]), _paragraph(value, styles["normal"])] for label, value in rows], colWidths=[32 * mm, 128 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#C8CCD0")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F3F5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _items_table(estimate: Estimate, styles: dict[str, ParagraphStyle]) -> Table:
    rows: list[list[object]] = [
        [
            _paragraph("번호", styles["header"]),
            _paragraph("공사 분류", styles["header"]),
            _paragraph("항목", styles["header"]),
            _paragraph("선택 옵션", styles["header"]),
            _paragraph("단위", styles["header"]),
            _paragraph("수량", styles["header"]),
            _paragraph("단가", styles["header"]),
            _paragraph("금액", styles["header"]),
        ]
    ]
    sorted_items = sorted(estimate.items, key=lambda item: (item.sort_order, item.id or 0))
    for index, item in enumerate(sorted_items, start=1):
        option_text = item.option_name_snapshot
        if item.description_snapshot:
            option_text = f"{option_text}\n{item.description_snapshot}"
        rows.append(
            [
                _paragraph(index, styles["small"]),
                _paragraph(item.category_name_snapshot, styles["small"]),
                _paragraph(item.item_name_snapshot, styles["small"]),
                _paragraph(option_text, styles["small"]),
                _paragraph(item.unit_snapshot, styles["small"]),
                _paragraph(format_quantity(item.quantity), styles["right"]),
                _paragraph(format_money(item.unit_price_snapshot), styles["right"]),
                _paragraph(format_money(item.line_total), styles["right"]),
            ]
        )
    table = Table(rows, repeatRows=1, colWidths=[11 * mm, 26 * mm, 25 * mm, 41 * mm, 13 * mm, 16 * mm, 27 * mm, 27 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8BEC5")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9ECEF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_estimate_pdf(estimate: Estimate, options: PdfRenderOptions | None = None) -> bytes:
    options = options or PdfRenderOptions()
    try:
        font_name, bold_font_name = register_pdf_fonts()
        styles = _build_styles(font_name, bold_font_name)
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=13 * mm, rightMargin=13 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title="Interior Estimate")
        story: list[object] = []
        story.append(_paragraph("인테리어 견적서", styles["title"]))
        story.append(_paragraph("인테리어 견적 서비스", styles["normal"]))
        story.append(Spacer(1, 5 * mm))

        info_rows = [
            ["견적번호", estimate.estimate_number],
            ["작성일", estimate.created_at.strftime("%Y-%m-%d") if estimate.created_at else ""],
            ["유효기간", estimate.valid_until.isoformat() if estimate.valid_until else ""],
            ["견적 상태", estimate.status],
        ]
        story.append(_paragraph("견적 기본정보", styles["section"]))
        story.append(_info_table(info_rows, styles))
        story.append(_paragraph("고객정보", styles["section"]))
        story.append(_info_table(_customer_rows(estimate, options), styles))
        story.append(_paragraph("공사 항목", styles["section"]))
        story.append(_items_table(estimate, styles))
        story.append(Spacer(1, 5 * mm))

        total_rows = [
            ["공급가액", format_money(estimate.subtotal)],
            ["부가세", f"{format_money(estimate.vat_amount)} ({format_rate(estimate.vat_rate)})"],
            ["총 견적금액", format_money(estimate.total_amount)],
        ]
        story.append(_info_table(total_rows, styles))
        story.append(Spacer(1, 5 * mm))
        story.append(_paragraph("본 견적서는 제공된 정보와 선택 항목을 기준으로 작성된 참고 견적입니다. 현장 조건과 세부 범위에 따라 최종 금액은 달라질 수 있습니다.", styles["small"]))

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()
    except PdfFontConfigurationError:
        raise
    except Exception as exc:
        raise PdfGenerationError("Failed to generate PDF") from exc
