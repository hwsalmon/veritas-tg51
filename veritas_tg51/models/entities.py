"""
SQLAlchemy ORM models for Veritas TG-51.

Entity hierarchy:
  Center → Linac → BeamEnergy
  Center → Equipment (IonChamber, Electrometer, Thermometer, Barometer)
  BeamEnergy + Equipment → CalibrationSession → CalibrationResult
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Facility hierarchy
# ---------------------------------------------------------------------------

class Center(Base):
    __tablename__ = "centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    institution: Mapped[Optional[str]] = mapped_column(String(200))
    physicist: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    linacs: Mapped[list[Linac]] = relationship(
        "Linac", back_populates="center", cascade="all, delete-orphan"
    )
    ion_chambers: Mapped[list[IonChamber]] = relationship(
        "IonChamber", back_populates="center", cascade="all, delete-orphan"
    )
    electrometers: Mapped[list[Electrometer]] = relationship(
        "Electrometer", back_populates="center", cascade="all, delete-orphan"
    )
    thermometers: Mapped[list[Thermometer]] = relationship(
        "Thermometer", back_populates="center", cascade="all, delete-orphan"
    )
    barometers: Mapped[list[Barometer]] = relationship(
        "Barometer", back_populates="center", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Center id={self.id} name={self.name!r}>"


class Linac(Base):
    __tablename__ = "linacs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id"), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "VersaHD"
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    center: Mapped[Center] = relationship("Center", back_populates="linacs")
    beam_energies: Mapped[list[BeamEnergy]] = relationship(
        "BeamEnergy", back_populates="linac", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Linac id={self.id} name={self.name!r} SN={self.serial_number!r}>"


class BeamEnergy(Base):
    """A specific beam on a linac (e.g. 6MV, 10MV FFF, 6MeV electrons)."""

    __tablename__ = "beam_energies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    linac_id: Mapped[int] = mapped_column(ForeignKey("linacs.id"), nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)  # "photon" | "electron"
    energy_mv: Mapped[float] = mapped_column(Float, nullable=False)    # MV or MeV nominal
    is_fff: Mapped[bool] = mapped_column(Boolean, default=False)       # Flattening-filter-free
    label: Mapped[str] = mapped_column(String(50), nullable=False)     # "6 MV", "10 MV FFF", "9 MeV"
    # Default calibration values (auto-populate new sessions)
    pdd_shift_pct: Mapped[Optional[float]] = mapped_column(Float)      # %dd shift (photons)
    clinical_pdd_pct: Mapped[Optional[float]] = mapped_column(Float)   # clinical %dd at ref depth (photons, for d_max)
    i50_cm: Mapped[Optional[float]] = mapped_column(Float)             # I_50 depth cm (electrons)

    linac: Mapped[Linac] = relationship("Linac", back_populates="beam_energies")
    calibration_sessions: Mapped[list[CalibrationSession]] = relationship(
        "CalibrationSession", back_populates="beam_energy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BeamEnergy id={self.id} label={self.label!r} fff={self.is_fff}>"


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class IonChamber(Base):
    __tablename__ = "ion_chambers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id"), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Exradin A12"
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    # Physical properties
    r_cav_cm: Mapped[float] = mapped_column(Float, nullable=False)      # cavity radius, cm
    wall_material: Mapped[str] = mapped_column(String(50))              # e.g. "C-552"
    wall_thickness_gcm2: Mapped[Optional[float]] = mapped_column(Float) # g/cm²
    volume_cc: Mapped[Optional[float]] = mapped_column(Float)           # cm³
    is_waterproof: Mapped[bool] = mapped_column(Boolean, default=True)
    # Calibration
    n_dw_gy_per_c: Mapped[float] = mapped_column(Float, nullable=False) # N_D,w^60Co, Gy/C
    calibration_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime)
    calibration_lab: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    center: Mapped[Center] = relationship("Center", back_populates="ion_chambers")

    def __repr__(self) -> str:
        return f"<IonChamber model={self.model!r} SN={self.serial_number!r}>"


class Electrometer(Base):
    __tablename__ = "electrometers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id"), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    # P_elec = 1.000 if calibrated as unit with chamber; otherwise enter factor
    p_elec: Mapped[float] = mapped_column(Float, default=1.000)
    calibration_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime)
    calibration_lab: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    center: Mapped[Center] = relationship("Center", back_populates="electrometers")


class Thermometer(Base):
    __tablename__ = "thermometers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id"), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    correction_offset_c: Mapped[float] = mapped_column(Float, default=0.0)  # additive correction, °C
    calibration_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    center: Mapped[Center] = relationship("Center", back_populates="thermometers")


class Barometer(Base):
    __tablename__ = "barometers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id"), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    serial_number: Mapped[Optional[str]] = mapped_column(String(100))
    correction_offset_kpa: Mapped[float] = mapped_column(Float, default=0.0)  # additive, kPa
    calibration_date: Mapped[Optional[datetime.date]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    center: Mapped[Center] = relationship("Center", back_populates="barometers")


# ---------------------------------------------------------------------------
# Calibration session and results
# ---------------------------------------------------------------------------

class CalibrationSession(Base):
    """
    One TG-51 calibration measurement session for a specific beam energy.
    Stores all raw inputs and intermediate correction factors.
    """

    __tablename__ = "calibration_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beam_energy_id: Mapped[int] = mapped_column(ForeignKey("beam_energies.id"), nullable=False)
    ion_chamber_id: Mapped[int] = mapped_column(ForeignKey("ion_chambers.id"), nullable=False)
    electrometer_id: Mapped[int] = mapped_column(ForeignKey("electrometers.id"), nullable=False)
    thermometer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("thermometers.id"))
    barometer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("barometers.id"))

    session_date: Mapped[datetime.date] = mapped_column(DateTime, nullable=False)
    physicist: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(String(1000))

    # --- Setup ---
    setup_type: Mapped[str] = mapped_column(String(10), default="SAD")  # "SSD" | "SAD"
    ssd_or_sad_cm: Mapped[float] = mapped_column(Float, default=100.0)
    monitor_units: Mapped[float] = mapped_column(Float, default=200.0)

    # --- Environmental ---
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False)

    # --- Polarity readings (raw, nC or rdg) ---
    m_raw_pos: Mapped[float] = mapped_column(Float, nullable=False)  # M+ (positive bias)
    m_raw_neg: Mapped[float] = mapped_column(Float, nullable=False)  # M- (negative bias)
    m_raw_ref: Mapped[str] = mapped_column(String(10), default="pos")  # which polarity matches calibration

    # --- Ion recombination (two-voltage technique) ---
    v_high: Mapped[float] = mapped_column(Float, nullable=False)   # V_H, V
    v_low: Mapped[float] = mapped_column(Float, nullable=False)    # V_L, V
    m_raw_high: Mapped[float] = mapped_column(Float, nullable=False)  # M at V_H
    m_raw_low: Mapped[float] = mapped_column(Float, nullable=False)   # M at V_L

    # --- Beam quality (photon) ---
    # %dd(10) measurement data
    pdd10_measured: Mapped[Optional[float]] = mapped_column(Float)   # %dd(10) open beam
    pdd10_pb_measured: Mapped[Optional[float]] = mapped_column(Float) # %dd(10)_Pb with lead foil
    pb_foil_distance_cm: Mapped[Optional[float]] = mapped_column(Float)  # 50 or 30 cm
    pdd10x_method: Mapped[Optional[str]] = mapped_column(String(20))  # "open"|"foil50"|"foil30"|"interim"

    # --- Beam quality (electron) ---
    i50_cm: Mapped[Optional[float]] = mapped_column(Float)  # I_50 from depth-ionization curve

    # --- FFF ---
    p_rp: Mapped[float] = mapped_column(Float, default=1.000)  # radial profile correction

    # Relationships
    beam_energy: Mapped[BeamEnergy] = relationship("BeamEnergy", back_populates="calibration_sessions")
    ion_chamber: Mapped[IonChamber] = relationship("IonChamber")
    electrometer: Mapped[Electrometer] = relationship("Electrometer")
    thermometer: Mapped[Optional[Thermometer]] = relationship("Thermometer")
    barometer: Mapped[Optional[Barometer]] = relationship("Barometer")
    result: Mapped[Optional[CalibrationResult]] = relationship(
        "CalibrationResult", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CalibrationSession id={self.id} date={self.session_date}>"


class CalibrationResult(Base):
    """
    Computed output of a TG-51 calibration — all intermediate factors stored for audit.
    """

    __tablename__ = "calibration_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("calibration_sessions.id"), nullable=False, unique=True
    )

    # Correction factors
    p_tp: Mapped[float] = mapped_column(Float)        # Temperature-pressure correction
    p_pol: Mapped[float] = mapped_column(Float)       # Polarity correction
    p_ion: Mapped[float] = mapped_column(Float)       # Ion recombination correction
    p_elec: Mapped[float] = mapped_column(Float)      # Electrometer calibration factor
    p_rp: Mapped[float] = mapped_column(Float)        # Radial beam profile correction

    # Corrected reading
    m_corrected: Mapped[float] = mapped_column(Float)  # M = M_raw * P_ion * P_TP * P_elec * P_pol * P_rp

    # Beam quality
    pdd10x: Mapped[Optional[float]] = mapped_column(Float)    # %dd(10)_x (photons)
    r50_cm: Mapped[Optional[float]] = mapped_column(Float)    # R_50 (electrons)
    d_ref_cm: Mapped[Optional[float]] = mapped_column(Float)  # reference depth

    # Quality conversion factor
    k_q: Mapped[float] = mapped_column(Float)          # k_Q (photon) or k_Q composite (electron)
    k_qecal: Mapped[Optional[float]] = mapped_column(Float)   # electron: k_Qecal
    k_q_prime: Mapped[Optional[float]] = mapped_column(Float) # electron: k'_Q

    # N_D,w from chamber record at time of session
    n_dw_gy_per_c: Mapped[float] = mapped_column(Float)

    # Dose results
    dose_ref_gy: Mapped[float] = mapped_column(Float)         # D_w at reference depth, Gy/MU
    dose_ref_cgy_per_mu: Mapped[float] = mapped_column(Float) # cGy/MU at reference depth
    dose_dmax_cgy_per_mu: Mapped[Optional[float]] = mapped_column(Float)  # cGy/MU at d_max

    # Clinical PDD/TMR used to convert ref→dmax
    clinical_pdd_or_tmr: Mapped[Optional[float]] = mapped_column(Float)

    computed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    session: Mapped[CalibrationSession] = relationship(
        "CalibrationSession", back_populates="result"
    )

    def __repr__(self) -> str:
        return (
            f"<CalibrationResult session={self.session_id} "
            f"dose={self.dose_ref_cgy_per_mu:.4f} cGy/MU>"
        )


# ---------------------------------------------------------------------------
# Flat calibration record — self-contained, no FK dependencies
# Used for History page without requiring full equipment hierarchy
# ---------------------------------------------------------------------------

class CalibrationRecord(Base):
    """
    Flat record of a completed TG-51 calibration.
    Self-contained: all inputs and results stored inline.
    No FK dependencies — can be written without the full equipment hierarchy.
    """

    __tablename__ = "calibration_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    modality: Mapped[str] = mapped_column(String(10), nullable=False)   # "photon" | "electron"
    physicist: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(String(1000))

    # Equipment (denormalized)
    chamber_model: Mapped[str] = mapped_column(String(100), nullable=False)
    chamber_type: Mapped[Optional[str]] = mapped_column(String(20))     # "cylindrical" | "parallel_plate"
    n_dw_gy_per_c: Mapped[float] = mapped_column(Float, nullable=False)

    # Environment
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_kpa: Mapped[float] = mapped_column(Float, nullable=False)

    # Beam
    energy_nominal: Mapped[float] = mapped_column(Float, nullable=False)  # MV or MeV
    is_fff: Mapped[bool] = mapped_column(Boolean, default=False)

    # Beam quality
    pdd10x: Mapped[Optional[float]] = mapped_column(Float)     # photon %dd(10)_x
    pdd10x_method: Mapped[Optional[str]] = mapped_column(String(30))
    r50_cm: Mapped[Optional[float]] = mapped_column(Float)     # electron R_50
    d_ref_cm: Mapped[Optional[float]] = mapped_column(Float)   # electron d_ref

    # Corrections
    p_tp: Mapped[float] = mapped_column(Float, nullable=False)
    p_pol: Mapped[float] = mapped_column(Float, nullable=False)
    p_ion: Mapped[float] = mapped_column(Float, nullable=False)
    p_elec: Mapped[float] = mapped_column(Float, nullable=False)
    p_rp: Mapped[float] = mapped_column(Float, default=1.0)
    p_leak: Mapped[float] = mapped_column(Float, default=1.0)

    # k_Q
    k_q: Mapped[float] = mapped_column(Float, nullable=False)
    k_qecal: Mapped[Optional[float]] = mapped_column(Float)    # electron
    k_q_prime: Mapped[Optional[float]] = mapped_column(Float)  # electron

    # Corrected reading and dose
    m_corrected: Mapped[float] = mapped_column(Float, nullable=False)
    monitor_units: Mapped[float] = mapped_column(Float, nullable=False)
    dose_ref_cgy_per_mu: Mapped[float] = mapped_column(Float, nullable=False)
    dose_dmax_cgy_per_mu: Mapped[Optional[float]] = mapped_column(Float)

    # Warnings (JSON list)
    warnings_json: Mapped[Optional[str]] = mapped_column(String(2000))

    def __repr__(self) -> str:
        return (
            f"<CalibrationRecord id={self.id} {self.modality} "
            f"{self.energy_nominal} dose={self.dose_ref_cgy_per_mu:.4f} cGy/MU>"
        )


# ---------------------------------------------------------------------------
# Worksheet session — full multi-beam session with auto-save support
# ---------------------------------------------------------------------------

class WorksheetSession(Base):
    """
    Complete multi-beam calibration session.
    All session setup metadata and every worksheet field for every beam tab
    are stored as JSON so the session can be fully restored at any time.
    """

    __tablename__ = "worksheet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    # Session metadata (denormalized from SessionSetup so recovery works
    # even if equipment records are later edited/deleted)
    center_id: Mapped[Optional[int]] = mapped_column(Integer)
    center_name: Mapped[str] = mapped_column(String(200), nullable=False)
    linac_id: Mapped[Optional[int]] = mapped_column(Integer)
    linac_name: Mapped[str] = mapped_column(String(100), nullable=False)
    linac_model: Mapped[str] = mapped_column(String(200), default="")
    chamber_id: Mapped[Optional[int]] = mapped_column(Integer)
    chamber_model: Mapped[str] = mapped_column(String(100), nullable=False)
    chamber_sn: Mapped[str] = mapped_column(String(100), default="")
    n_dw_gy_per_c: Mapped[float] = mapped_column(Float, nullable=False)
    r_cav_cm: Mapped[float] = mapped_column(Float, default=0.0)
    electrometer_id: Mapped[Optional[int]] = mapped_column(Integer)
    electrometer_model: Mapped[str] = mapped_column(String(100), default="")
    electrometer_sn: Mapped[str] = mapped_column(String(100), default="")
    p_elec: Mapped[float] = mapped_column(Float, default=1.000)
    physicist: Mapped[Optional[str]] = mapped_column(String(200))
    session_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    # All beam worksheet field states: JSON dict keyed by str(beam_id)
    # Each value is a field-state dict (see EnergyTab.get_state / restore_state)
    beam_states_json: Mapped[str] = mapped_column(String(65536), default="{}")

    # Summary counters (convenience for display)
    beams_total: Mapped[int] = mapped_column(Integer, default=0)
    beams_calculated: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return (
            f"<WorksheetSession id={self.id} linac={self.linac_name!r} "
            f"date={self.session_date} {self.beams_calculated}/{self.beams_total} beams>"
        )


# ---------------------------------------------------------------------------
# Database initialisation helper
# ---------------------------------------------------------------------------

def get_engine(db_path: str = "data/veritas.db"):
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(db_path: str = "data/veritas.db"):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    # Migrate: add new columns to existing tables if they don't exist yet
    _migrate(engine)
    return engine


def _migrate(engine):
    """Add columns introduced after initial release without dropping data."""
    migrations = {
        "beam_energies": [
            ("pdd_shift_pct",    "FLOAT"),
            ("clinical_pdd_pct", "FLOAT"),
            ("i50_cm",           "FLOAT"),
        ],
        "ion_chambers": [
            ("calibration_date", "DATETIME"),
            ("calibration_lab",  "VARCHAR(200)"),
        ],
        "electrometers": [
            ("calibration_date", "DATETIME"),
            ("calibration_lab",  "VARCHAR(200)"),
        ],
        "thermometers": [
            ("calibration_date", "DATETIME"),
        ],
        "barometers": [
            ("calibration_date", "DATETIME"),
        ],
    }
    with engine.connect() as conn:
        for table, cols in migrations.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            for col, typedef in cols:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}"))
        conn.commit()


def get_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
