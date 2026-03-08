# Veritas TG-51

**A desktop application for AAPM TG-51 absolute dosimetry calibrations on medical linear accelerators.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt6)-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## ⚠️ Important Notice — Authorised Use Only

> **This software is intended exclusively for use by qualified Medical Physicists and authorised radiation therapy personnel.**
>
> Veritas TG-51 performs calculations that directly inform the calibration of ionising radiation treatment machines. Incorrect use, data entry errors, or misinterpretation of results could lead to patient harm.
>
> - All calibration measurements must be performed by or under the direct supervision of a qualified Medical Physicist.
> - Results must be independently verified before clinical use.
> - This software does not replace professional judgement or institutional QA procedures.
> - The authors accept no liability for clinical decisions made using this application.
>
> **By using this software you confirm that you are a qualified Medical Physicist or are operating under the direct supervision of one.**

---

## Overview

Veritas TG-51 is a Python desktop application that replaces the traditional Excel-based TG-51 calibration workflow. It implements the full AAPM TG-51 dosimetry protocol for both photon and electron beams, including the 2022 (Report 374) and 2024 (Report 385 — WGTG51-e) addenda.

It is designed around the clinical workflow at a radiation therapy department, supporting multiple treatment machines, energies, and instrumentation sets with a complete audit trail and professional PDF reporting.

---

## Protocol References

| Document | Coverage |
|---|---|
| Almond et al. *Med. Phys.* 1999;26(9):1847–1870 | Primary TG-51 protocol — photon & electron formalism |
| McEwen et al. *Med. Phys.* 2014;41:041501 | TG-51 Addendum — beam quality for FFF beams |
| Muir et al. *Med. Phys.* 2022;49(9):6739–6764 | WGTG51 Report 374 — practical guidance, FFF, P_rp |
| Muir et al. *Med. Phys.* 2024;51:5840–5857 | WGTG51 Report 385 — updated electron k_Q formalism |

---

## Features

### Physics Engine

**Photon beams (TG-51 + 2014 Addendum + Report 374)**
- Beam quality determination: `%dd(10)_x` with open beam, lead foil (50 cm or 30 cm geometry), or interim equation
- FFF beam support: lead foil mandatory; `P_rp` correction applied
- `k_Q` from TG-51 Table I via linear interpolation in `%dd(10)_x`
- Full correction chain: `M = M_raw × P_ion × P_TP × P_elec × P_pol × P_rp × P_leak`
- `P_TP` temperature-pressure correction (Eq. 10)
- `P_pol` polarity correction (Eq. 9) — sign-convention correct for negative-bias operation
- `P_ion` two-voltage technique (Eq. 12) for pulsed/pulsed-swept beams
- Absorbed dose at 10 cm and at d_max (via clinical PDD/TMR)

**Electron beams (2024 WGTG51-e Addendum — Report 385)**
- Updated `k_Q = k'_Q × k_Qecal` formalism — no measured gradient correction required
- Beam quality from `R_50` (via `I_50` with EPOM correction for PDI scanning only)
- `d_ref = 0.6 × R_50 − 0.1 cm`
- Cylindrical chamber positioned with central axis at `d_ref` (no EPOM shift for reference dosimetry)
- `k_Qecal` and `k'_Q` power-law fit (Table 4/5, Report 385) for Exradin A12 and other cylindrical chambers
- Absorbed dose at `d_ref` and at `d_max` (via clinical PDD)

### Instrumentation Support
- **Ion chambers**: Farmer-type cylindrical chambers (e.g. Standard Imaging Exradin A12)
- **Electrometers**: any electrometer with known `P_elec` factor
- Calibration date tracking with automatic `>2 year` overdue warning

### Equipment Management
- Multi-institution, multi-machine database
- Institutions → Treatment Machines → Beam Energies hierarchy
- Ion chambers and electrometers are institution-independent — a single piece of equipment can be used across multiple sites without re-entry
- Beam-level default values: `%dd shift`, clinical `%dd`, `I_50`

### Calibration Session
- Per-energy worksheets with triplicate reading entry and automatic mean/SD
- Real-time calculation of all correction factors and absorbed dose
- Dose results at both `d_ref`/10 cm and `d_max` (prominent display)
- `% deviation` from 1.000 cGy/MU shown only at `d_max`
- Field size (photons) and applicator/cone (electrons) recorded
- Auto-save and session restore on startup
- Session history with resume, delete, and individual beam record export

### User Interface
- **Dark mode** — toggle via **☾/☼** button in the header bar or **View → Dark Mode** (`Ctrl+Shift+D`); preference persisted across sessions
- Sidebar navigation: Current Session · Session History · Configuration
- Clone treatment machine (copies all beam energies to the same or different institution)
- Beam energies managed inline within the machine configuration dialog

