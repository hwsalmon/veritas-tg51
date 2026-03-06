"""
db.py — Shared database engine singleton and calibration save helpers.

Usage:
    from veritas_tg51.models.db import set_engine, save_photon_record, save_electron_record
"""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

_engine: Optional[Engine] = None
_Session = None


def set_engine(engine: Engine) -> None:
    """Store the application-wide SQLAlchemy engine (called once at startup)."""
    global _engine, _Session
    _engine = engine
    _Session = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    if _Session is None:
        raise RuntimeError("Database not initialized. Call set_engine() first.")
    return _Session()


def is_ready() -> bool:
    return _engine is not None


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_photon_record(inp, result, physicist: str = "", notes: str = "") -> int:
    """
    Persist a photon calibration result as a CalibrationRecord.

    Parameters
    ----------
    inp : PhotonCalibrationInput
    result : PhotonCalibrationResult
    physicist : str  (optional, free-text name)
    notes : str      (optional)

    Returns
    -------
    int  — id of the new record
    """
    from .entities import CalibrationRecord

    session = get_session()
    try:
        rec = CalibrationRecord(
            modality="photon",
            physicist=physicist or None,
            notes=notes or None,
            chamber_model=inp.chamber_model,
            chamber_type="cylindrical",
            n_dw_gy_per_c=inp.n_dw_gy_per_c,
            temperature_c=inp.temperature_c,
            pressure_kpa=inp.pressure_kpa,
            energy_nominal=inp.energy_mv,
            is_fff=inp.is_fff,
            pdd10x=result.pdd10x,
            pdd10x_method=result.pdd10x_method,
            p_tp=result.p_tp,
            p_pol=result.p_pol,
            p_ion=result.p_ion,
            p_elec=result.p_elec,
            p_rp=result.p_rp,
            p_leak=result.p_leak,
            k_q=result.k_q,
            m_corrected=result.m_corrected,
            monitor_units=inp.monitor_units,
            dose_ref_cgy_per_mu=result.dose_10cm_cgy_per_mu,
            dose_dmax_cgy_per_mu=result.dose_dmax_cgy_per_mu,
            warnings_json=json.dumps(result.warnings),
        )
        session.add(rec)
        session.commit()
        return rec.id
    finally:
        session.close()


def save_electron_record(inp, result, physicist: str = "", notes: str = "") -> int:
    """
    Persist an electron calibration result as a CalibrationRecord.

    Parameters
    ----------
    inp : ElectronCalibrationInput
    result : ElectronCalibrationResult
    physicist : str
    notes : str

    Returns
    -------
    int  — id of the new record
    """
    from .entities import CalibrationRecord

    session = get_session()
    try:
        rec = CalibrationRecord(
            modality="electron",
            physicist=physicist or None,
            notes=notes or None,
            chamber_model=inp.chamber_model,
            chamber_type=inp.chamber_type,
            n_dw_gy_per_c=inp.n_dw_gy_per_c,
            temperature_c=inp.temperature_c,
            pressure_kpa=inp.pressure_kpa,
            energy_nominal=inp.energy_mev,
            is_fff=False,
            r50_cm=result.r50_cm,
            d_ref_cm=result.d_ref_cm,
            p_tp=result.p_tp,
            p_pol=result.p_pol,
            p_ion=result.p_ion,
            p_elec=result.p_elec,
            p_leak=result.p_leak,
            k_q=result.k_q,
            k_qecal=result.k_qecal,
            k_q_prime=result.k_q_prime,
            m_corrected=result.m_corrected,
            monitor_units=inp.monitor_units,
            dose_ref_cgy_per_mu=result.dose_dref_cgy_per_mu,
            dose_dmax_cgy_per_mu=result.dose_dmax_cgy_per_mu,
            warnings_json=json.dumps(result.warnings),
        )
        session.add(rec)
        session.commit()
        return rec.id
    finally:
        session.close()


