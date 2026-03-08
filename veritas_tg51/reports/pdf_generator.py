"""
pdf_generator.py — TG-51 PDF worksheet reports.

US Letter, portrait.  Mirrors TG-51 Worksheet A (photon, Almond 1999 pp.1861-1862)
and Worksheet B (electron, 2024 WGTG51-e Addendum Report 385).

NOTE: All text uses only Latin-1 characters (U+0000-U+00FF) so that ReportLab's
built-in Helvetica/Times fonts render correctly without requiring an external TTF.
Unicode superscripts/subscripts are replaced with ASCII equivalents.
"""

from __future__ import annotations

import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..physics.tg51_photon import PhotonCalibrationInput, PhotonCalibrationResult
from ..physics.tg51_electron import ElectronCalibrationInput, ElectronCalibrationResult


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
NAVY        = colors.HexColor("#1B2A4A")
NAVY_LIGHT  = colors.HexColor("#2E4A7A")
BLUE_PALE   = colors.HexColor("#EBF5FB")
BLUE_MED    = colors.HexColor("#D6EAF8")
GREEN_PALE  = colors.HexColor("#D5F5E3")
GREEN_DARK  = colors.HexColor("#1E8449")
AMBER_PALE  = colors.HexColor("#FEF9E7")
AMBER_DARK  = colors.HexColor("#7D6608")
GREY_LIGHT  = colors.HexColor("#F4F6F7")
GREY_MED    = colors.HexColor("#D5D8DC")
GREY_DARK   = colors.HexColor("#717D7E")
WHITE       = colors.white
BLACK       = colors.black

PAGE_W = LETTER[0]
PAGE_H = LETTER[1]
LM = RM = 0.55 * inch
CONTENT_W = PAGE_W - LM - RM

_NC = 1e9   # C -> nC multiplier for display


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _S():
    base = getSampleStyleSheet()
    return {
        "h_title": ParagraphStyle(
            "h_title", parent=base["Normal"],
            fontSize=13, textColor=WHITE, fontName="Helvetica-Bold", leading=16,
        ),
        "h_sub": ParagraphStyle(
            "h_sub", parent=base["Normal"],
            fontSize=8.5, textColor=colors.HexColor("#AED6F1"),
            fontName="Helvetica", leading=11,
        ),
        "h_date": ParagraphStyle(
            "h_date", parent=base["Normal"],
            fontSize=9, textColor=WHITE, fontName="Helvetica",
            alignment=2,
        ),
        "label": ParagraphStyle(
            "label", parent=base["Normal"],
            fontSize=8.5, textColor=BLACK, fontName="Helvetica-Bold",
        ),
        "value": ParagraphStyle(
            "value", parent=base["Normal"],
            fontSize=8.5, textColor=BLACK, fontName="Helvetica",
        ),
        "step": ParagraphStyle(
            "step", parent=base["Normal"],
            fontSize=8, textColor=NAVY, fontName="Helvetica-Bold",
            alignment=1,
        ),
        "desc": ParagraphStyle(
            "desc", parent=base["Normal"],
            fontSize=8.5, textColor=BLACK, fontName="Helvetica",
        ),
        "eq": ParagraphStyle(
            "eq", parent=base["Normal"],
            fontSize=8, textColor=GREY_DARK, fontName="Helvetica-Oblique",
        ),
        "val_num": ParagraphStyle(
            "val_num", parent=base["Normal"],
            fontSize=9, textColor=BLACK, fontName="Helvetica-Bold",
            alignment=2,
        ),
        "unit": ParagraphStyle(
            "unit", parent=base["Normal"],
            fontSize=7.5, textColor=GREY_DARK, fontName="Helvetica-Oblique",
        ),
        "sec_hdr": ParagraphStyle(
            "sec_hdr", parent=base["Normal"],
            fontSize=8.5, textColor=WHITE, fontName="Helvetica-Bold",
        ),
        "dose_val": ParagraphStyle(
            "dose_val", parent=base["Normal"],
            fontSize=15, textColor=GREEN_DARK, fontName="Helvetica-Bold",
            alignment=1,
        ),
        "dose_lbl": ParagraphStyle(
            "dose_lbl", parent=base["Normal"],
            fontSize=9, textColor=BLACK, fontName="Helvetica",
            alignment=1,
        ),
        "warning": ParagraphStyle(
            "warning", parent=base["Normal"],
            fontSize=8, textColor=AMBER_DARK, fontName="Helvetica",
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"],
            fontSize=8.5, textColor=BLACK, fontName="Helvetica-Oblique",
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, textColor=GREY_DARK, fontName="Helvetica-Oblique",
        ),
        "sig": ParagraphStyle(
            "sig", parent=base["Normal"],
            fontSize=8.5, textColor=BLACK, fontName="Helvetica",
        ),
    }


# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------

def _header_banner(title: str, subtitle: str, date_str: str) -> Table:
    S = _S()
    data = [[
        Paragraph(title, S["h_title"]),
        Paragraph(date_str, S["h_date"]),
    ], [
        Paragraph(subtitle, S["h_sub"]),
        "",
    ]]
    tbl = Table(data, colWidths=[CONTENT_W - 1.5 * inch, 1.5 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (0, -1), 12),
        ("RIGHTPADDING",  (-1, 0), (-1, -1), 10),
    ]))
    return tbl


