# Veritas TG-51 — Project Context for Claude

## Role
Act as an expert Medical Physicist and Senior Python Software Engineer specializing in radiotherapy applications.

## Project Description
A Python desktop application (PySide6) for AAPM TG-51 absolute dosimetry calibrations on linear accelerators. Replaces an Excel-based workflow. Named "Veritas TG-51."

---

## Reference Documents (Data/)
| File | Purpose |
|---|---|
| `Medical Physics - 1999 - Almond - AAPM's TG-51 protocol...pdf` | Primary protocol: photon + electron formalism, worksheets A–D, kQ tables |
| `Medical Physics - 2022 - Muir - AAPM WGTG51 Report 374...pdf` | Practical guidance: EPOM shifts, FFF corrections, P_rp, equipment specs |
| `Medical Physics - 2024 - Muir - AAPM WGTG51 Report 385...pdf` | **Electron Addendum** (WGTG51-e): updated kQ formalism, MC-based kQecal/k'Q data, no P_gr needed |
| `1180-30-Exradin_BR.pdf` | Standard Imaging Exradin A12 specs |
| `TG 51 VersaHD SN153991 - 09-14-2025.xlsx` | User's current Excel workflow (baseline reference) |

---

## Clinical Context
- **Institution machine**: Elekta VersaHD, SN 153991
- **Photon energies**: 6 MV, 10 MV, 15 MV, 6 MV FFF, 10 MV FFF
- **Electron energies**: 6 MeV, 9 MeV, 12 MeV, 15 MeV
- **Primary chamber**: Standard Imaging Exradin A12 (Farmer-type)
- **Electrometer**: Standard Imaging MAX-ELITE (assumed)

---

## Exradin A12 Key Specifications
| Parameter | Value |
|---|---|
| Collecting volume | 0.64 cm³ |
| Shell/wall material | C-552 air-equivalent plastic |
| Wall thickness | 0.5 mm (0.088 g/cm²) |
| Cavity radius (r_cav) | 0.305 cm |
| Collector length | 21.6 mm |
| Recommended bias | 300 V |
| Waterproof | Yes (inherent) |
| EPOM shift (photons, Δz) | 1.4 mm (MC, Report 374 Table 1) |
| EPOM shift (electrons, Δz) | 1.1 mm (MC, Report 374 Table 2 / 2024 Addendum Table 2) |

---

## Physics Protocol Summary

### Core Equation (all modalities)
```
D_w^Q = M · k_Q · N_D,w^60Co       [TG-51 Eq. 3]
```

### Corrected Reading M
```
M = M_raw · P_ion · P_TP · P_elec · P_pol [· P_leak · P_rp]   [TG-51 Eq. 8; P_leak/P_rp from WGTG51-X/Report 374]
```

### Environmental Correction P_TP
```
P_TP = ((273.2 + T) / 295.2) × (101.33 / P)    [TG-51 Eq. 10]
```
T in °C (water temperature), P in kPa.

### Polarity Correction P_pol
```
P_pol = |(M+_raw - M-_raw) / (2 · M_raw)|       [TG-51 Eq. 9]
```

### Ion Recombination P_ion
- **60Co / continuous beam**: Eq. 11 (two-voltage, nonlinear)
- **Pulsed / pulsed-swept beams** (all linac beams): Eq. 12 (linear two-voltage)
```
P_ion(V_H) = (1 - V_H/V_L) / (M^H_raw/M^L_raw - V_H/V_L)    [TG-51 Eq. 12]
```
- FFF beams: P_ion can be up to 2% — Jaffé plot commissioning required (Report 374 §4.4.4)
- If P_ion > 1.05, use a different chamber

---

## Photon Protocol (TG-51 1999 + WGTG51-X 2014 Addendum + Report 374 2022)

### Beam Quality Specifier: %dd(10)_x
- **< 10 MV**: `%dd(10)_x = %dd(10)` (open beam, no lead foil needed)
- **≥ 10 MV**: Measure `%dd(10)_Pb` with 1 mm Pb foil at 50±5 cm or 30±1 cm from phantom surface
  - 50 cm: `%dd(10)_x = [0.8905 + 0.00150·%dd(10)_Pb] · %dd(10)_Pb`  [if %dd(10)_Pb ≥ 73%] (Eq.13)
  - 30 cm: `%dd(10)_x = [0.8116 + 0.00264·%dd(10)_Pb] · %dd(10)_Pb`  [if %dd(10)_Pb ≥ 71%] (Eq.14)
  - Interim (no foil, ≥45 cm clearance): `%dd(10)_x = 1.267·%dd(10) - 20.0` [75% < %dd(10) ≤ 89%] (Eq.15)
- **FFF beams**: ALWAYS use lead foil (Report 374 §3.3)

### Photon kQ
From TG-51 Table I (interpolate linearly in %dd(10)_x):

| %dd(10)_x | 58.0 | 63.0 | 66.0 | 71.0 | 81.0 | 93.0 |
|---|---|---|---|---|---|---|
| A12 k_Q | 1.000 | 0.999 | 0.996 | 0.990 | 0.972 | 0.948 |

