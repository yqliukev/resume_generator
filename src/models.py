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
    
    def to_dict(self) -> dict:
        return {
            "preamble": self.preamble,
            "header": self.header,
            "trailing": self.trailing,
            "sections": [section.to_dict() for section in self.sections],
        }
    
    @classmethod
    def from_dict(cls, raw: dict) -> "ResumeDocument | None":
        preamble = raw.get("preamble")
        if not isinstance(preamble, str):
            preamble = None

        header = raw.get("header")
        if not isinstance(header, str):
            header = None
            
        trailing = raw.get("trailing", str)
        if not isinstance(trailing, str):
            trailing = None

        raw_sections = raw.get("sections")
        sections: list[Section] = []
        if isinstance(raw_sections, list):
            for raw_section in raw_sections:
                if isinstance(raw_section, dict):
                    section = Section.from_dict(raw_section)
                    if section:
                        sections.append(section)

        return cls(
            preamble=preamble,
            header=header,
            trailing=trailing,
            sections=sections
        )


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
class LinkLibrary:
    """Library of LinkRecords"""

    source_path: str
    source_file: SourceFile
    links: dict[str, GeneratedFile] = field(default_factory=dict) # keyed by generated file path

    def to_dict(self) -> dict: 
        return {
            "source_path": self.source_path,
            "source_file": self.source_file.to_dict(),
            "links": {gen_path: gen_file.to_dict() for gen_path, gen_file in self.links.items()},
        }
    
    @classmethod
    def from_dict(cls, raw: dict) -> "LinkLibrary | None":
        path = raw.get("source_path")
        raw_file = raw.get("source_file")
        if isinstance(raw_file, dict):
            source_file = ResumeDocument.from_dict(raw_file) 
        
        raw_links = raw.get("links")
        links: dict[str, GeneratedFile] = {}
        if isinstance(raw_links, dict):
            for gen_path, raw_gen_file in raw_links.items():
                if not isinstance(gen_path, str) or not isinstance(raw_gen_file, dict):
                    continue
                raw_gen_file = ResumeDocument.from_dict(raw_gen_file)
                if raw_gen_file is not None:
                    gen_file = ResumeDocument.from_dict(raw_gen_file)
                    if gen_file is not None:
                        links[gen_path] = gen_file

        return cls(
            source_path=path,
            source_file=source_file,
            links=links,
        )
        
        
