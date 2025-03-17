"""
File reader executor module.
"""
import logging
from typing import Optional

from doc_search.extactor.coxit.pdf_extractor import PDFExtractor
from doc_search.extactor.coxit.section_parser import SectionContentData, SectionParserFromText, SectionParserFromDict

logger: logging.Logger = logging.getLogger(__name__)



class FileReader:
    """
    File reader executor class.
    """
    def __init__(
        self,
        file_data: bytes,
        file_name: str,
    ) -> None:
        self._file_data = file_data

        self._file_name = file_name

    def extract_text(
        self,
        for_llm: bool = True,
    ) -> Optional[list[SectionContentData]]:
        """
        Extracts the contents of a pdf file and splits it into sections
        The extracted content is in Markdown format
        """
        parsed_sections = []

        extractor = PDFExtractor(
            file_data=self._file_data,
            file_name=self._file_name
        )
        extracted_text_list: list[str] = extractor.extract_content(
            for_llm=for_llm,
        )

        if len(extracted_text_list) == 0:
            logger.error("There are no text extracted from PDF.")
            return None

        sections_dict = extractor.extract_sections_from_colontitles()
        logger.info(
            f"Extracted sections from "
            f"colontitles: {sections_dict}"
        )

        if len(sections_dict) != 0:
            parsed_sections = SectionParserFromDict(
                sections_dict, extracted_text_list
            ).start_parsing()

        else:
            extracted_text = "\n".join(
                extracted_text_list
            )

            logger.info(
                f"{len(extracted_text)=!r}, "
            )

            parsed_sections = SectionParserFromText(
                extracted_text
            ).start_parsing()

        return parsed_sections