### PDF Reporting
- Professional two-page beam worksheets mirroring TG-51 Worksheets A and B
- Full session report: cover page + calibration summary + per-beam detail pages
- Cover page: institution, physicist, machine (with serial number), chamber and electrometer details, calibration dates
- Amber/red highlighting and overdue notice for instruments with calibration dates >2 years past
- Beam summary table: all beams, dose at d_max, % deviation, PASS/REVIEW status
- Section 8 (ion recombination) kept together — no page breaks mid-table
- Electronic signature block on every page

### Data & Audit
- SQLite database — single portable file, no server required
- All intermediate values (P_TP, P_pol, P_ion, k_Q, M_corrected, etc.) stored for audit
- Historical calibration records viewable and printable
- Automatic schema migration — database upgrades without data loss

---

## Supported Beam Energies

| Modality | Energies |
|---|---|
| Photon | 6 MV, 10 MV, 15 MV, 6 MV FFF, 10 MV FFF |
| Electron | 6 MeV, 9 MeV, 12 MeV, 15 MeV, 18 MeV, 20 MeV |

*Configurable per machine in the Equipment setup.*

---

## Installation

### Requirements
- Python 3.11 or later
- Linux, macOS, or Windows

### From source (development install)

```bash
git clone https://github.com/hwsalmon/veritas-tg51.git
cd veritas-tg51
pip install -e .
```

### Run

```bash
veritas-tg51
# or
python -m veritas_tg51.main
```

---

## Project Structure

```
veritas_tg51/
├── main.py                    # Application entry point
├── models/
│   ├── entities.py            # SQLAlchemy ORM models + schema migration
│   ├── db.py                  # Database session management, record storage
│   └── schemas.py             # Pydantic validation schemas
├── physics/
│   ├── tg51_photon.py         # Photon calibration engine (TG-51 + addenda)
│   ├── tg51_electron.py       # Electron calibration engine (2024 Report 385)
│   ├── corrections.py         # P_TP, P_pol, P_ion, P_elec, P_rp, P_leak
│   └── chamber_data.py        # Tabulated k_Q, k_Qecal, k'_Q data
├── ui/
│   ├── main_window.py         # Main application window and navigation
│   ├── pages/
│   │   ├── session_page.py    # Active calibration session with per-energy tabs
│   │   ├── equipment_page.py  # Equipment database management
│   │   └── records_page.py    # Historical calibration records
│   ├── worksheets/
│   │   ├── photon_worksheet.py   # Photon beam input form
│   │   └── electron_worksheet.py # Electron beam input form
│   └── dialogs/
│       └── new_session_dialog.py # Session setup wizard
├── reports/
│   └── pdf_generator.py       # ReportLab PDF report generation
└── data/
    ├── icon.png               # Application icon
    └── icon.ico               # Windows icon
data/
└── veritas.db                 # SQLite database (created on first run, not committed)
```

---

## First-Time Setup

1. Launch the application: `veritas-tg51`
2. Go to the **Equipment** tab
3. Add your **Institution** (e.g. "Franciscan Health Indianapolis") under the **Institutions** tab
4. Add your **Treatment Machine(s)** under the **Linacs** tab, linked to the institution
5. Add **Beam Energies** for each machine (modality, energy, default %dd/I_50 values)
6. Add your **Ion Chamber** (model, serial number, N_D,w calibration factor, r_cav, calibration date) — chambers are shared across all institutions
7. Add your **Electrometer** (model, serial number, P_elec, calibration date) — likewise institution-independent
8. Click **New Session** on the Session tab, select institution, machine, and instruments
9. Enter measurements on each beam energy tab and click **Calculate**
10. Use **Print Full Session Report** to generate the PDF

---

## Physics Notes

### Sign Convention (Polarity)
At −300 V bias, the collected charge is positive. At +300 V bias, charge is negative. The application labels fields accordingly: `M⁺ = reading at −300 V`, `M⁻ = reading at +300 V`. The denominator in P_pol uses the operating-voltage reading.

### Electron Formalism (2024 vs. 1999)
The 2024 WGTG51-e Addendum changes the electron k_Q formalism. For cylindrical chambers, no measured gradient correction (P_gr) is required — the gradient effect is incorporated into the Monte Carlo-derived k_Q factors. Results are typically 1–2% higher than the 1999 protocol. The EPOM shift (1.1 mm for Exradin A12) applies only when scanning the depth-ionisation curve to determine I_50, not for the reference dosimetry measurement.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors and contributors are not responsible for any errors in calibration data, clinical decisions, or patient outcomes resulting from the use of this software. All calibrations must be verified independently by a qualified Medical Physicist before clinical implementation.
