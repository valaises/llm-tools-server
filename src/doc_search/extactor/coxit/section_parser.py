"""
This module focuses on parsing sections from a given text.
SectionParserFromDict parse section content by range of section,
    and page content array.
SectionParserFromText parse section by pages content.
It utilizes regex patterns to identify the start and end of sections,
extracts section names, and accumulates corresponding content.

"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List

from core.logger import debug
import doc_search.extactor.coxit.const as c


RangeDict = Dict[str, int]
SectionDict = Dict[str, RangeDict]


@dataclass
class SectionContentData:
    """
    Data class that holds the text and section name extracted from a PDF file.
    """
    text: Optional[str] = field(
        default=None
    )
    section_name: Optional[str] = field(
        default=None
    )

    def to_dict(self) -> dict:
        """
        Converts the dataclass to a dictionary for JSON serialization.
        """
        return {self.section_name: self.text}


class SectionBaseParser(ABC):
    """Abstract base class for section parsing."""
    @abstractmethod
    def start_parsing(self) -> list[SectionContentData]:
        """Extracts sections from the provided input."""
        pass


class SectionParserFromDict(SectionBaseParser):
    """
    Parses sections from a pre-structured list of dictionaries.

    Attributes:
        section_dicts: A list of dictionaries
            with {"section_name": section_content}.
        extracted_text A list of text extracted
            from every page from the file.
    """
    section_dicts: SectionDict
    extracted_text: List[str]

    def __init__(self, section_dicts: SectionDict, extracted_text: List[str]):
        self._section_dicts = section_dicts
        self._extracted_text = extracted_text

    def _parse_sections(self) -> list[SectionContentData]:
        debug("Starting parsing sections from sections dict")
        sections: Dict[str, SectionContentData] = {}

        for section_name, range_dict in self._section_dicts.items():

            first_page = range_dict[c.SECTION_START] - 1
            last_page = range_dict[c.SECTION_END]

            section_text = "\n".join(self._extracted_text[first_page:last_page])

            sections[section_name] = SectionContentData(
                section_name=section_name,
                text=section_text
            )

        return list(sections.values())

    def start_parsing(self) -> list[SectionContentData]:
        """
        Initiates the parsing process and returns a list of parsed sections.
        """
        return self._parse_sections()


class SectionParserFromText(SectionBaseParser):
    """
    A parser designed to extract and process sections from a given text,
    specifically formatted with "SECTION" markers. The parser groups lines
    belonging to the same section, merges identical sections, and extracts text
    for each distinct section.
    """
    def __init__(self, extracted_text: str) -> None:
        self._extracted_text = extracted_text

    def _extract_section_name(self, line: str) -> Optional[str]:
        """
        Extracts the formatted section name from a given line using the
        SECTION_START_PATTERN regex. Returns None if no section name is found.
        """
        match = c.SECTION_START_PATTERN.search(line)
        if match:
            raw_section = match.group(1)
            return raw_section.replace(" ", "")
        return None

    def _is_section_start(self, line: str) -> bool:
        # Skip lines that are likely not part of a section
        result = False
        if (
            c.FAKE_SECTION_PATTERN.match(line) and
            c.SECTION_END_PATTERN.search(line) is None
        ):
            debug(f"Skipping FAKE section: {line}")
        elif c.SECTION_START_PATTERN.search(line) is not None:
            result = True
        return result

    def _parse_sections(self) -> list[SectionContentData]:
        """
        Processes the input text and parses it into distinct sections based
        on the SECTION_START_PATTERN and SECTION_END_PATTERN markers, appending
        or merging text as needed when multiple occurrences of the same
        section name exist.
        """
        debug("Starting parsing sections from extracted text")
        sections: Dict[str, SectionContentData] = {}
        current_section_lines = []
        current_section_name = None

        for line in self._extracted_text.splitlines():
            # Check if the line indicates the start of a new section
            if self._is_section_start(line) is True:
                if current_section_name is not None:
                    # Save the current section before starting a new one
                    if current_section_name not in sections:
                        sections[current_section_name] = SectionContentData(
                            text="\n".join(current_section_lines),
                            section_name=current_section_name
                        )
                    else:
                        # Append text to the existing section
                        sections[  # pyright: ignore [reportOperatorIssue]
                            current_section_name
                        ].text += "\n" + "\n".join(current_section_lines)
                    current_section_lines = []

                current_section_name = self._extract_section_name(line)

            # Add line to the current section
            if current_section_name is not None:
                current_section_lines.append(line)

            # Check if the line indicates the end of the current section
            if (
                c.SECTION_END_PATTERN.search(line) is not None and
                current_section_name is not None
            ):
                if current_section_name not in sections:
                    sections[current_section_name] = SectionContentData(
                        text="\n".join(current_section_lines),
                        section_name=current_section_name
                    )
                else:
                    # Append text to the existing section
                    sections[  # pyright: ignore [reportOperatorIssue]
                        current_section_name
                    ].text += "\n" + "\n".join(current_section_lines)
                current_section_lines = []
                current_section_name = None

        # Handle any remaining lines for the last section
        if (
            current_section_name is not None and
            current_section_lines is not None
        ):
            if current_section_name not in sections:
                sections[current_section_name] = SectionContentData(
                    text="\n".join(current_section_lines),
                    section_name=current_section_name
                )
            else:
                sections[  # pyright: ignore [reportOperatorIssue]
                    current_section_name
                ].text += "\n" + "\n".join(current_section_lines)

        debug(f"Extracted {len(sections)} sections from the text")

        return list(sections.values())

    def start_parsing(self) -> list[SectionContentData]:
        """
        Initiates the parsing process and returns a list of parsed sections.
        """
        return self._parse_sections()