def _session_table(rows: list[list[str]]) -> Table:
    S = _S()
    tbl_data = []
    for row in rows:
        tbl_data.append([
            Paragraph(row[0], S["label"]),
            Paragraph(row[1], S["value"]),
            Paragraph(row[2], S["label"]),
            Paragraph(row[3], S["value"]),
        ])
    col = CONTENT_W / 4
    tbl = Table(tbl_data, colWidths=[col * 0.70, col * 1.30, col * 0.70, col * 1.30])
    tbl.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_MED),
        ("BACKGROUND",    (0, 0), (-1, -1), BLUE_PALE),
        ("BACKGROUND",    (0, 0), (0, -1), BLUE_MED),
        ("BACKGROUND",    (2, 0), (2, -1), BLUE_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _equipment_table(
    chamber_model: str,
    chamber_sn: str,
    n_dw: float,
    r_cav: float,
    elec_model: str,
    elec_sn: str,
    p_elec: float,
) -> Table:
    S = _S()
    def _h(t): return Paragraph(t, S["label"])
    def _v(t): return Paragraph(t, S["value"])

    data = [
        [_h("Ion Chamber"), _h("Serial No."), _h("N_D,w (Gy/C)"), _h("r_cav (cm)"),
         _h("Electrometer"), _h("Serial No."), _h("P_elec")],
        [_v(chamber_model), _v(chamber_sn), _v(f"{n_dw:.3E}"),
         _v(f"{r_cav:.3f}"), _v(elec_model), _v(elec_sn), _v(f"{p_elec:.4f}")],
    ]
    col_w = [CONTENT_W * f for f in [0.20, 0.10, 0.14, 0.10, 0.20, 0.10, 0.16]]
    tbl = Table(data, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("BACKGROUND",    (0, 1), (-1, 1), GREY_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _section_header(text: str) -> Table:
    S = _S()
    tbl = Table([[Paragraph(text, S["sec_hdr"])]], colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return tbl


_CW = [0.38 * inch, 3.20 * inch, 1.55 * inch, 1.87 * inch]


def _step_table_header() -> list:
    S = _S()
    return [[
        Paragraph("<b>Step</b>",      S["step"]),
        Paragraph("<b>Parameter / Equation</b>", S["label"]),
        Paragraph("<b>Value</b>",     S["label"]),
        Paragraph("<b>Unit  /  Ref</b>", S["label"]),
    ]]


def _step_row(step: str, desc: str, val: str, unit: str,
              highlight: bool = False, section_break: bool = False) -> list:
    S = _S()
    return [
        Paragraph(step, S["step"]),
        Paragraph(desc, S["desc"]),
        Paragraph(val,  S["val_num"]),
        Paragraph(unit, S["unit"]),
    ], highlight, section_break


def _step_table(rows_meta: list) -> Table:
    S = _S()
    hdr = _step_table_header()
    data = hdr + [r[0] for r in rows_meta]

    style_cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (2, 0), (2, -1), "RIGHT"),
    ]
    for i, (_, highlight, _sb) in enumerate(rows_meta):
        row_idx = i + 1
        if highlight:
            style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), GREEN_PALE))
            style_cmds.append(("FONTNAME",   (2, row_idx), (2, row_idx), "Helvetica-Bold"))
            style_cmds.append(("FONTSIZE",   (2, row_idx), (2, row_idx), 10))
            style_cmds.append(("TEXTCOLOR",  (2, row_idx), (2, row_idx), GREEN_DARK))

    tbl = Table(data, colWidths=_CW)
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _dose_result_box(label: str, value: str, unit: str,
                     label2: Optional[str] = None, value2: Optional[str] = None,
                     unit2: Optional[str] = None) -> Table:
    S = _S()
    if label2 and value2:
        data = [
            [Paragraph(label,  S["dose_lbl"]), Paragraph(label2,  S["dose_lbl"])],
            [Paragraph(value,  S["dose_val"]), Paragraph(value2,  S["dose_val"])],
            [Paragraph(unit,   S["unit"]),     Paragraph(unit2 or "", S["unit"])],
        ]
        tbl = Table(data, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
    else:
        data = [
            [Paragraph(label, S["dose_lbl"])],
            [Paragraph(value, S["dose_val"])],
            [Paragraph(unit,  S["unit"])],
        ]
        tbl = Table(data, colWidths=[CONTENT_W])

    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREEN_PALE),
        ("BOX",           (0, 0), (-1, -1), 1.5, GREEN_DARK),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, GREY_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _esignature(physicist: str, date_str: str) -> Table:
    """Electronic signature line — replaces wet-ink signature rows."""
    S = _S()
    name = physicist.strip() if physicist and physicist.strip() else "—"
    data = [[
        Paragraph(
            f"Electronically signed by: <b>{name}</b>     Date: {date_str}",
            S["sig"],
        ),
    ], [
        Paragraph("Veritas Medical Physics, LLC", S["sig"]),
    ]]
    tbl = Table(data, colWidths=[CONTENT_W])
    tbl.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("BACKGROUND",    (0, 0), (-1, -1), GREY_LIGHT),
        ("LINEABOVE",     (0, 1), (-1, 1), 0.25, GREY_MED),
    ]))
    return tbl


def _doc(output_path: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        rightMargin=RM, leftMargin=LM,
        topMargin=0.45 * inch, bottomMargin=0.45 * inch,
    )


# ---------------------------------------------------------------------------
# Internal story-builder helpers (reused by full session report)
# ---------------------------------------------------------------------------

