from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from patchwise.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_git: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(String(64), default="unknown")
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    findings: Mapped[list["Finding"]] = relationship(back_populates="project")
    scans: Mapped[list["ScanRecord"]] = relationship(back_populates="project")


class ScanRecord(Base):
    __tablename__ = "scan_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    summary: Mapped[str] = mapped_column(Text, default="")
    scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="scans")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(32), default="unknown")
    status: Mapped[str] = mapped_column(String(32), default="open")
    scanner: Mapped[str] = mapped_column(String(64), default="unknown")
    source: Mapped[str] = mapped_column(String(255), default="")
    cve: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    osv: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    cvss_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    package_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    package_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    direct_dependency: Mapped[bool] = mapped_column(Boolean, default=False)
    fix_available: Mapped[bool] = mapped_column(Boolean, default=False)
    is_kev: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="findings")


class FindingEvidence(Base):
    __tablename__ = "finding_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), default="raw")
    evidence_value: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    finding_id: Mapped[Optional[int]] = mapped_column(ForeignKey("findings.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RemediationRecord(Base):
    __tablename__ = "remediation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), nullable=False)
    proposed_fix: Mapped[str] = mapped_column(Text, default="")
    verification_status: Mapped[str] = mapped_column(String(64), default="pending")
    justification: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertGroup(Base):
    __tablename__ = "alert_groups"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    rule_version: Mapped[str] = mapped_column(String(32), default="exact-evidence-v1")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("alert_groups.id"), index=True)
    normalized_json: Mapped[str] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text)


class AlertInvestigation(Base):
    __tablename__ = "alert_investigations"

    group_id: Mapped[str] = mapped_column(ForeignKey("alert_groups.id"), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    timeline_notes: Mapped[str] = mapped_column(Text, default="")
    supporting_evidence: Mapped[str] = mapped_column(Text, default="")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    missing_context: Mapped[str] = mapped_column(Text, default="")
    disposition: Mapped[str] = mapped_column(String(64), default="Investigating")
    escalation_rationale: Mapped[str] = mapped_column(Text, default="")
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertAIDraft(Base):
    __tablename__ = "alert_ai_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("alert_groups.id"), index=True)
    model: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))
    # Store only validated output or a fixed safe error, never provider bodies/credentials.
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TriageBenchmarkRun(Base):
    __tablename__ = "triage_benchmark_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant: Mapped[str] = mapped_column(String(255))
    case_id: Mapped[str] = mapped_column(String(255))
    workflow: Mapped[str] = mapped_column(String(32))
    case_set_sha256: Mapped[str] = mapped_column(String(64))
    elapsed_seconds: Mapped[float] = mapped_column(Float)
    evidence_missed: Mapped[int] = mapped_column(Integer)
    unsupported_claims: Mapped[int] = mapped_column(Integer)
    ai_mistake: Mapped[str] = mapped_column(Text, default="")
    analyst_correction: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