### Reference Conditions (Photons)
- Reference depth: 10 cm (water equivalent)
- Field size: 10×10 cm² at phantom surface (SSD) or at detector (SAD)
- SSD or SAD ≈ 100 cm

### Dose at d_max (Photons)
- SSD setup: `D(d_max) = D(10cm) / (%dd(10)/100)`
- SAD setup: `D(d_max) = D(10cm) / TMR(10, 10×10)`

---

## Electron Protocol (2024 WGTG51-e Addendum — NEW FORMALISM)

### Key Change from 1999 TG-51
No measured gradient correction P_gr^Q needed for cylindrical chambers. k_Q factors now include gradient correction implicitly via Monte Carlo. Cylindrical chambers positioned with **central axis at d_ref** (no EPOM shift for the reference measurement itself).

### Updated Formalism
```
D_w^Q = M · k_Q · N_D,w^60Co = M · k'_Q · k_Qecal · N_D,w^60Co    [2024 Addendum Eq. 4]
```
Where:
- `k_Qecal`: photon-electron conversion factor (fixed for a given chamber model)
- `k'_Q`: beam-quality-dependent factor (function of R_50)

### Beam Quality Specifier: R_50
From depth-ionization scan (cylindrical chamber with EPOM shift Δz=1.1 mm for A12):
```
R_50 = 1.029 · I_50 - 0.06 cm    (for 2 ≤ I_50 ≤ 10 cm)    [Eq. 3 / TG-51 Eq. 16]
```
Note: EPOM shift applied ONLY for PDI scanning, NOT for reference dosimetry point measurement.

### Reference Depth
```
d_ref = 0.6 · R_50 - 0.1 cm    [TG-51 Eq. 18 / 2024 Eq. 2]
```

### Electron k_Q Factors for Exradin A12 (2024 Addendum)
- `k_Qecal = 0.907`  [Table 4, cylindrical, central axis at d_ref]
- `k'_Q(cyl) = a_0 + b_0 × R_50^c_0`  [Table 5, Eq. 7]
  - A12: a_0 = 0.965, b_0 = 0.119, c_0 = 0.607
  - Valid for 1.70 cm ≤ R_50 ≤ 8.70 cm (4–22 MeV)

### Reference Conditions (Electrons)
- Field size: ≥10×10 cm² on phantom surface (all energies per 2024 Addendum §7.1)
- SSD: 90–110 cm (consistent with TPS commissioning)

### Dose at d_max (Electrons)
```
D(d_max) = D(d_ref) / (%dd(d_ref) / 100)
```
Use clinical PDD curve (%dd as used clinically, not the depth-ionization curve).

---

## FFF Beam Special Considerations (Report 374 + WGTG51-X)
- Lead foil mandatory for beam quality determination
- P_rp correction required for non-uniform beam profile over chamber volume
- P_ion variation with depth up to 0.8% — measure at each setup, not assumed constant
- Jaffé plot commissioning required to verify two-voltage technique validity

---

## Planned Architecture
- **UI**: PySide6 (Qt6) desktop application
- **Data models**: Pydantic v2 + SQLAlchemy + SQLite
- **Physics engine**: `tg51_calculator.py` (pure Python, no UI dependencies)
- **Reports**: PDF output replicating TG-51 worksheets
- **Stack**: Python 3.11+, PySide6, SQLAlchemy 2.x, Pydantic v2, ReportLab

## Entity Hierarchy
```
Center → Machine (Linac) → BeamEnergy
Center → Equipment (IonChamber, Electrometer, Thermometer, Barometer)
BeamEnergy + Equipment → CalibrationSession → CalibrationResult
```

## File Structure (planned)
```
veritas_tg51/
├── main.py                  # PySide6 app entry point
├── models/
│   ├── entities.py          # SQLAlchemy ORM models
│   └── schemas.py           # Pydantic validation schemas
├── physics/
│   ├── tg51_photon.py       # Photon calculation engine
│   ├── tg51_electron.py     # Electron calculation engine (2024 Addendum)
│   ├── corrections.py       # P_TP, P_pol, P_ion, P_elec
│   └── chamber_data.py      # Tabulated kQ, kQecal, k'Q data per chamber
├── ui/
│   ├── worksheets/
│   │   ├── photon_worksheet.py
│   │   └── electron_worksheet.py
│   └── dialogs/             # Equipment, machine management dialogs
├── reports/
│   └── pdf_generator.py     # ReportLab PDF output
└── data/
    └── veritas.db           # SQLite database
```

## Coding Conventions
- All physics equations must include docstring references to the source document and equation number
- Units: SI throughout (Gy, C, kPa, °C, cm)
- Pressure input from user: kPa (provide mmHg conversion helper)
- kQ tables implemented as numpy interpolation; never hardcode single values
- All calculated intermediate values must be stored and accessible for audit/display
- Pydantic validators enforce physical plausibility (e.g., P_ion < 1.05, T in 15–35°C)