def fetch_all_records(
    modality: Optional[str] = None,
    limit: int = 500,
) -> list:
    """
    Return CalibrationRecord rows, newest first.

    Parameters
    ----------
    modality : "photon" | "electron" | None (all)
    limit : max rows to return
    """
    from .entities import CalibrationRecord
    from sqlalchemy import select, desc

    session = get_session()
    try:
        stmt = select(CalibrationRecord).order_by(desc(CalibrationRecord.recorded_at))
        if modality:
            stmt = stmt.where(CalibrationRecord.modality == modality)
        stmt = stmt.limit(limit)
        return session.scalars(stmt).all()
    finally:
        session.close()


def delete_record(record_id: int) -> None:
    """Delete a CalibrationRecord by id."""
    from .entities import CalibrationRecord

    session = get_session()
    try:
        rec = session.get(CalibrationRecord, record_id)
        if rec:
            session.delete(rec)
            session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# WorksheetSession helpers
# ---------------------------------------------------------------------------

def upsert_worksheet_session(
    ws_id: Optional[int],
    setup,              # SessionSetup dataclass
    beam_states: dict,  # {str(beam_id): field_state_dict}
    beams_total: int,
    beams_calculated: int,
) -> int:
    """
    Create or update a WorksheetSession row.

    Parameters
    ----------
    ws_id : existing id to update, or None to create a new row
    setup : SessionSetup dataclass
    beam_states : dict mapping str(beam_id) → field state dict
    beams_total / beams_calculated : counts for display

    Returns
    -------
    int — id of the saved WorksheetSession
    """
    import datetime
    from .entities import WorksheetSession

    session = get_session()
    try:
        if ws_id is not None:
            ws = session.get(WorksheetSession, ws_id)
        else:
            ws = None

        now = datetime.datetime.utcnow()

        # Convert session_date (date or str) to datetime for SQLite compatibility
        sd = setup.session_date
        if isinstance(sd, str):
            import datetime as _dt
            sd = _dt.datetime.strptime(sd, "%Y-%m-%d")
        elif hasattr(sd, 'year') and not isinstance(sd, datetime.datetime):
            sd = datetime.datetime(sd.year, sd.month, sd.day)

        if ws is None:
            ws = WorksheetSession(
                created_at=now,
                center_id=setup.center_id,
                center_name=setup.center_name,
                linac_id=setup.linac_id,
                linac_name=setup.linac_name,
                linac_model=setup.linac_model,
                chamber_id=setup.chamber_id,
                chamber_model=setup.chamber_model,
                chamber_sn=setup.chamber_sn,
                n_dw_gy_per_c=setup.n_dw_gy_per_c,
                r_cav_cm=setup.r_cav_cm,
                electrometer_id=setup.electrometer_id,
                electrometer_model=setup.electrometer_model,
                electrometer_sn=setup.electrometer_sn,
                p_elec=setup.p_elec,
                physicist=setup.physicist or None,
                session_date=sd,
            )
            session.add(ws)
        else:
            # Update mutable fields
            ws.physicist = setup.physicist or None

        ws.updated_at = now
        ws.beam_states_json = json.dumps(beam_states)
        ws.beams_total = beams_total
        ws.beams_calculated = beams_calculated

        session.commit()
        return ws.id
    finally:
        session.close()


def fetch_worksheet_sessions(limit: int = 200) -> list:
    """Return WorksheetSession rows, newest first."""
    from .entities import WorksheetSession
    from sqlalchemy import select, desc

    session = get_session()
    try:
        stmt = (
            select(WorksheetSession)
            .order_by(desc(WorksheetSession.updated_at))
            .limit(limit)
        )
        return session.scalars(stmt).all()
    finally:
        session.close()


def load_worksheet_session(ws_id: int):
    """Return a single WorksheetSession by id, or None."""
    from .entities import WorksheetSession

    session = get_session()
    try:
        return session.get(WorksheetSession, ws_id)
    finally:
        session.close()


def delete_worksheet_session(ws_id: int) -> None:
    """Delete a WorksheetSession by id."""
    from .entities import WorksheetSession

    session = get_session()
    try:
        ws = session.get(WorksheetSession, ws_id)
        if ws:
            session.delete(ws)
            session.commit()
    finally:
        session.close()