def _photon_story_elements(
    inp: PhotonCalibrationInput,
    result: PhotonCalibrationResult,
    institution: str = "",
    physicist: str = "",
    machine: str = "",
    chamber_sn: str = "",
    electrometer_model: str = "",
    electrometer_sn: str = "",
    r_cav_cm: float = 0.0,
    notes: str = "",
    session_date: Optional[str] = None,
    field_size: str = "10x10 cm",
    mraw_adjusted: bool = False,
) -> list:
    """Return story elements for a single photon beam page (no doc.build)."""
    S = _S()
    story = []
    date_str = session_date or datetime.date.today().strftime("%Y-%m-%d")
    beam_label = f"{inp.energy_mv:.0f} MV{'  FFF' if inp.is_fff else ''}"

    story.append(_header_banner(
        "AAPM TG-51  -  Photon Beam Calibration",
        "Protocol: Almond et al. Med. Phys. 1999;26(9):1847-1870  +  "
        "WGTG51 Reports 374 (2022) & 385 (2024)  -  US Letter",
        date_str,
    ))
    story.append(Spacer(1, 0.10 * inch))
    story.append(_session_table([
        ["Institution:",  institution or "-",  "Beam energy:",   beam_label],
        ["Machine:",      machine or "-",       "Setup:",
         f"{'FFF' if inp.is_fff else 'Standard'}  |  {inp.setup_type}  {inp.ssd_or_sad_cm:.0f} cm"],
        ["Physicist:",    physicist or "-",     "Monitor units:", f"{inp.monitor_units:.0f} MU"],
        ["Date:",         date_str,             "Field size:",    field_size],
        ["Notes:",        notes or "-",         "",               ""],
    ]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_equipment_table(
        chamber_model=inp.chamber_model.title(), chamber_sn=chamber_sn or "-",
        n_dw=inp.n_dw_gy_per_c, r_cav=r_cav_cm,
        elec_model=electrometer_model or "-", elec_sn=electrometer_sn or "-",
        p_elec=inp.p_elec,
    ))
    story.append(Spacer(1, 0.08 * inch))

    story.append(_section_header("SECTION 4-5  |  Beam Quality  &  Chamber Factor k_Q"))
    rows = [_step_row("4", "%dd(10) method", result.pdd10x_method, "TG-51 Sec. VIII.B")]
    if inp.pdd10_open:
        rows.append(_step_row("4", "%dd(10)  [open beam]", f"{inp.pdd10_open:.2f}", "%"))
    rows.append(_step_row("4", "%dd(10)x  (photon component)", f"{result.pdd10x:.2f}", "%  [2014 Addendum]"))
    rows.append(_step_row("5", "k_Q  (Table I, interpolated)", f"{result.k_q:.3f}", "dimensionless"))
    story.append(_step_table(rows))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 6  |  Temperature-Pressure Correction  P_TP"))
    rows = [
        _step_row("6", "Temperature  T",  f"{inp.temperature_c:.1f}", "deg C"),
        _step_row("6", "Pressure  P",     f"{inp.pressure_kpa:.2f}",  "kPa"),
        _step_row("6", "P_TP = [(273.2 + T) / 295.2] x [101.33 / P]", f"{result.p_tp:.3f}", "Eq. (10)"),
    ]
    story.append(_step_table(rows))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 7  |  Polarity Correction  P_pol"))
    cal = "Positive (+)" if inp.calibration_polarity == "pos" else "Negative (-)"
    mraw_lbl = ("M_raw  (calibration polarity)  [*OUTPUT ADJUSTED — see note]"
                if mraw_adjusted else "M_raw  (calibration polarity)")
    rows = [
        _step_row("7", "Calibration polarity", cal, ""),
        _step_row("7", "M+_raw  (positive bias)", f"{inp.m_raw_pos * _NC:+.3f}", "nC"),
        _step_row("7", "M-_raw  (negative bias)", f"{inp.m_raw_neg * _NC:+.3f}", "nC"),
        _step_row("7", mraw_lbl, f"{result.m_raw_ref * _NC:.3f}", "nC",
                  highlight=mraw_adjusted),
        _step_row("7", "P_pol = (|M+| + |M-|) / (2 x |M_cal|)", f"{result.p_pol:.3f}", "Eq. (9)"),
    ]
    story.append(_step_table(rows))
    if mraw_adjusted:
        S = _S()
        story.append(Spacer(1, 0.03 * inch))
        story.append(Paragraph(
            "[*] Machine output adjustment was performed. The Reference Reading M_raw "
            "shown above is the post-adjustment reading used for the final dose calculation. "
            "Initial readings (M+_raw / M-_raw) were used for correction factor derivation only.",
            S["warning"],
        ))
    story.append(Spacer(1, 0.06 * inch))

    rows = [
        _step_row("8", "V_H  (high voltage)",   f"{inp.v_high:.0f}", "V"),
        _step_row("8", "V_L  (low voltage)",    f"{inp.v_low:.0f}",  "V"),
        _step_row("8", "M_H  (reading at V_H)", f"{inp.m_raw_high * _NC:.3f}", "nC"),
        _step_row("8", "M_L  (reading at V_L)", f"{inp.m_raw_low  * _NC:.3f}", "nC"),
        _step_row("8", "P_ion = (1 - V_L/V_H) / (M_L/M_H - V_L/V_H)", f"{result.p_ion:.3f}", "Eq. (12)  [pulsed]"),
        _step_row("8", "P_elec", f"{result.p_elec:.3f}", "Sec. VII.B"),
        _step_row("8", "P_rp  (FFF radial correction)", f"{inp.p_rp:.3f}", "WGTG51-X Sec. 4.5"),
        _step_row("8", "P_leak", f"{result.p_leak:.3f}", "Report 374 Sec. 4.4.1"),
    ]
    story.append(KeepTogether([
        _section_header("SECTION 8  |  Ion Recombination  P_ion  &  Other Correction Factors"),
        Spacer(1, 0.02 * inch),
        _step_table(rows),
    ]))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 9  |  Corrected Reading  M = M_raw x P_ion x P_TP x P_elec x P_pol x P_rp x P_leak"))
    story.append(_step_table([_step_row("9", "M_corrected", f"{result.m_corrected:.3E}", "C  [Eq. 8]")]))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 10  |  Absorbed Dose  D_w(10 cm) = M x k_Q x N_D,w"))
    dose_str = f"{result.dose_10cm_cgy_per_mu:.3f} cGy/MU"
    dose_lbl = f"D_w at 10 cm  (beam: {beam_label})"
    dose_unit = (f"D = {result.m_corrected:.3E} C  x  {result.k_q:.3f}  "
                 f"x  {inp.n_dw_gy_per_c:.3E} Gy/C  /  {inp.monitor_units:.0f} MU  x  100")
    if result.dose_dmax_cgy_per_mu is not None:
        err_max = (result.dose_dmax_cgy_per_mu - 1.000) * 100.0
        sign_max = "+" if err_max >= 0 else ""
        story.append(_dose_result_box(
            dose_lbl, dose_str, dose_unit,
            "D_w at d_max",
            f"{result.dose_dmax_cgy_per_mu:.3f} cGy/MU  ({sign_max}{err_max:.1f}%)",
            "from clinical PDD/TMR  [Report 374 Sec. 2.4.3]",
        ))
    else:
        story.append(_dose_result_box(dose_lbl, dose_str, dose_unit))

    if result.warnings:
        story.append(Spacer(1, 0.08 * inch))
        story.append(_section_header("WARNINGS"))
        story.append(Spacer(1, 0.04 * inch))
        for w in result.warnings:
            story.append(Paragraph(f"[!]  {w}", S["warning"]))
            story.append(Spacer(1, 0.03 * inch))

    story.append(Spacer(1, 0.10 * inch))
    if notes:
        story.append(Paragraph(f"Notes: {notes}", S["note"]))
        story.append(Spacer(1, 0.08 * inch))
    story.append(_esignature(physicist, date_str))
    story.append(Spacer(1, 0.10 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MED))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph(
        "Almond PR et al. AAPM TG-51. Med. Phys. 1999;26(9):1847-1870.  |  "
        "McEwen MR et al. TG-51 Addendum. Med. Phys. 2014;41:041501.  |  "
        "Muir BR et al. Report 374. Med. Phys. 2022;49(9):6739-6764.  |  "
        "Generated by Veritas TG-51",
        S["footer"],
    ))
    return story


