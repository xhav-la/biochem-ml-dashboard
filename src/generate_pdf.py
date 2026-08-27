# -*- coding: utf-8 -*-
"""
generate_pdf.py
==================
Krijon raportin PDF për një pacient: parametra biokimikë, demografi,
antropometri, parashikimet e modeleve ML dhe planin ushqimor.
"""
import datetime
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.enums import TA_CENTER

from . import config

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H1c", parent=styles["Heading1"], alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.grey))
styles.add(ParagraphStyle(name="SectionHeader", parent=styles["Heading2"],
                           textColor=colors.HexColor("#1f4e79"), spaceBefore=14))

RISK_COLORS = {
    "Low": "#2e7d32", "Normal": "#2e7d32",
    "Medium": "#f9a825", "Kufitar": "#f9a825",
    "Kufitar (pre-hipertension)": "#f9a825", "Prediabet": "#f9a825",
    "High": "#c62828", "I lartë": "#c62828",
    "Diabetik": "#c62828",
    "Të pamjaftueshme të dhëna": "#757575", "Nuk ka të dhëna": "#757575",
    "E panjohur": "#757575",
}


def _risk_row(label, category, extra=""):
    color_hex = RISK_COLORS.get(category, "#000000")
    return [
        Paragraph(f"<b>{label}</b>", styles["Normal"]),
        Paragraph(f'<font color="{color_hex}"><b>{category}</b></font>', styles["Normal"]),
        Paragraph(extra, styles["Normal"]),
    ]


