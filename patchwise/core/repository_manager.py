from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, or_, select

from patchwise.core.database import get_session_factory, init_db, resolve_db_path
from patchwise.core.models import ActivityLog, Finding, FindingEvidence, Project, RemediationRecord, ScanRecord


def validate_repository_path(path: str | Path) -> Path:
    raw = str(path)
    if not raw or raw.strip() == "":
        raise ValueError("Repository path cannot be empty")

    candidate = Path(raw).expanduser()
    if ".." in candidate.parts:
        raise ValueError("Unsafe path traversal reference detected")

    resolved = candidate.resolve(strict=False)
    if not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")

    if any(part in {".git", "node_modules", ".venv", "venv", "dist", "build"} for part in resolved.parts):
        raise ValueError("Unsupported or unsafe repository path")
    return resolved


def detect_manifests(path: str | Path) -> list[str]:
    directory = validate_repository_path(path)
    if directory.is_file():
        return [directory.name]

    results: list[str] = []
    for manifest in ["requirements.txt", "pyproject.toml", "package.json", "package-lock.json"]:
        if (directory / manifest).exists():
            results.append(manifest)

    python_files = 0
    for child in directory.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "node_modules", "dist", "build"} for part in child.parts):
            continue
        python_files += 1
        if python_files == 1:
            results.append(str(child.relative_to(directory)))
            break
    return results


def is_git_repo(path: str | Path) -> bool:
    location = validate_repository_path(path)
    return (location / ".git").exists() or (location / ".git").is_dir()


def detect_language(path: str | Path) -> str:
    directory = validate_repository_path(path)
    if (directory / "package.json").exists():
        return "javascript"
    if (directory / "requirements.txt").exists() or (directory / "pyproject.toml").exists():
        return "python"
    if any(directory.rglob("*.py")):
        return "python"
    return "unknown"


def register_project(path: str | Path, db_path: str | None = None) -> dict:
    location = validate_repository_path(path)
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    session_factory = get_session_factory(db_path)
    with session_factory() as session:
        existing = session.execute(select(Project).where(Project.path == str(location))).scalar_one_or_none()
        if existing:
            existing.is_git = is_git_repo(location)
            existing.language = detect_language(location)
            session.commit()
            session.refresh(existing)
            return {"id": existing.id, "name": existing.name, "path": existing.path, "is_git": existing.is_git, "language": existing.language}

        project = Project(
            name=location.name,
            path=str(location),
            is_git=is_git_repo(location),
            language=detect_language(location),
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return {"id": project.id, "name": project.name, "path": project.path, "is_git": project.is_git, "language": project.language}


def list_projects(db_path: str | None = None) -> list[Project]:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        return list(session.execute(select(Project).order_by(Project.id.desc())).scalars().all())


def get_project_by_id(project_id: int, db_path: str | None = None) -> Project | None:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        return session.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()


def remove_project(project_id: int, db_path: str | None = None) -> None:
    """Delete a project's stored scanner records atomically; leave source files intact."""
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        project = session.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if project is None:
            return
        finding_ids = select(Finding.id).where(Finding.project_id == project_id)
        # Delete dependents first, including logs linked only through a finding.
        # Explicit deletes work with existing SQLite files without schema migration
        # and avoid the ORM trying to null non-nullable project foreign keys.
        session.execute(delete(ActivityLog).where(or_(
            ActivityLog.project_id == project_id,
            ActivityLog.finding_id.in_(finding_ids),
        )))
        session.execute(delete(FindingEvidence).where(FindingEvidence.finding_id.in_(finding_ids)))
        session.execute(delete(RemediationRecord).where(RemediationRecord.finding_id.in_(finding_ids)))
        session.execute(delete(ScanRecord).where(ScanRecord.project_id == project_id))
        session.execute(delete(Finding).where(Finding.project_id == project_id))
        session.execute(delete(Project).where(Project.id == project_id))
        session.commit()


def save_scan_record(project_id: int, status: str, summary: str, db_path: str | None = None) -> ScanRecord:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        project = session.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
        if project is not None:
            project.last_scanned_at = datetime.now(timezone.utc)
        record = ScanRecord(project_id=project_id, status=status, summary=summary)
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


def list_scan_records(project_id: int | None = None, db_path: str | None = None) -> list[ScanRecord]:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        query = select(ScanRecord)
        if project_id is not None:
            query = query.where(ScanRecord.project_id == project_id)
        query = query.order_by(ScanRecord.id.desc())
        return list(session.execute(query).scalars().all())


def save_findings(project_id: int, findings: list[dict], db_path: str | None = None) -> list[Finding]:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    created: list[Finding] = []
    with get_session_factory(db_path)() as session:
        for finding in findings:
            record = Finding(
                project_id=project_id,
                title=finding.get("title") or "Unnamed finding",
                description=finding.get("description") or "",
                severity=(finding.get("severity") or "unknown").lower(),
                status="open",
                scanner=finding.get("scanner") or "unknown",
                source=finding.get("source") or "",
                cve=finding.get("cve"),
                osv=finding.get("osv"),
                cvss_score=finding.get("cvss_score"),
                package_name=finding.get("package") or finding.get("package_name"),
                package_version=finding.get("version") or finding.get("package_version"),
                fixed_version=finding.get("fixed_version"),
                direct_dependency=bool(finding.get("direct_dependency")),
                fix_available=bool(finding.get("fix_available")),
                is_kev=bool(finding.get("is_kev")),
            )
            session.add(record)
            created.append(record)
        session.commit()
        for record in created:
            session.refresh(record)
    return created


def list_findings(project_id: int | None = None, db_path: str | None = None) -> list[Finding]:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        query = select(Finding)
        if project_id is not None:
            query = query.where(Finding.project_id == project_id)
        query = query.order_by(Finding.id.desc())
        return list(session.execute(query).scalars().all())


def update_finding_status(finding_id: int, status: str, db_path: str | None = None) -> Finding | None:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        finding = session.execute(select(Finding).where(Finding.id == finding_id)).scalar_one_or_none()
        if finding is None:
            return None
        finding.status = status
        session.commit()
        session.refresh(finding)
        return finding


def log_activity(project_id: int | None, finding_id: int | None, action: str, details: str, db_path: str | None = None) -> ActivityLog:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        log = ActivityLog(project_id=project_id, finding_id=finding_id, action=action, details=details)
        session.add(log)
        session.commit()
        session.refresh(log)
        return log


def get_activity_logs(project_id: int | None = None, finding_id: int | None = None, db_path: str | None = None) -> list[ActivityLog]:
    db_path = resolve_db_path(db_path)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        query = select(ActivityLog)
        if project_id is not None:
            query = query.where(ActivityLog.project_id == project_id)
        if finding_id is not None:
            query = query.where(ActivityLog.finding_id == finding_id)
        query = query.order_by(ActivityLog.id.desc())
        return list(session.execute(query).scalars().all())