# ---------------------------------------------------------------------------
# Photon report  (Worksheet A)
# ---------------------------------------------------------------------------

def generate_photon_report(
    inp: PhotonCalibrationInput,
    result: PhotonCalibrationResult,
    output_path: str,
    institution: str = "",
    physicist: str = "",
    machine: str = "",
    chamber_sn: str = "",
    electrometer_model: str = "",
    electrometer_sn: str = "",
    r_cav_cm: float = 0.0,
    notes: str = "",
    session_date: Optional[str] = None,
    mraw_adjusted: bool = False,
) -> None:
    """Photon beam calibration report (TG-51 / 2014 Addendum)."""
    doc = _doc(output_path)
    story = _photon_story_elements(
        inp, result,
        institution=institution, physicist=physicist, machine=machine,
        chamber_sn=chamber_sn, electrometer_model=electrometer_model,
        electrometer_sn=electrometer_sn, r_cav_cm=r_cav_cm,
        notes=notes, session_date=session_date,
        mraw_adjusted=mraw_adjusted,
    )
    doc.build(story)


# ---------------------------------------------------------------------------
# Electron report  (Worksheet B — 2024 Addendum)
# ---------------------------------------------------------------------------

def _electron_story_elements(
    inp: ElectronCalibrationInput,
    result: ElectronCalibrationResult,
    institution: str = "",
    physicist: str = "",
    machine: str = "",
    chamber_sn: str = "",
    electrometer_model: str = "",
    electrometer_sn: str = "",
    r_cav_cm: float = 0.0,
    notes: str = "",
    session_date: Optional[str] = None,
    cone: str = "10x10 cm",
    mraw_adjusted: bool = False,
) -> list:
    """Return story elements for a single electron beam page (no doc.build)."""
    S = _S()
    story = []
    date_str = session_date or datetime.date.today().strftime("%Y-%m-%d")
    beam_label = f"{inp.energy_mev:.0f} MeV electrons"

    story.append(_header_banner(
        "AAPM TG-51  -  Electron Beam Calibration",
        "Protocol: 2024 WGTG51-e Addendum  -  "
        "Muir et al. Med. Phys. 2024;51:5840-5857  (Report 385)  -  US Letter",
        date_str,
    ))
    story.append(Spacer(1, 0.06 * inch))
    notice = Table([[Paragraph(
        "2024 Addendum formalism:  k_Q = k'_Q x k_Qecal.  "
        "No measured gradient correction P_gr required for cylindrical chambers.  "
        "Cylindrical chamber CENTRAL AXIS positioned at d_ref "
        "(no EPOM shift for the reference measurement).",
        ParagraphStyle("notice", parent=S["desc"],
                       backColor=BLUE_MED, textColor=colors.HexColor("#154360"),
                       borderPad=5),
    )]], colWidths=[CONTENT_W])
    notice.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#2980B9"))]))
    story.append(notice)
    story.append(Spacer(1, 0.08 * inch))

    story.append(_session_table([
        ["Institution:", institution or "-",  "Beam energy:", beam_label],
        ["Machine:",     machine or "-",      "SSD:",         f"{inp.ssd_cm:.1f} cm"],
        ["Physicist:",   physicist or "-",    "Monitor units:", f"{inp.monitor_units:.0f} MU"],
        ["Date:",        date_str,            "Applicator/cone:", cone],
        ["Notes:",       notes or "-",        "",             ""],
    ]))
    story.append(Spacer(1, 0.08 * inch))

    story.append(_equipment_table(
        chamber_model=inp.chamber_model.title(),
        chamber_sn=chamber_sn or "-",
        n_dw=inp.n_dw_gy_per_c,
        r_cav=r_cav_cm,
        elec_model=electrometer_model or "-",
        elec_sn=electrometer_sn or "-",
        p_elec=inp.p_elec,
    ))
    story.append(Spacer(1, 0.08 * inch))

    story.append(_section_header("SECTIONS 4-5  |  Beam Quality  R_50  &  k_Q"))
    rows = [
        _step_row("4", "I_50  (50% ionization depth, EPOM-corrected for cyl. chambers)",
                  f"{inp.i50_cm:.3f}", "cm  [Report 385 Sec. III.B]"),
        _step_row("4", "R_50 = 1.029 x I_50 - 0.06  (for I_50 <= 10 cm)",
                  f"{result.r50_cm:.3f}", "cm  [Eq. 3 / TG-51 Eq. 16]"),
        _step_row("4", "d_ref = 0.6 x R_50 - 0.1",
                  f"{result.d_ref_cm:.3f}", "cm  [Eq. 2 / TG-51 Eq. 18]"),
        _step_row("5a", "k_Qecal  (Table 4 cyl. / Table 6 PP)",
                  f"{result.k_qecal:.4f}", "Report 385"),
        _step_row("5b", "k'_Q  (fit to R_50, Table 5 / 7)",
                  f"{result.k_q_prime:.4f}", "Report 385  Eq. 7/8"),
        _step_row("5c", "k_Q = k'_Q x k_Qecal",
                  f"{result.k_q:.3f}", "Eq. (4)"),
    ]
    story.append(_step_table(rows))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 6  |  Temperature-Pressure Correction  P_TP"))
    rows = [
        _step_row("6", "Temperature  T",  f"{inp.temperature_c:.1f}", "deg C"),
        _step_row("6", "Pressure  P",     f"{inp.pressure_kpa:.2f}",  "kPa"),
        _step_row("6", "P_TP = [(273.2 + T) / 295.2] x [101.33 / P]",
                  f"{result.p_tp:.3f}", "Eq. (10)"),
    ]
    story.append(_step_table(rows))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header("SECTION 7  |  Polarity Correction  P_pol"))
    cal = "Positive (+)" if inp.calibration_polarity == "pos" else "Negative (-)"
    mraw_lbl = ("M_raw  (calibration polarity)  [*OUTPUT ADJUSTED — see note]"
                if mraw_adjusted else "M_raw  (calibration polarity)")
    rows = [
        _step_row("7", "Calibration polarity", cal, ""),
        _step_row("7", "M+_raw  (positive bias, at d_ref)",
                  f"{inp.m_raw_pos * _NC:+.3f}", "nC"),
        _step_row("7", "M-_raw  (negative bias, at d_ref)",
                  f"{inp.m_raw_neg * _NC:+.3f}", "nC"),
        _step_row("7", mraw_lbl,
                  f"{result.m_raw_ref * _NC:.3f}", "nC",
                  highlight=mraw_adjusted),
        _step_row("7", "P_pol = (|M+| + |M-|) / (2 x |M_cal|)",
                  f"{result.p_pol:.3f}", "Eq. (9)"),
    ]
    story.append(_step_table(rows))
    if mraw_adjusted:
        S = _S()
        story.append(Spacer(1, 0.03 * inch))
        story.append(Paragraph(
            "[*] Machine output adjustment was performed. The Reference Reading M_raw "
            "shown above is the post-adjustment reading used for the final dose calculation. "
            "Initial readings (M+_raw / M-_raw) were used for correction factor derivation only.",
            S["warning"],
        ))
    story.append(Spacer(1, 0.06 * inch))

    rows = [
        _step_row("8", "V_H  (high voltage)",  f"{inp.v_high:.0f}", "V"),
        _step_row("8", "V_L  (low voltage)",   f"{inp.v_low:.0f}",  "V"),
        _step_row("8", "M_H  (reading at V_H)", f"{inp.m_raw_high * _NC:.3f}", "nC"),
        _step_row("8", "M_L  (reading at V_L)", f"{inp.m_raw_low  * _NC:.3f}", "nC"),
        _step_row("8", "P_ion = (1 - V_L/V_H) / (M_L/M_H - V_L/V_H)",
                  f"{result.p_ion:.3f}", "Eq. (12)  [pulsed]"),
        _step_row("8", "P_elec  (electrometer calibration factor)",
                  f"{result.p_elec:.3f}", "Sec. VII.B"),
        _step_row("8", "P_leak  (leakage correction factor)",
                  f"{result.p_leak:.3f}", "Report 374 Sec. 4.4.1"),
    ]
    story.append(KeepTogether([
        _section_header("SECTION 8  |  Ion Recombination  P_ion  &  Other Corrections"),
        Spacer(1, 0.02 * inch),
        _step_table(rows),
    ]))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header(
        "SECTION 9  |  Corrected Reading  "
        "M = M_raw x P_ion x P_TP x P_elec x P_pol x P_leak"))
    story.append(_step_table([
        _step_row("9", "M_corrected", f"{result.m_corrected:.3E}", "C  [Eq. 9]"),
    ]))
    story.append(Spacer(1, 0.06 * inch))

    story.append(_section_header(
        "SECTION 10  |  Absorbed Dose to Water  D_w(d_ref) = M x k_Q x N_D,w"))
    dose_str  = f"{result.dose_dref_cgy_per_mu:.3f} cGy/MU"
    dose_lbl  = f"D_w at d_ref = {result.d_ref_cm:.2f} cm  (beam: {beam_label})"
    dose_unit = (f"D = {result.m_corrected:.3E} C  x  {result.k_q:.3f}  "
                 f"x  {inp.n_dw_gy_per_c:.3E} Gy/C  /  {inp.monitor_units:.0f} MU  x  100")
    if result.dose_dmax_cgy_per_mu is not None:
        err_max = (result.dose_dmax_cgy_per_mu - 1.000) * 100.0
        sign_max = "+" if err_max >= 0 else ""
        story.append(_dose_result_box(
            dose_lbl, dose_str, dose_unit,
            "D_w at d_max",
            f"{result.dose_dmax_cgy_per_mu:.3f} cGy/MU  ({sign_max}{err_max:.1f}%)",
            "from clinical %dd(d_ref)  [Report 374 Sec. 2.4.3]",
        ))
    else:
        story.append(_dose_result_box(dose_lbl, dose_str, dose_unit))

    if result.warnings:
        story.append(Spacer(1, 0.08 * inch))
        story.append(_section_header("WARNINGS"))
        story.append(Spacer(1, 0.04 * inch))
        for w in result.warnings:
            story.append(Paragraph(f"[!]  {w}", S["warning"]))
            story.append(Spacer(1, 0.03 * inch))

    story.append(Spacer(1, 0.10 * inch))
    if notes:
        story.append(Paragraph(f"Notes: {notes}", S["note"]))
        story.append(Spacer(1, 0.08 * inch))
    story.append(_esignature(physicist, date_str))
    story.append(Spacer(1, 0.10 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MED))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph(
        "Almond PR et al. AAPM TG-51 protocol. Med. Phys. 1999;26(9):1847-1870.  |  "
        "Muir BR et al. WGTG51 Report 374. Med. Phys. 2022;49(9):6739-6764.  |  "
        "Muir BR et al. WGTG51 Report 385. Med. Phys. 2024;51:5840-5857.  |  "
        "Generated by Veritas TG-51",
        S["footer"],
    ))
    return story


