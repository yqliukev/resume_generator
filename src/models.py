from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Entry:
    '''
      Entry within a section, e.g. "Backend Developer @ Ground News". 
      Each "skill line" is an entry.
    '''
    display_label: str   # clean text for UI tree (e.g. "Backend Dev @ Ground News")
    raw_text: str        # verbatim source lines, preserved for output
    selected: bool = True

    def to_dict(self) -> dict:
        return {
            "display_label": self.display_label,
            "raw_text": self.raw_text,
            "selected": self.selected,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entry | None":
        display_label = data.get("display_label")
        raw_text = data.get("raw_text")
        if not isinstance(display_label, str) or not isinstance(raw_text, str):
            return None
        selected = data.get("selected", True)
        return cls(display_label=display_label, raw_text=raw_text, selected=bool(selected))


@dataclass
class Section:
    ''' Document section, e.g. "Work Experience". '''
    name: str            # e.g. "Work Experience"
    section_type: str    # "standard" | "skills"
    raw_header: str      # "\section{...}" line verbatim (may include preceding comment)
    list_prefix: str     # lines between header and first entry
    list_suffix: str     # lines after last entry (before next section)
    entries: list[Entry] = field(default_factory=list)
    selected: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "section_type": self.section_type,
            "raw_header": self.raw_header,
            "list_prefix": self.list_prefix,
            "list_suffix": self.list_suffix,
            "selected": self.selected,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Section | None":
        name = data.get("name")
        section_type = data.get("section_type")
        raw_header = data.get("raw_header")
        list_prefix = data.get("list_prefix")
        list_suffix = data.get("list_suffix")

        if not isinstance(name, str) or not isinstance(section_type, str):
            return None
        if not isinstance(raw_header, str) or not isinstance(list_prefix, str) or not isinstance(list_suffix, str):
            return None

        raw_entries = data.get("entries", [])
        entries: list[Entry] = []
        if isinstance(raw_entries, list):
            for raw_entry in raw_entries:
                if not isinstance(raw_entry, dict):
                    continue
                entry = Entry.from_dict(raw_entry)
                if entry is not None:
                    entries.append(entry)

        selected = data.get("selected", True)
        return cls(
            name=name,
            section_type=section_type,
            raw_header=raw_header,
            list_prefix=list_prefix,
            list_suffix=list_suffix,
            entries=entries,
            selected=bool(selected),
        )


@dataclass
class ResumeDocument(ABC):
    ''' Parameters also called Zones '''
    preamble: str           # everything up to (not including) \begin{center}
    header: str             # \begin{center}...\end{center} block (inclusive)
    sections: list[Section] = field(default_factory=list)
    trailing: str = ""      # \end{document} and any trailing content

    @property
    @abstractmethod
    def document_type(self) -> str:
        """Return the document category used for persistence."""


def _normalize_path(path: str) -> str:
    return str(Path(path).expanduser().resolve(strict=False))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class SourceFile(ResumeDocument):
    path: str = ""

    def __post_init__(self) -> None:
        self.path = _normalize_path(self.path)

    @property
    def document_type(self) -> str:
        return "source"


@dataclass
class GeneratedFile(ResumeDocument):
    path: str = ""

    def __post_init__(self) -> None:
        self.path = _normalize_path(self.path)

    @property
    def document_type(self) -> str:
        return "generated"


def _section_entries_map(document: ResumeDocument) -> dict[str, set[str]]:
    return {
        section.name: {entry.display_label for entry in section.entries}
        for section in document.sections
    }


def validate_generated_subset(source: SourceFile, generated: GeneratedFile) -> None:
    """Ensure generated sections/entries are strict subsets of the source file."""
    source_sections = _section_entries_map(source)
    source_section_types = {section.name: section.section_type for section in source.sections}

    for target_section in generated.sections:
        if target_section.name not in source_sections:
            raise ValueError(f"Generated section is not present in source: {target_section.name}")

        source_section_type = source_section_types.get(target_section.name)
        if target_section.section_type != source_section_type:
            raise ValueError(
                f"Generated section type mismatch for {target_section.name}: "
                f"{target_section.section_type} != {source_section_type}"
            )

        source_entries = source_sections[target_section.name]
        for target_entry in target_section.entries:
            if target_entry.display_label not in source_entries:
                raise ValueError(
                    "Generated entry is not present in source section "
                    f"{target_section.name}: {target_entry.display_label}"
                )


@dataclass
class LinkRecord:
    """Persisted link between one source document and one generated document."""

    source_path: str
    target_path: str
    metadata_path: str
    sections: dict[str, list[str]] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utc_now_iso)
    schema_version: int = 1

    def __post_init__(self) -> None:
        self.source_path = _normalize_path(self.source_path)
        self.target_path = _normalize_path(self.target_path)
        self.metadata_path = _normalize_path(self.metadata_path)

    @staticmethod
    def default_metadata_path(target_path: str) -> str:
        target_abs = Path(_normalize_path(target_path))
        return str(target_abs.parent / f"{target_abs.name}.resume-link.json")

    @classmethod
    def from_documents(
        cls,
        source: SourceFile,
        generated: GeneratedFile,
        metadata_path: str | None = None,
    ) -> "LinkRecord":
        validate_generated_subset(source, generated)

        sections: dict[str, list[str]] = {}
        for section in generated.sections:
            sections[section.name] = [entry.display_label for entry in section.entries]

        return cls(
            source_path=source.path,
            target_path=generated.path,
            metadata_path=metadata_path or cls.default_metadata_path(generated.path),
            sections=sections,
            updated_at=_utc_now_iso(),
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "updated_at": self.updated_at,
            "source": {"path": self.source_path},
            "target": {
                "path": self.target_path,
                "sections": [
                    {"name": section_name, "entries": list(entry_labels)}
                    for section_name, entry_labels in self.sections.items()
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: dict, metadata_path: str) -> "LinkRecord":
        raw_source = data.get("source", {})
        raw_target = data.get("target", {})
        source_path = raw_source.get("path")
        target_path = raw_target.get("path")
        if not isinstance(source_path, str) or not isinstance(target_path, str):
            raise ValueError("Invalid link record payload: missing source/target path")

        sections: dict[str, list[str]] = {}
        raw_sections = raw_target.get("sections", [])
        if isinstance(raw_sections, list):
            for raw_section in raw_sections:
                if not isinstance(raw_section, dict):
                    continue
                section_name = raw_section.get("name")
                if not isinstance(section_name, str) or not section_name.strip():
                    continue
                raw_entries = raw_section.get("entries", [])
                entry_labels: list[str] = []
                if isinstance(raw_entries, list):
                    for label in raw_entries:
                        if isinstance(label, str):
                            entry_labels.append(label)
                sections[section_name] = entry_labels

        raw_schema_version = data.get("schema_version", 1)
        schema_version = int(raw_schema_version) if isinstance(raw_schema_version, (int, float)) else 1

        updated_at = data.get("updated_at")
        if not isinstance(updated_at, str):
            updated_at = _utc_now_iso()

        return cls(
            source_path=source_path,
            target_path=target_path,
            metadata_path=metadata_path,
            sections=sections,
            updated_at=updated_at,
            schema_version=schema_version,
        )
