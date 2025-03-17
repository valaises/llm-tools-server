import re
import logging
import pathlib

from collections import Counter
from typing import Set, Dict

import fitz
import pymupdf
import pymupdf4llm

import doc_search.extactor.coxit.const as c
from core.logger import debug, exception
from doc_search.extactor.coxit.page_classifier import PageType, PDFPageClassifier

RangeDict = Dict[str, int]
SectionDict = Dict[str, RangeDict]


class PDFPagesCountLimitExceeded(Exception):
    """
    Exception raised when a PDF file contains more pages than the allowed limit.

    This exception is used to enforce a maximum page count restriction for PDF
    processing.
    """
    pass


class PDFExtractor:
    """
    PDFExtractor class extracts text and images from PDF files.
    Also removes headers and footers from PDF files.
    """
    ALLOWED_CHARS = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        "0123456789 .,@#&()[]-_"
    )
    HEADER_SEARCH_PERCENTAGE: float = 0.15
    FOOTER_SEARCH_PERCENTAGE: float = 0.88
    TOP_RIGHT_X: int = 0
    TOP_RIGHT_Y: int = 0
    DIR_PATH: str = "data/pdf_processing/"
    PDF_FILE_PATH: str = DIR_PATH + "pymupdf_edited_pdf"
    MD_FILE_PATH: str = DIR_PATH + "pymupdf_md"
    A4_RECT = fitz.Rect(0, 0, 595.44, 841.68)
    classifier_result: list[PageType] = []

    def __init__(self, file_data: bytes, file_name: str) -> None:
        self._file_data = file_data
        self._file_name = file_name
        self.classifier_result = self._classify_pdf_pages()

    def _classify_pdf_pages(self):
        """
        Remove all annotations from the PDF because they
        are vector drawings and classify the document.
        """
        # Remove all annotations from the PDF. Annotations are vector drawings,
        # so specification pages can be misclassified as drawing pages.
        self.pdf_without_annot = self._remove_annotations()

        return PDFPageClassifier(
            pdf_doc=self.pdf_without_annot
        ).classify_document()

    def __delete_candidates(
        self,
        page: fitz.Page,
        header_candidates: list[str],
        footer_candidates: list[str],
        header_clip: fitz.Rect,
        footer_clip: fitz.Rect
    ) -> tuple[list[str], list[str]]:
        removed_headers, removed_footers = [], []
        for line in header_candidates:
            instances = page.search_for(line, clip=header_clip)
            for inst in instances:
                page.add_redact_annot(inst, text="")
                removed_headers.append(line)

        for line in footer_candidates:
            instances = page.search_for(line, clip=footer_clip)
            for inst in instances:
                page.add_redact_annot(inst, text="")
                removed_footers.append(line)

        page.apply_redactions()

        return removed_headers, removed_footers

    def __remove_candidates(
        self,
        header_candidates: list[str],
        footer_candidates: list[str],
        pdf: pymupdf.Document
    ) -> pymupdf.Document:
        removed_headers, removed_footers = [], []
        # Remove header and footer candidates from PDF pages with clip
        # to avoid removing text that is not header or footer
        for page in pdf:  # pylint: disable=unused-variable
            try:
                page_height = page.rect.height
                page_width = page.rect.width

                header_clip = pymupdf.Rect(
                    self.TOP_RIGHT_X,
                    self.TOP_RIGHT_Y,
                    page_width,
                    page_height * self.HEADER_SEARCH_PERCENTAGE
                )
                footer_clip = pymupdf.Rect(
                    self.TOP_RIGHT_X,
                    page_height * self.FOOTER_SEARCH_PERCENTAGE,
                    page_width,
                    page_height
                )

                removed_headers_candidates, removed_footers_candidates = (
                    self.__delete_candidates(
                        page=page,
                        header_candidates=header_candidates,
                        footer_candidates=footer_candidates,
                        header_clip=header_clip,
                        footer_clip=footer_clip
                    )
                )
                removed_headers.extend(removed_headers_candidates)
                removed_footers.extend(removed_footers_candidates)

            except Exception as error:
                exception(f"Error removing header and footer "
                                 f"candidates: {error}")

        removed_headers = list(set(removed_headers))
        removed_footers = list(set(removed_footers))

        debug(f"{header_candidates=!r}\n{removed_headers=!r}")
        debug(f"{footer_candidates=!r}\n{removed_footers=!r}")
        return pdf

    def _remove_headers_and_footers_from_pdf(
        self,
        file_bytes: bytes,
        output_file: str,
    ) -> bytes:
        logging.info("Removing headers and footers from PDF file...")
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
            header_texts, footer_texts = [], []
            header_candidates, footer_candidates = [], []

            # Search for header and footer candidates
            for page_number, page in enumerate(pdf):
                if self.classifier_result[page_number] == PageType.DRAWING_PAGE:
                    continue

                page_height = page.rect.height
                top_text = page.get_text(
                    "text",
                    clip=pymupdf.Rect(
                        self.TOP_RIGHT_X,
                        self.TOP_RIGHT_Y,
                        page.rect.width,
                        page_height *
                        self.HEADER_SEARCH_PERCENTAGE
                    )
                )
                bottom_text = page.get_text(
                    "text",
                    clip=pymupdf.Rect(
                        self.TOP_RIGHT_X,
                        page_height *
                        self.FOOTER_SEARCH_PERCENTAGE,
                        page.rect.width,
                        page_height
                    )
                )
                header_texts.extend(top_text.splitlines())
                footer_texts.extend(bottom_text.splitlines())

            # Find header and footer candidates
            # that appear on more than half of the pages
            if header_texts or footer_texts:
                header_candidates = [text for text in set(header_texts) if
                                     header_texts.count(
                                         text
                                     ) >= pdf.page_count // 2]
                footer_candidates = [text for text in set(footer_texts) if
                                     footer_texts.count(
                                         text
                                     ) >= pdf.page_count // 2]

            pdf = self.__remove_candidates(
                header_candidates=header_candidates,
                footer_candidates=footer_candidates,
                pdf=pdf
            )

            # Save edited PDF file to disk if not executed in cloud
            if c.IS_EXECUTED_IN_CLOUD is False:
                debug(f"Saving PDF file to disk: {output_file}")
                output_path = pathlib.Path(
                    f"{self.PDF_FILE_PATH}/{output_file}.pdf"
                )
                output_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                pdf.save(output_path)

            debug("Returning PDF as bytes.")

            return pdf.tobytes()

    def _decode_pdf_text_bytes(
        self,
        file_bytes: bytes,
        for_llm: bool = False,
    ) -> list[str]:
        debug("Decoding PDF text bytes...")
        text_content: list = []

        # Open PDF file with pymupdf as pymupdf.Document object
        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:

            # Extract text from PDF pages for llm
            if for_llm is True:
                for page_num in range(pdf.page_count):
                    markdown_content = pymupdf4llm.to_markdown(
                        doc=pdf,
                        pages=[page_num],
                        show_progress=False,
                        margins=0,
                        # (int) ignore page with too many vector graphics.
                        # graphics_limit=None,
                    )
                    text_content.append(markdown_content)
                    debug(f"Extracted {len(markdown_content)}"
                                f" chars from page {page_num}")

            # Extract text from PDF pages with default settings
            else:
                for page in pdf:
                    text = page.get_text()
                    if text:
                        text_content.append(text)

        if c.IS_EXECUTED_IN_CLOUD is False:
            # Save extracted text to disk
            output_path = pathlib.Path(
                f"{self.MD_FILE_PATH}/{self._file_name}.md"
            )
            debug(f"Saving text file to disk: {output_path}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes("\n".join(text_content).encode())

        debug("Returning extracted text content.")

        return text_content

    def _check_pdf_page_count(
        self,
    ) -> tuple[bool, int]:
        # Check pdf page count before processing
        file_bytes = self._file_data
        result = True
        pdf_page_count = 0

        with pymupdf.open(stream=file_bytes, filetype="pdf") as pdf:
            debug(f"{pdf.page_count=!r}")
            pdf_page_count = pdf.page_count  # Get page count here
            if pdf_page_count >= c.PDF_PAGE_COUNT_THRESHOLD:
                result = False

        return result, pdf_page_count

    def _remove_annotations(self) -> fitz.Document:
        # Remove all annotations from the PDF.
        # Annotations are vector drawings, and they can mislead the
        # classification of pages as drawing pages or specification pages.
        uploaded_pdf = fitz.open(self._file_name, self._file_data)
        for page_num in range(uploaded_pdf.page_count):
            page = uploaded_pdf.load_page(page_num)
            for xref in page.annot_xrefs():
                try:
                    annot = page.load_annot(xref[0])
                    if annot is not None:
                        page.delete_annot(annot)
                except Exception as error:
                    err_str = f"Error deleting annotation: {error}"

                    # Before if is here to avoid logging a spamming error that
                    # means nothing actually.
                    if "is not an annot of this page" in str(error):
                        debug(err_str)
                    else:
                        exception(err_str)
        return uploaded_pdf

    def _clear_drawing_pages(self, pdf: fitz.Document) -> fitz.Document:

        new_pdf = fitz.open()

        # This function basically creates a copy of the input doc but replaces
        # all drawing pages with blank pages.
        # The drawings mess up with footer/header removal algorithm and increase
        # its execution time and resources usage dramatically.
        # Drawing pages are pages that contain vector drawings, and they should
        # be removed from the PDF before extracting text content
        for page_num in range(pdf.page_count):
            if self.classifier_result[page_num] == PageType.DRAWING_PAGE:
                # Insert an empty page in the new document
                debug(f"Inserting blank page {page_num}")
                new_pdf.insert_page(
                    page_num,
                    width=self.A4_RECT.width,
                    height=self.A4_RECT.height
                )
            else:
                debug(f"Copying page {page_num} to the new document")
                # Copy the page from the old document to the new document
                new_pdf.insert_pdf(pdf, from_page=page_num, to_page=page_num)
        pdf.close()

        return new_pdf

    def _add_page_numbers(self, pdf: fitz.Document) -> fitz.Document:
        # Add text to each page
        for page_num in range(pdf.page_count):
            page = pdf.load_page(page_num)
            page.insert_text((10, 10),
                             f"[PAGE-{page_num + 1}]")
            page.insert_text((10,page.rect.height - 20),
                             f"[END_OF_PAGE-{page_num + 1}]")

        return pdf

    def extract_content(
        self,
        for_llm: bool = True,
    ) -> list[str]:
        """
        Extract content from a PDF file, optionally formatted for LLM
        processing.

        Args:
            for_llm (bool): If True, extract content formatted for LLM
                processing. Defaults to True.

        Returns:
            List[str]: The extracted text content from every page of
            the PDF, or empty array if the PDF pages number is too big.
        """
        debug("Extracting PDF content")
        pdf_page_count_result, pdf_page_count = self._check_pdf_page_count()

        if pdf_page_count_result is False:
            debug(f"The number of pages is too big, {pdf_page_count=!r}")
            raise PDFPagesCountLimitExceeded("The number of pages is too big")

        # Replace all drawing pages with blank page.
        pdf_without_drawing_pages = self._clear_drawing_pages(
            self.pdf_without_annot
        )

        pdf_with_page_numbers = self._add_page_numbers(
            pdf_without_drawing_pages
        )

        bytes_pdf_with_page_numbers = pdf_with_page_numbers.tobytes(
            clean=True, garbage=1
        )

        # Remove headers and footers from PDF
        clear_file_bytes = self._remove_headers_and_footers_from_pdf(
            file_bytes=bytes_pdf_with_page_numbers,
            output_file=self._file_name,
        )

        extracted_text = self._decode_pdf_text_bytes(
            file_bytes=clear_file_bytes,
            for_llm=for_llm,
        )
        debug("PDF content extracted.")

        return extracted_text

    def _get_common_header_words(
            self,
            pdf_file: fitz.Document,
            percentage: float,
            min_occurrences: int,
            top_right_x: int = 0,
            top_right_y: int = 0
    ) -> Set[str]:
        """
        Extract common words from header or footer sections across PDF pages.

        Common words are identified by their
        occurrence on at least half the pages.

        Args:
            pdf_file (fitz.Document): The PDF document to analyze.

            percentage (float): Fraction of the page height
                for the header/footer region.

            top_right_x (Optional[int]): X-coordinate for the
                top-right of the clipping rectangle.

            top_right_y (Optional[int]): Y-coordinate for the
                top-right of the clipping rectangle.

            min_occurrences (int): Minimum number of occurrences of
                extracted common words

        Returns:
            Set[str]: A set of common words found
            in the header/footer.
        """
        line_counts = Counter()

        for page in pdf_file:
            page_width, page_height = page.rect.width, page.rect.height
            clip_rect = fitz.Rect(
                top_right_x,
                top_right_y,
                page_width,
                page_height * percentage
            )

            extracted_text = page.get_text("text", clip=clip_rect)
            line_counts.update(extracted_text.splitlines())

        common_words = {
            line for line, count in line_counts.items()
            if count >= min_occurrences and self._is_valid_common_word(line)
        }

        return common_words

    def _is_valid_common_word(self, word: str) -> bool:
        """
        Check if a word meets the criteria to be
        considered a valid header or footer word.

        Criteria:
            1. Must contain at least one alphanumeric character.
            2. Should not contain unexpected symbols.
            3. Avoid single-letter alphanumeric words like 'A.'
                to exclude common section headers.

        Args:
            word (str): The word to validate.

        Returns:
            bool: True if the word is valid, False otherwise.
        """
        if not word or not any(char.isalnum() for char in word):
            return False

        digit_letter_count = sum(char.isalnum() for char in word)

        # Avoid string like '1.' as valid common word
        if digit_letter_count <= c.MIN_NON_SYMBOL_COUNT:
            return False

        return all(char in self.ALLOWED_CHARS for char in word)

    def _get_headers_height(self, pdf_file: fitz.Document) -> float:
        """
        Determine the height distance from the top edge of the page
        to the most bottom edge of all common words in the header in the PDF.

        Args:
            pdf_file (fitz.Document): The PDF document to analyze.

        Returns:
            float: The maximum header height in pixels.
        """
        min_occurrences = len(
            [
                page_type for page_type in self.classifier_result
                if page_type == PageType.SPEC_PAGE
            ]
        ) // 2

        common_words = self._get_common_header_words(
            pdf_file,
            percentage=self.HEADER_SEARCH_PERCENTAGE,
            min_occurrences=min_occurrences
        )
        max_header_height = 0

        for page_number, page in enumerate(pdf_file):
            # If page is not specification, skip
            if self.classifier_result[page_number] != PageType.SPEC_PAGE:
                continue

            page_width, page_height = page.rect.width, page.rect.height

            for word in common_words:
                headers_candidates = page.search_for(
                    word, clip=fitz.Rect(
                        self.TOP_RIGHT_X,
                        self.TOP_RIGHT_Y,
                        page_width,
                        page_height * self.HEADER_SEARCH_PERCENTAGE
                    )
                )

                if len(headers_candidates) != 0:
                    instance_height = min(
                        word_obj[c.Y1_POS]
                        for word_obj in headers_candidates
                    )
                    max_header_height = max(max_header_height, instance_height)

        return max_header_height

    def _extract_sections_from_headers(
            self, pdf_file: fitz.Document
    ) -> SectionDict:
        """
        Extracts sections from headers in a PDF file.

        Args:
            pdf_file: A PyMuPDF Document object.

        Returns:
            A dictionary where keys are section names,
            and values dictionaries that contain
            'start' and 'end' page numbers.
        """
        sections = {}
        previous_section = ""
        last_specification_page_number = None

        headers_height = self._get_headers_height(pdf_file)

        # If there are no headers, return empty dict
        if headers_height == 0:
            return sections

        for page_number, page in enumerate(pdf_file):
            # If page is not specification, skip
            if self.classifier_result[page_number] != PageType.SPEC_PAGE:
                continue

            last_specification_page_number = page_number

            page_width = page.rect.width

            # Extract text from the upper header region of the page
            top_text = page.get_text(
                "text",
                clip=fitz.Rect(
                    self.TOP_RIGHT_X,
                    self.TOP_RIGHT_Y,
                    page_width,
                    headers_height
                )
            )
            page_text = page.get_text("text")

            # Detect end of the previous section if the pattern is found
            if (c.SECTION_END_PATTERN.search(page_text)
                    and previous_section in sections):

                sections[previous_section][c.SECTION_END] = page_number + 1

            # Search for a section match in the header text
            match = c.SECTION_HEADER_PATTERN_WITH_DOT.search(top_text)
            if match is None:
                continue

            # Extract and clean section identifier
            section_match = match.group(1).strip()

            if "\n" in section_match:
                section_match = section_match.split("\n")[-1]

            # Remove spaces between digits to get a clean section number
            section_name = "".join(section_match.split())

            # If section has format like '112233.44', take only the first part
            section_name = section_name.split(".", maxsplit=1)[0]

            # Validate section length and uniqueness
            if (len(section_name) != c.SPECIFICATION_SECTION_LEN
                    or section_name in sections
            ):
                continue

            sections[section_name] = {
                c.SECTION_START: page_number + 1, c.SECTION_END: None
            }

            # Set end of previous section if not already set
            if (previous_section != ""
                    and sections[previous_section][c.SECTION_END] is None):

                sections[previous_section][c.SECTION_END] = page_number

            # Update the previous section to the current one
            previous_section = section_name

        # Ensure the last section has an end if not set by the last page
        if (previous_section != ""
                and sections[previous_section][c.SECTION_END] is None
                and last_specification_page_number is not None):

            sections[previous_section][c.SECTION_END] = last_specification_page_number + 1  # pylint: disable=line-too-long

        return sections

    def _extract_sections_from_footers(
            self, pdf_file: fitz.Document
    ) -> SectionDict:
        """
        Extracts sections from footers of a given PDF file.

        Args:
            pdf_file: A PyMuPDF Document object.

        Returns:
            A dictionary where keys are section names,
            and values dictionaries that contain
            'start' and 'end' page numbers.
        """
        sections = {}
        previous_section = ""
        last_specification_page_number = None

        for page_number, page in enumerate(pdf_file):
            # If page is not specification, skip
            if self.classifier_result[page_number] != PageType.SPEC_PAGE:
                continue

            last_specification_page_number = page_number

            page_width, page_height = page.rect.width, page.rect.height

            bottom_text = page.get_text(
                "text",
                clip=fitz.Rect(
                    self.TOP_RIGHT_X,
                    page_height * self.FOOTER_SEARCH_PERCENTAGE,
                    page_width,
                    page_height
                )
            ).strip()
            page_text = page.get_text("text")

            # Search for end of section on whole page
            if (c.SECTION_END_PATTERN.search(page_text) is not None
                    and previous_section in sections):

                sections[previous_section][c.SECTION_END] = page_number + 1

            section_match = c.SECTION_PATTERN_WITHOUT_SECTION_WORD.search(
                bottom_text
            )
            if section_match is None:
                continue

            # Remove all spaces from section number and take only first 6 chars
            # for cases where section is in format '12 32 55 - 12'
            section_name = "".join(
                section_match.group(0).split()
            )[:c.SPECIFICATION_SECTION_LEN]

            # Ensure found section has valid length and was not found before
            if (len(section_name) != c.SPECIFICATION_SECTION_LEN
                    or section_name in sections):
                continue

            sections[section_name] = {
                c.SECTION_START: page_number + 1, c.SECTION_END: None
            }

            # Set end of previous section by current page
            # if section does not have end
            if (previous_section != ""
                    and sections[previous_section][c.SECTION_END] is None):

                sections[previous_section][c.SECTION_END] = page_number

            # Set current section as previous
            previous_section = section_name

        # Ensure last section has end if not set by last page
        if (previous_section != ""
                and sections[previous_section][c.SECTION_END] is None
                and last_specification_page_number is not None):

            sections[previous_section][c.SECTION_END] = last_specification_page_number + 1  # pylint: disable=line-too-long

        return sections

    def extract_sections_from_colontitles(self) -> dict:
        """
        Extracts sections from footers/headers.

        If extracting from headers worked, return sections
        from headers, otherwise return footers sections.

        Returns:
            A dictionary where keys are section names,
            and values dictionaries that contain
            'start' and 'end' page numbers.
        """
        sections_dict = {}
        uploaded_pdf = fitz.open(self._file_name, self._file_data)

        sections_from_headers = self._extract_sections_from_headers(
            uploaded_pdf
        )
        sections_from_footers = self._extract_sections_from_footers(
            uploaded_pdf
        )

        headers_sections_count = len(sections_from_headers)
        footers_sections_count = len(sections_from_footers)
        debug(
            f"Extracted sections count from headers : {headers_sections_count}"
        )
        debug(
            f"Extracted sections count from footers : {footers_sections_count}"
        )

        if headers_sections_count != 0 or footers_sections_count != 0:

            if headers_sections_count >= footers_sections_count:

                debug("Returning sections from headers.")
                sections_dict = sections_from_headers

            else:
                debug("Returning sections from footers.")
                sections_dict = sections_from_footers

        return sections_dict