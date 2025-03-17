import os

import fitz
from enum import Enum

from core.logger import debug

MAX_TEXT_PAGE_SIZE_KB=500


class PageType(Enum):
    """Enumeration representing the possible types of a PDF page."""

    DRAWING_PAGE = 0  # Represents a drawing page
    SPEC_PAGE = 1  # Represents a specification page
    UNCLASSIFIED_PAGE = 2  # Represents a page that could not be classified


class PDFPageClassifier:
    """
    A classifier for determining the type of pages within a PDF document.

    This classifier analyzes each page in a PDF document to determine whether it is
    a specification page, a drawing page, or cannot be classified based on vector drawings,
    raster image coverage, and text block coverage.

    Attributes:
        PAGE_TOP_AREA_PERCENTAGE_LIMIT (float): The percentage height from the top of the
            page to define the region for image and vector detection.
        MIN_VECTOR_IMAGE_SIZE (int): The minimum size (width or height) of images
            to be considered during classification.
        DRAWING_PAGE_VECTOR_IMAGES_COUNT_THRESHOLD (int): The threshold for the number of vector images
            to classify a page as a drawing page.
        RASTER_PAGE_AREA_PERCENTAGE_THRESHOLD (int): The threshold for the percentage of the page
            area covered by raster images to classify a page as unclassified.
        SPEC_PAGE_TEXT_AREA_PERCENTAGE_THRESHOLD (int): The threshold for the percentage of the page
            area covered by text blocks to classify a page as unclassified.
        SPEC_PAGE_MIN_VECTOR_COUNT_THRESHOLD (int): The minimum number of vector images to classify a page
            as a specification page.
        pdf_doc (fitz.Document): The PDF document to classify.
    """

    PAGE_TOP_AREA_PERCENTAGE_LIMIT = 0.2  # 20% of the page height
    DRAWING_PAGE_VECTOR_IMAGES_COUNT_THRESHOLD = 100  # Threshold for vector images to classify as DRAWING_PAGE
    RASTER_PAGE_AREA_PERCENTAGE_THRESHOLD = 95  # 95% raster coverage triggers UNCLASSIFIED_PAGE
    SPEC_PAGE_TEXT_AREA_PERCENTAGE_THRESHOLD = 20  # 20% text block coverage threshold
    SPEC_PAGE_MIN_VECTOR_COUNT_THRESHOLD = 15  # Minimum vector count threshold for SPEC_PAGE
    MIN_VECTOR_IMAGE_SIZE = 10  # Minimum size to consider a vector drawing significant

    def __init__(
        self,
        pdf_doc: fitz.Document,
    ):
        """
        Initialize the PDFPageClassifier with the provided PDF document.

        Args:
            pdf_doc (fitz.Document): The PDF document to classify.
        """
        self.pdf_doc = pdf_doc

    def classify_document(self) -> list[PageType]:
        """
        Classify all pages in the PDF document as either 'specification pages',
        'drawing pages', or 'unclassified pages'.

        Iterates over all pages in the PDF document, classifying each one based on
        the criteria defined in the `classify_page` method.

        Returns:
            list[PageType]: A list of PageType values where each element corresponds
                to a page in the document (SPEC_PAGE, DRAWING_PAGE, or UNCLASSIFIED_PAGE).
        """
        result = []

        for page_num in range(self.pdf_doc.page_count):
            page = self.pdf_doc.load_page(page_num)
            page_type = self.classify_page(page, page_num)
            result.append(page_type)

        return result

    def classify_page(self, page: fitz.Page, page_number: int) -> PageType:
        """Determines whether a page is a 'specification page' or a
        'drawing page'.

        A page is considered a 'specification page' if it contains
        at most one image and one vector drawing whose bottom edge is within the
        top 20% of the page height. If any image or vector drawing extends below
        this limit, the page is classified as a 'drawing page'.

        Args:
            page (fitz.Page): The PDF page to classify.
            page_number (int): The page number in the PDF document.

        Returns:
            PageType: PageType.SPEC_PAGE if classified as a specification page,
                otherwise PageType.DRAWING_PAGE.
        """
        page_height = page.rect.height
        top_limit = page_height * self.PAGE_TOP_AREA_PERCENTAGE_LIMIT

        result = PageType.SPEC_PAGE

        if self._is_page_too_big_for_a_text_page(page, page_number):
            debug(
                f"Page {page_number} size is bigger than"
                f" {MAX_TEXT_PAGE_SIZE_KB} - considered a Drawings page."
            )
            result = PageType.DRAWING_PAGE

        else:
            vector_images_count = self._count_vector_images(page, top_limit)
            raster_coverage_percent = self._calculate_raster_coverage_percentage(
                page)
            text_blocks_coverage_percent = self._calculate_text_blocks_coverage_percentage(
                page)

            if vector_images_count >= self.DRAWING_PAGE_VECTOR_IMAGES_COUNT_THRESHOLD:
                result = PageType.DRAWING_PAGE
            elif (
                raster_coverage_percent >= self.RASTER_PAGE_AREA_PERCENTAGE_THRESHOLD
                and text_blocks_coverage_percent <= self.SPEC_PAGE_TEXT_AREA_PERCENTAGE_THRESHOLD
            ):
                debug(
                    f"Page {page.number} classified as UNCLASSIFIED_PAGE.")
                result = PageType.UNCLASSIFIED_PAGE

        return result

    def _is_page_too_big_for_a_text_page(self,
                                         page: fitz.Page,
                                         page_number: int) -> bool:
        """Check if the page is too big to be a text page without drawings.
        Usually, the text page size is less than N KB.

        Args:
            page (fitz.Page): The PDF page to check.
            page_number (int): The page number in the PDF document.

        Returns:
            bool: True if page is too big to be a text page, False otherwise.
        """
        # Save the page to a new PDF file in the /tmp directory
        tmp_pdf_path = f"/tmp/temp_page_{page.number}.pdf"
        new_pdf = fitz.open()
        new_pdf.insert_pdf(page.parent, from_page=page_number, to_page=page_number)
        new_pdf.save(tmp_pdf_path)
        new_pdf.close()

        # Get the size of the new PDF file
        file_size_bytes = os.path.getsize(tmp_pdf_path)
        file_size_kb = file_size_bytes / 1024
        debug(f"Size of page {page_number+1}: {file_size_kb:.2f} KB")

        os.remove(tmp_pdf_path)

        return file_size_kb > MAX_TEXT_PAGE_SIZE_KB

    def _count_vector_images(self, page: fitz.Page, top_limit: float) -> int:
        """
        Estimate the number of significant vector drawings on the page.

        A vector drawing is considered significant if it:
            - Exceeds the minimum size.
            - Contains more than a single line.
            - Is positioned below the top margin.

        The method returns a simplified count used to determine if the page is a drawing page.

        Args:
            page (fitz.Page): The PDF page to analyze.
            top_limit (float): The height limit from the top of the page to ignore vector positions.

        Returns:
            int: The number of qualifying vector drawings found on the page.
        """
        vector_drawings = page.get_cdrawings()
        vector_count = 0

        # Quick classification based on total vector count
        if len(vector_drawings) < self.SPEC_PAGE_MIN_VECTOR_COUNT_THRESHOLD:  # type: ignore
            return 0
        elif len(vector_drawings) > self.DRAWING_PAGE_VECTOR_IMAGES_COUNT_THRESHOLD:  # type: ignore
            return self.DRAWING_PAGE_VECTOR_IMAGES_COUNT_THRESHOLD

        for vector_drawing in vector_drawings:  # type: ignore
            rect = fitz.Rect(vector_drawing["rect"])
            bottom_y = rect.y1
            width = rect.width
            height = rect.height

            # Skip small vector drawings
            if max(width, height) <= self.MIN_VECTOR_IMAGE_SIZE:
                continue

            items = vector_drawing["items"]
            # Skip single-line vector drawings
            if len(items) == 1 and items[0][0] == "l":
                continue

            # Ignore shapes entirely within the top 20% of the page
            if bottom_y <= top_limit:
                continue
            else:
                vector_count += 1

        return vector_count

    def _calculate_raster_coverage_percentage(self, page: fitz.Page) -> float:
        """
        Calculate the percentage of the page area covered by raster images.

        Raster images are identified and their total area is computed to determine
        the coverage percentage relative to the entire page area.

        Args:
            page (fitz.Page): The PDF page to analyze.

        Returns:
            float: The percentage of the page covered by raster images.
                Returns %100.0 if the page area is zero to avoid division by zero.
        """
        page_area = page.rect.width * page.rect.height
        image_area = 0.0
        seen_images = set()
        raster_images = page.get_images(full=True)

        for img in raster_images:
            xref = img[0]  # Image reference
            width = img[2]  # Image width
            height = img[3]  # Image height

            if xref in seen_images:
                continue  # Skip duplicate images

            image_area += width * height
            seen_images.add(xref)

        return (image_area / page_area) * 100 if page_area > 0 else 100.0

    def _calculate_text_blocks_coverage_percentage(self, page: fitz.Page) -> float:
        """
        Calculate the percentage of the page area covered by text blocks.

        Text blocks are retrieved and their combined area is calculated as a percentage
        of the total page area.

        Args:
            page (fitz.Page): The PDF page to analyze.

        Returns:
            float: The percentage of the page area covered by text blocks.
                Returns %100.0 if the page area is zero to avoid division by zero.
        """
        blocks = page.get_text("blocks")  # type: ignore
        total_area = 0.0
        page_area = page.rect.width * page.rect.height

        for block in blocks:
            x0, y0, x1, y1, *_ = block
            width = x1 - x0
            height = y1 - y0
            total_area += width * height

        return (total_area / page_area) * 100 if page_area > 0 else 100.0
