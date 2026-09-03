from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from backend.app.schemas.responses import AnalyzeResponse
from backend.app.logging import logger


class PDFReportGenerator:
    """
    Generates downloadable, comprehensive PDF intelligence audit reports using ReportLab.
    Documents all query parameters, detected metadata, models used, metric spatial evidence,
    and observable execution trace.
    """
    @staticmethod
    def generate(response: AnalyzeResponse, output_path: str | Path) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(out),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#64748B"),
        )
        h2_style = ParagraphStyle(
            "ReportH2",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=12,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
        )
        code_style = ParagraphStyle(
            "ReportCode",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
            fontName="Courier",
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("SATQUERY AI — INTELLIGENCE AUDIT REPORT", title_style))
        elements.append(Paragraph(f"Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Job ID: {response.request_id}", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3B82F6"), spaceAfter=15))

        # 2. Executive Summary Box
        summary_data = [
            [Paragraph("<b>Status:</b>", body_style), Paragraph(str(response.status.value), body_style)],
            [Paragraph("<b>Task:</b>", body_style), Paragraph(str(response.task.value), body_style)],
            [Paragraph("<b>Workflow:</b>", body_style), Paragraph(response.workflow_id, body_style)],
            [Paragraph("<b>Workflow Reason:</b>", body_style), Paragraph(response.workflow_reason, body_style)],
            [Paragraph("<b>Models Used:</b>", body_style), Paragraph(", ".join(response.models_used) if response.models_used else "None", body_style)],
            [Paragraph("<b>Confidence:</b>", body_style), Paragraph(f"{response.confidence:.4f}" if response.confidence is not None else "N/A (uncalibrated/missing)", body_style)],
        ]
        t_summary = Table(summary_data, colWidths=[120, 420])
        t_summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 15))

        # 3. User Query & AI Answer
        elements.append(Paragraph("Analysis Answer", h2_style))
        answer_text = response.answer or "No textual answer produced."
        ans_box = Table([[Paragraph(f"<b>Answer:</b><br/>{answer_text}", body_style)]], colWidths=[540])
        ans_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(ans_box)
        elements.append(Spacer(1, 15))

        # 4. Spatial & Area Statistics (if available)
        if response.evidence and response.evidence.spatial and response.evidence.spatial.statistics:
            stats = response.evidence.spatial.statistics
            elements.append(Paragraph("Metric Geospatial Statistics", h2_style))
            stats_data = [
                [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)],
                [Paragraph("Changed Pixels", body_style), Paragraph(str(stats.changed_pixels), body_style)],
                [Paragraph("Total Valid Pixels", body_style), Paragraph(str(stats.total_valid_pixels), body_style)],
                [Paragraph("Change Ratio", body_style), Paragraph(f"{stats.change_ratio * 100:.2f}%", body_style)],
                [Paragraph("Estimated Area (m²)", body_style), Paragraph(f"{stats.estimated_area_sq_m:,.2f}" if stats.estimated_area_sq_m else "N/A", body_style)],
                [Paragraph("Estimated Area (km²)", body_style), Paragraph(f"{stats.estimated_area_sq_km:,.4f}" if stats.estimated_area_sq_km else "N/A", body_style)],
                [Paragraph("Calculation Projection", body_style), Paragraph(stats.metric_crs or "Pixel space", body_style)],
            ]
            t_stats = Table(stats_data, colWidths=[200, 340])
            t_stats.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_stats)
            elements.append(Spacer(1, 15))

        # 5. Observable Execution Trace
        if response.execution_trace:
            elements.append(Paragraph("Observable Execution Trace", h2_style))
            trace_rows = [
                [Paragraph("<b>Timestamp</b>", body_style), Paragraph("<b>Step</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Duration</b>", body_style)]
            ]
            for step in response.execution_trace:
                dur = f"{step.duration_ms:.1f}ms" if step.duration_ms is not None else "-"
                trace_rows.append([
                    Paragraph(step.timestamp.split("T")[-1].replace("Z", ""), code_style),
                    Paragraph(step.step, body_style),
                    Paragraph(step.status.upper(), body_style),
                    Paragraph(dur, code_style)
                ])
            t_trace = Table(trace_rows, colWidths=[100, 260, 90, 90])
            t_trace.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_trace)
            elements.append(Spacer(1, 15))

        # 6. Warnings and Caveats
        if response.warnings:
            elements.append(Paragraph("System Warnings & Diagnostic Flags", h2_style))
            warn_items = [Paragraph(f"• {w}", body_style) for w in response.warnings]
            t_warn = Table([[w] for w in warn_items], colWidths=[540])
            t_warn.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#FCD34D")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(t_warn)

        doc.build(elements)
        logger.info(f"PDF audit report saved to {out}")
        return out
