"""Continuity-pack assembly contracts and helpers."""

from dataclasses import dataclass
from pathlib import Path


CONTINUITY_PACK_SECTIONS = (
    "Potwierdzone",
    "Przypuszczenia",
    "Do weryfikacji",
    "Recommended next test",
)
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class ContinuityPack:
    """Decision-ready wrapper over an existing SourceTrace artifact."""

    title: str
    source_artifact_path: str
    confirmed: tuple[str, ...]
    assumptions: tuple[str, ...]
    to_verify: tuple[str, ...]
    recommended_next_test: tuple[str, ...]
    decision_snapshot: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContinuityPackRequest:
    """Input contract for creating a continuity-pack artifact view."""

    title: str
    source_artifact_path: str
    confirmed: tuple[str, ...]
    assumptions: tuple[str, ...]
    to_verify: tuple[str, ...]
    recommended_next_test: tuple[str, ...]
    decision_snapshot: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContinuityPackOutcome:
    """Output contract containing the assembled continuity-pack artifact."""

    request: ContinuityPackRequest
    continuity_pack: ContinuityPack


def render_continuity_pack_markdown(continuity_pack: ContinuityPack) -> str:
    """Render a continuity pack into a compact markdown handoff."""

    lines = [
        f"# {continuity_pack.title}",
        "",
        f"Source artifact: `{continuity_pack.source_artifact_path}`",
        "",
    ]
    sections = (
        (CONTINUITY_PACK_SECTIONS[0], continuity_pack.confirmed),
        (CONTINUITY_PACK_SECTIONS[1], continuity_pack.assumptions),
        (CONTINUITY_PACK_SECTIONS[2], continuity_pack.to_verify),
        (CONTINUITY_PACK_SECTIONS[3], continuity_pack.recommended_next_test),
    )
    for heading, items in sections:
        lines.append(f"## {heading}")
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- none")
        lines.append("")
    if continuity_pack.decision_snapshot:
        lines.append("## Decision snapshot")
        lines.extend(f"- {item}" for item in continuity_pack.decision_snapshot)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_continuity_pack_request_from_artifact(
    artifact_path: str,
    *,
    title: str | None = None,
) -> ContinuityPackRequest:
    """Auto-build a continuity-pack request from a markdown artifact with known headings."""

    resolved_path = _resolve_artifact_path(artifact_path)
    text = resolved_path.read_text(encoding="utf-8")
    sections = {
        heading: _extract_markdown_section_items(text, heading)
        for heading in CONTINUITY_PACK_SECTIONS
    }
    decision_snapshot = _extract_markdown_section_items(text, "Decision snapshot")
    derived_title = title.strip() if title and title.strip() else _derive_title(text, resolved_path)
    return ContinuityPackRequest(
        title=derived_title,
        source_artifact_path=str(resolved_path.relative_to(REPO_ROOT)),
        confirmed=sections[CONTINUITY_PACK_SECTIONS[0]],
        assumptions=sections[CONTINUITY_PACK_SECTIONS[1]],
        to_verify=sections[CONTINUITY_PACK_SECTIONS[2]],
        recommended_next_test=sections[CONTINUITY_PACK_SECTIONS[3]],
        decision_snapshot=decision_snapshot,
    )


def _resolve_artifact_path(artifact_path: str) -> Path:
    candidate = Path(artifact_path).expanduser()
    resolved = candidate if candidate.is_absolute() else (REPO_ROOT / candidate)
    resolved = resolved.resolve()
    if not resolved.exists():
        raise ValueError(f"artifact_path not found: {artifact_path}")
    if REPO_ROOT not in resolved.parents and resolved != REPO_ROOT:
        raise ValueError("artifact_path must stay inside the repo root.")
    return resolved


def _derive_title(text: str, resolved_path: Path) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return resolved_path.stem.replace("-", " ").strip()


def _extract_markdown_section_items(text: str, heading: str) -> tuple[str, ...]:
    lines = text.splitlines()
    normalized_heading = heading.casefold()
    in_section = False
    items: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_heading = stripped[3:].strip().casefold()
            if in_section and current_heading != normalized_heading:
                break
            in_section = current_heading == normalized_heading
            continue
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
            continue
        if items:
            items[-1] = f"{items[-1]} {stripped}".strip()
    return tuple(item for item in items if item)


__all__ = [
    "build_continuity_pack_request_from_artifact",
    "CONTINUITY_PACK_SECTIONS",
    "ContinuityPack",
    "ContinuityPackOutcome",
    "ContinuityPackRequest",
    "render_continuity_pack_markdown",
]