def build_patient_pdf(output_path, patient_id, biochem: dict, demo: dict,
                       predictions: dict, diet: dict):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                             topMargin=1.5*cm, bottomMargin=1.5*cm,
                             leftMargin=1.8*cm, rightMargin=1.8*cm)
    story = []

    # ---------- Header ----------
    story.append(Paragraph("Raport Individual i Shëndetit Metabolik", styles["H1c"]))
    story.append(Paragraph(f"Pacienti ID: {patient_id} &nbsp;|&nbsp; "
                            f"Data e raportit: {datetime.date.today().isoformat()}",
                            ParagraphStyle(name="sub", parent=styles["Normal"], alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<i>Ky raport gjenerohet automatikisht nga modele machine learning bazuar në "
        "analiza laboratorike dhe kritere klinike standarde. NUK zëvendëson diagnozën "
        "e mjekut.</i>", styles["Small"]))
    story.append(Spacer(1, 0.5*cm))

    # ---------- Demografi & Antropometri ----------
    story.append(Paragraph("1. Të dhëna Demografike &amp; Antropometrike", styles["SectionHeader"]))
    demo_table_data = [
        ["Mosha", "Gjinia", "Nacionaliteti", "Pesha (kg)", "Gjatësia (cm)", "BMI"],
        [str(demo.get("MOSHA", "-")), demo.get("GJINIA", "-"), demo.get("NACIONALITETI", "-"),
         str(demo.get("PESHA_KG", "-")), str(demo.get("GJATESIA_CM", "-")), str(demo.get("BMI", "-"))],
    ]
    t = Table(demo_table_data, hAlign="LEFT", colWidths=[2.3*cm, 2*cm, 3.2*cm, 2.7*cm, 3*cm, 1.8*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Paragraph(
        "<i>Shënim: të dhënat demografike/antropometrike janë SINTETIKE (të gjeneruara për "
        "prototip), sepse dataseti origjinal nuk i përmban. Zëvendësohen me të dhëna reale "
        "kur të bëhen të disponueshme.</i>", styles["Small"]))
    story.append(Spacer(1, 0.4*cm))

    # ---------- Parametrat Biokimikë ----------
    story.append(Paragraph("2. Parametrat Biokimikë", styles["SectionHeader"]))
    bio_rows = [["Analiza", "Vlera", "Referenca"]]
    for key, label in [
        ("HEMOGLOBIN", "Hemoglobina"), ("HEMATOKRIT", "Hematokriti"),
        ("TROMBOCITI", "Trombocitet"), ("GLIKEMIA", "Glikemia (mmol/L)"),
        ("HBA1C", "HbA1c (%)"), ("HOLESTEROL", "Kolesteroli Total (mmol/L)"),
        ("LDL", "LDL (mmol/L)"), ("HDL", "HDL (mmol/L)"),
        ("TRIGLICERIDI", "Trigliceridet (mmol/L)"), ("CRP", "CRP (mg/L)"),
    ]:
        val = biochem.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            val_str = "N/A (mungon)"
        else:
            val_str = f"{val:.2f}"
        ref = config.REFERENCE_RANGES.get(key, "-")
        bio_rows.append([label, val_str, ref])

    t2 = Table(bio_rows, hAlign="LEFT", colWidths=[6.5*cm, 3*cm, 6*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t2)
    story.append(Spacer(1, 0.4*cm))

    # ---------- Parashikimet Klinike ----------
    story.append(Paragraph("3. Parashikimet e Modeleve ML", styles["SectionHeader"]))

    ms = predictions["sindroma_metabolike"]
    dia = predictions["rreziku_diabetit"]
    htn = predictions["hipertension"]
    lip = predictions["profili_lipidik"]

    risk_rows = [
        [Paragraph("<b>Vlerësimi</b>", styles["Normal"]),
         Paragraph("<b>Kategoria</b>", styles["Normal"]),
         Paragraph("<b>Detaje</b>", styles["Normal"])],
        _risk_row("Sindroma Metabolike", ms["kategoria"],
                  ", ".join(f"{k}: {v*100:.0f}%" for k, v in ms["probabilitetet"].items())),
        _risk_row("Rreziku i Diabetit", dia["kategoria"],
                  f"Afërsia me diabetin: {dia['afersia_perqindje']}%"),
        _risk_row("Hipertensioni", htn["kategoria"],
                  ", ".join(f"{k}: {v*100:.0f}%" for k, v in htn["probabilitetet"].items())),
        _risk_row("Profili Lipidik", lip["kategoria"],
                  ", ".join(f"{k}: {v*100:.0f}%" for k, v in lip["probabilitetet"].items())),
    ]
    t3 = Table(risk_rows, hAlign="LEFT", colWidths=[4.5*cm, 3.5*cm, 7.5*cm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    story.append(t3)

    missing_core = [k for k in ("GLIKEMIA", "HBA1C", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI")
                    if biochem.get(k) is None or (isinstance(biochem.get(k), float) and pd.isna(biochem.get(k)))]
    if missing_core:
        story.append(Paragraph(
            f"<i>Shënim: {len(missing_core)} analiza kyçe mungonin te ky pacient "
            f"({', '.join(missing_core)}) dhe u zëvendësuan me vlerën mediane statistikore "
            f"gjatë parashikimit -- rezultati përkatës mund të jetë më pak i saktë.</i>",
            styles["Small"]))
    story.append(Spacer(1, 0.4*cm))

    # ---------- Plani Ushqimor ----------
    story.append(Paragraph("4. Plani Ushqimor i Personalizuar", styles["SectionHeader"]))
    story.append(Paragraph(
        f"<b>Kaloritë bazale (BMR):</b> {diet['kalori_bazale_bmr']} kcal/ditë &nbsp;|&nbsp; "
        f"<b>Kaloritë ditore të synuara:</b> {diet['kalori_ditore_te_synuara']} kcal/ditë",
        styles["Normal"]))
    ms_split = diet["ndarja_makronutrienteve"]
    story.append(Paragraph(
        f"<b>Ndarja e makronutrientëve:</b> Proteina {ms_split['proteina_%']}% / "
        f"Yndyra {ms_split['yndyra_%']}% / Karbohidrate {ms_split['karbohidrate_%']}%",
        styles["Normal"]))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph("<b>Kufizime:</b>", styles["Normal"]))
    for r in diet["kufizime"]:
        story.append(Paragraph(f"• {r}", styles["Normal"]))
    story.append(Spacer(1, 0.15*cm))

    story.append(Paragraph("<b>Rekomandime:</b>", styles["Normal"]))
    for r in diet["rekomandime"]:
        story.append(Paragraph(f"• {r}", styles["Normal"]))

    if diet["shenime"]:
        story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph("<b>Shënime shtesë:</b>", styles["Normal"]))
        for r in diet["shenime"]:
            story.append(Paragraph(f"• {r}", styles["Normal"]))

    story.append(Spacer(1, 0.6*cm))
    story.append(Paragraph(
        "Raport i gjeneruar automatikisht — për qëllime informative/kërkimore. "
        "Konsultohu gjithmonë me mjekun tënd përpara vendimeve mjekësore ose dietike.",
        styles["Small"]))

    doc.build(story)
    return output_path