def generate_electron_report(
    inp: ElectronCalibrationInput,
    result: ElectronCalibrationResult,
    output_path: str,
    institution: str = "",
    physicist: str = "",
    machine: str = "",
    chamber_sn: str = "",
    electrometer_model: str = "",
    electrometer_sn: str = "",
    r_cav_cm: float = 0.0,
    notes: str = "",
    session_date: Optional[str] = None,
    mraw_adjusted: bool = False,
) -> None:
    """Electron beam calibration report (TG-51 / 2024 Addendum Report 385)."""
    doc = _doc(output_path)
    story = _electron_story_elements(
        inp, result,
        institution=institution, physicist=physicist, machine=machine,
        chamber_sn=chamber_sn, electrometer_model=electrometer_model,
        electrometer_sn=electrometer_sn, r_cav_cm=r_cav_cm,
        notes=notes, session_date=session_date,
        mraw_adjusted=mraw_adjusted,
    )
    doc.build(story)


# ---------------------------------------------------------------------------
# Full session report  (cover + summary + per-beam pages)
# ---------------------------------------------------------------------------

def generate_full_session_report(
    beam_results: list,
    output_path: str,
    institution: str = "",
    physicist: str = "",
    machine: str = "",
    chamber_model: str = "",
    chamber_sn: str = "",
    electrometer_model: str = "",
    electrometer_sn: str = "",
    r_cav_cm: float = 0.0,
    session_date: Optional[str] = None,
    chamber_calibration_date: Optional[str] = None,
    electrometer_calibration_date: Optional[str] = None,
) -> None:
    """
    Generate a complete session PDF: cover page + summary table + per-beam detail pages.

    beam_results: list of (beam, inp, result) tuples where beam has .modality,
                  inp is PhotonCalibrationInput or ElectronCalibrationInput,
                  result is the corresponding result object.
    """
    from reportlab.platypus import PageBreak

    S = _S()
    doc = _doc(output_path)
    date_str = session_date or datetime.date.today().strftime("%Y-%m-%d")
    story = []

    # ── Cover page ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * inch))
    cover_title = Table([[Paragraph(
        "Veritas TG-51 Calibration Report",
        ParagraphStyle("cover_title", parent=S["h_title"],
                       fontSize=22, alignment=1, textColor=NAVY),
    )]], colWidths=[CONTENT_W])
    cover_title.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(cover_title)
    story.append(Spacer(1, 0.15 * inch))
    story.append(HRFlowable(width="80%", thickness=2, color=NAVY, hAlign="CENTER"))
    story.append(Spacer(1, 0.20 * inch))

    def _cal_overdue(cal_str):
        """Return True if cal_str date is more than 2 years before session date."""
        if not cal_str or cal_str == "-":
            return False
        try:
            cal = datetime.date.fromisoformat(str(cal_str).split()[0])
            sess = datetime.date.fromisoformat(date_str)
            return (sess - cal).days > 730
        except Exception:
            return False

    ch_cal_raw = str(chamber_calibration_date).split()[0] if chamber_calibration_date else None
    el_cal_raw = str(electrometer_calibration_date).split()[0] if electrometer_calibration_date else None
    ch_overdue = _cal_overdue(ch_cal_raw)
    el_overdue = _cal_overdue(el_cal_raw)
    ch_cal = (ch_cal_raw or "-") + ("  [!] OVERDUE" if ch_overdue else "")
    el_cal = (el_cal_raw or "-") + ("  [!] OVERDUE" if el_overdue else "")

    warn_style = ParagraphStyle("cal_warn", parent=S["value"],
                                textColor=AMBER_DARK, fontName="Helvetica-Bold")

    cover_info_rows = [
        (0, "Operator / Physicist:", physicist or "-", False),
        (1, "Institution:",          institution or "-", False),
        (2, "Treatment Machine:",    machine or "-", False),
        (3, "Chamber:",              f"{chamber_model}  S/N: {chamber_sn}" if chamber_sn else chamber_model or "-", False),
        (4, "Chamber cal. date:",    ch_cal, ch_overdue),
        (5, "Electrometer:",         f"{electrometer_model}  S/N: {electrometer_sn}" if electrometer_sn else electrometer_model or "-", False),
        (6, "Electrometer cal. date:", el_cal, el_overdue),
        (7, "Date:",                 date_str, False),
        (8, "Beams measured:",       str(len(beam_results)), False),
    ]
    ci_data = [[
        Paragraph(r[1], S["label"]),
        Paragraph(r[2], warn_style if r[3] else S["value"]),
    ] for r in cover_info_rows]
    ci_tbl = Table(ci_data, colWidths=[CONTENT_W * 0.38, CONTENT_W * 0.62])
    ci_style = [
        ("BACKGROUND",    (0, 0), (-1, -1), BLUE_PALE),
        ("BACKGROUND",    (0, 0), (0, -1), BLUE_MED),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    for r in cover_info_rows:
        if r[3]:  # overdue row
            ci_style.append(("BACKGROUND", (0, r[0]), (-1, r[0]), AMBER_PALE))
    ci_tbl.setStyle(TableStyle(ci_style))
    story.append(ci_tbl)
    if ch_overdue or el_overdue:
        story.append(Spacer(1, 0.06 * inch))
        which = []
        if ch_overdue:
            which.append("Ion chamber")
        if el_overdue:
            which.append("Electrometer")
        story.append(Paragraph(
            f"[!] CALIBRATION OVERDUE (>2 years):  {' and '.join(which)}.  "
            "Re-calibration required before clinical use.",
            ParagraphStyle("overdue_warn", parent=S["warning"],
                           fontName="Helvetica-Bold", fontSize=9,
                           backColor=AMBER_PALE, borderPad=4),
        ))
    story.append(Spacer(1, 0.20 * inch))

    # ── Summary table on page 1 ───────────────────────────────────────────────
    story.append(Paragraph("<b>Calibration Summary  —  Dose at d_max</b>",
                           ParagraphStyle("sum_title", parent=S["label"],
                                          fontSize=10, textColor=NAVY, spaceAfter=4)))
    story.append(Spacer(1, 0.06 * inch))

    sum_hdr = [
        Paragraph("<b>Beam</b>",              S["label"]),
        Paragraph("<b>Modality</b>",          S["label"]),
        Paragraph("<b>D_w d_max (cGy/MU)</b>", S["label"]),
        Paragraph("<b>% Error</b>",           S["label"]),
        Paragraph("<b>Status</b>",            S["label"]),
    ]
    sum_rows = [sum_hdr]
    sum_styles = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("BOX",           (0, 0), (-1, -1), 0.5, GREY_MED),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, GREY_MED),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_LIGHT]),
    ]

    for i, item in enumerate(beam_results):
        beam, inp, result = item[0], item[1], item[2]
        field_info = item[3] if len(item) > 3 else {}
        row_idx = i + 1
        if beam.modality == "photon":
            label  = f"{inp.energy_mv:.0f} MV{'  FFF' if inp.is_fff else ''}"
            mod    = "Photon (FFF)" if inp.is_fff else "Photon"
            dose   = result.dose_dmax_cgy_per_mu if result.dose_dmax_cgy_per_mu is not None else result.dose_10cm_cgy_per_mu
            dose_s = f"{dose:.3f}"
        else:
            label  = f"{inp.energy_mev:.0f} MeV"
            mod    = "Electron"
            dose   = result.dose_dmax_cgy_per_mu if result.dose_dmax_cgy_per_mu is not None else result.dose_dref_cgy_per_mu
            dose_s = f"{dose:.3f}"

        err    = (dose - 1.000) * 100.0
        sign   = "+" if err >= 0 else ""
        err_s  = f"{sign}{err:.1f}%"
        ok     = abs(err) <= 2.0
        status = "PASS" if ok else "REVIEW"

        sum_rows.append([
            Paragraph(label,  S["value"]),
            Paragraph(mod,    S["value"]),
            Paragraph(dose_s, S["val_num"]),
            Paragraph(err_s,  S["val_num"]),
            Paragraph(status, S["label"]),
        ])
        bg = GREEN_PALE if ok else AMBER_PALE
        tc = GREEN_DARK if ok else AMBER_DARK
        sum_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))
        sum_styles.append(("TEXTCOLOR",  (4, row_idx), (4, row_idx), tc))

    col_w = [CONTENT_W * f for f in [0.22, 0.22, 0.22, 0.17, 0.17]]
    sum_tbl = Table(sum_rows, colWidths=col_w)
    sum_tbl.setStyle(TableStyle(sum_styles))
    story.append(sum_tbl)
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "Green: within 2% of 1.000 cGy/MU.  Amber: deviation exceeds 2% — review required.",
        S["note"],
    ))
    story.append(Spacer(1, 0.2 * inch))
    story.append(_esignature(physicist, date_str))
    story.append(PageBreak())

    # ── Individual beam pages ────────────────────────────────────────────────
    common_kw = dict(
        institution=institution, physicist=physicist, machine=machine,
        chamber_sn=chamber_sn, electrometer_model=electrometer_model,
        electrometer_sn=electrometer_sn, r_cav_cm=r_cav_cm,
        session_date=session_date,
    )
    for idx, item in enumerate(beam_results):
        beam, inp, result = item[0], item[1], item[2]
        field_info = item[3] if len(item) > 3 else {}
        mraw_adj = field_info.get("mraw_adjusted", False)
        if beam.modality == "photon":
            page_elements = _photon_story_elements(
                inp, result, **common_kw,
                field_size=field_info.get("field_size", "10x10 cm"),
                mraw_adjusted=mraw_adj,
            )
        else:
            page_elements = _electron_story_elements(
                inp, result, **common_kw,
                cone=field_info.get("cone", "10x10 cm"),
                mraw_adjusted=mraw_adj,
            )
        story.extend(page_elements)
        if idx < len(beam_results) - 1:
            story.append(PageBreak())

    doc.build(story)


# ---------------------------------------------------------------------------
# Reprint from stored CalibrationRecord
# ---------------------------------------------------------------------------

def generate_report_from_record(record, output_path: str) -> None:
    """Generate a PDF directly from a CalibrationRecord (no input objects needed)."""
    import json
    S = _S()
    doc = _doc(output_path)
    story = []

    date_str = record.recorded_at.strftime("%Y-%m-%d")
    physicist = record.physicist or "-"

    if record.modality == "photon":
        fff = " FFF" if record.is_fff else ""
        beam_label = f"{record.energy_nominal:.0f} MV{fff}"
        story.append(_header_banner(
            "AAPM TG-51  -  Photon Beam Calibration  [Record Reprint]",
            f"Protocol: TG-51 (1999) + WGTG51 Reports 374 & 385  |  Record #{record.id}",
            date_str,
        ))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_session_table([
            ["Physicist:", physicist, "Beam energy:", beam_label],
            ["Record ID:", str(record.id),
             "Saved:", record.recorded_at.strftime("%Y-%m-%d %H:%M")],
        ]))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_section_header("CALIBRATION DATA"))
        rows_meta = [
            _step_row("2",  "Chamber model", record.chamber_model.title(), ""),
            _step_row("2",  "N_D,w^60Co (Gy/C)", f"{record.n_dw_gy_per_c:.3E}", "Gy/C"),
            _step_row("3",  "Monitor units", f"{record.monitor_units:.0f}", "MU"),
            _step_row("4",  "%dd(10)x", f"{record.pdd10x:.2f}" if record.pdd10x else "-", "%"),
            _step_row("4",  "Method", record.pdd10x_method or "-", ""),
            _step_row("5",  "k_Q", f"{record.k_q:.4f}", ""),
            _step_row("6",  "Temperature", f"{record.temperature_c:.1f}", "deg C"),
            _step_row("6",  "Pressure", f"{record.pressure_kpa:.2f}", "kPa"),
            _step_row("6",  "P_TP", f"{record.p_tp:.5f}", "Eq. (10)"),
            _step_row("7",  "P_pol", f"{record.p_pol:.5f}", "Eq. (9)"),
            _step_row("8",  "P_ion", f"{record.p_ion:.5f}", "Eq. (12)"),
            _step_row("8",  "P_elec", f"{record.p_elec:.4f}", ""),
            _step_row("8",  "P_rp", f"{record.p_rp:.4f}", ""),
            _step_row("8",  "P_leak", f"{record.p_leak:.5f}", ""),
            _step_row("9",  "M_corrected", f"{record.m_corrected:.4E}", "C"),
            _step_row("10", "D_w at 10 cm", f"{record.dose_ref_cgy_per_mu:.4f}",
                      "cGy/MU", highlight=True),
        ]
        if record.dose_dmax_cgy_per_mu is not None:
            rows_meta.append(_step_row("11", "D_w at d_max",
                             f"{record.dose_dmax_cgy_per_mu:.4f}", "cGy/MU", highlight=True))
        story.append(_step_table(rows_meta))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_dose_result_box(
            f"D_w at 10 cm  (beam: {beam_label})",
            f"{record.dose_ref_cgy_per_mu:.4f} cGy/MU",
            "cGy/MU  [TG-51 Eq. 3]",
        ))

    else:  # electron
        beam_label = f"{record.energy_nominal:.0f} MeV electrons"
        story.append(_header_banner(
            "AAPM TG-51  -  Electron Beam Calibration  [Record Reprint]",
            f"Protocol: 2024 WGTG51-e Addendum (Report 385)  |  Record #{record.id}",
            date_str,
        ))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_session_table([
            ["Physicist:", physicist, "Beam energy:", beam_label],
            ["Record ID:", str(record.id),
             "Saved:", record.recorded_at.strftime("%Y-%m-%d %H:%M")],
        ]))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_section_header("CALIBRATION DATA"))
        rows_meta = [
            _step_row("2",  f"Chamber  ({record.chamber_type or 'cylindrical'})",
                      record.chamber_model.title(), ""),
            _step_row("2",  "N_D,w^60Co (Gy/C)", f"{record.n_dw_gy_per_c:.3E}", "Gy/C"),
            _step_row("3",  "Energy", f"{record.energy_nominal:.0f}", "MeV"),
            _step_row("3",  "Monitor units", f"{record.monitor_units:.0f}", "MU"),
            _step_row("4",  "R_50", f"{record.r50_cm:.3f}" if record.r50_cm else "-", "cm"),
            _step_row("4",  "d_ref", f"{record.d_ref_cm:.3f}" if record.d_ref_cm else "-", "cm"),
            _step_row("5a", "k_Qecal", f"{record.k_qecal:.4f}" if record.k_qecal else "-", ""),
            _step_row("5b", "k'_Q", f"{record.k_q_prime:.4f}" if record.k_q_prime else "-", ""),
            _step_row("5c", "k_Q", f"{record.k_q:.5f}", "Eq. (4)"),
            _step_row("6",  "Temperature", f"{record.temperature_c:.1f}", "deg C"),
            _step_row("6",  "Pressure", f"{record.pressure_kpa:.2f}", "kPa"),
            _step_row("6",  "P_TP", f"{record.p_tp:.5f}", "Eq. (10)"),
            _step_row("7",  "P_pol", f"{record.p_pol:.5f}", "Eq. (9)"),
            _step_row("8",  "P_ion", f"{record.p_ion:.5f}", "Eq. (12)"),
            _step_row("8",  "P_elec", f"{record.p_elec:.4f}", ""),
            _step_row("8",  "P_leak", f"{record.p_leak:.5f}", ""),
            _step_row("9",  "M_corrected", f"{record.m_corrected:.4E}", "C"),
            _step_row("10", "D_w at d_ref", f"{record.dose_ref_cgy_per_mu:.4f}",
                      "cGy/MU", highlight=True),
        ]
        if record.dose_dmax_cgy_per_mu is not None:
            rows_meta.append(_step_row("11", "D_w at d_max",
                             f"{record.dose_dmax_cgy_per_mu:.4f}", "cGy/MU", highlight=True))
        story.append(_step_table(rows_meta))
        story.append(Spacer(1, 0.08 * inch))
        story.append(_dose_result_box(
            f"D_w at d_ref  (beam: {beam_label})",
            f"{record.dose_ref_cgy_per_mu:.4f} cGy/MU",
            "cGy/MU  [Report 385 Eq. 4]",
        ))

    warnings = json.loads(record.warnings_json or "[]")
    if warnings:
        story.append(Spacer(1, 0.08 * inch))
        story.append(_section_header("WARNINGS"))
        story.append(Spacer(1, 0.04 * inch))
        for w in warnings:
            story.append(Paragraph(f"[!]  {w}", S["warning"]))
            story.append(Spacer(1, 0.03 * inch))

    if record.notes:
        story.append(Spacer(1, 0.06 * inch))
        story.append(Paragraph(f"Notes: {record.notes}", S["note"]))

    story.append(Spacer(1, 0.10 * inch))
    story.append(_esignature(physicist, date_str))
    story.append(Spacer(1, 0.08 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_MED))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph(
        "Almond PR et al. AAPM TG-51. Med. Phys. 1999;26(9):1847-1870.  |  "
        "Muir BR et al. Report 374. Med. Phys. 2022;49(9):6739-6764.  |  "
        "Muir BR et al. Report 385. Med. Phys. 2024;51:5840-5857.  |  "
        "Generated by Veritas TG-51",
        S["footer"],
    ))

    doc.build(story)
