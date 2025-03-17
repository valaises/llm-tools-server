import re


SECTION_END_PATTERN = re.compile(
    r'END\s*OF\s*SECTION', re.IGNORECASE
)
SECTION_HEADER_PATTERN_WITH_DOT = re.compile(
    r'\bSection\s((?:\d\s*)+\.?\d*)\b', re.IGNORECASE
)
SECTION_PATTERN_WITHOUT_SECTION_WORD = re.compile(
    r'(?<!\S)(\d\s?){6,}(-\s?\d+)?(\s?of\s?\d+)?'
)
FAKE_SECTION_PATTERN = re.compile(
    r'^(?!\s*[A-Za-z])\s*(\d+\.\s*)?Section\s*\d{2}\s*\d{2}\s*\d{2}|^'
    r'[A-Za-z].*Section\s*\d{2}\s*\d{2}\s*\d{2}',
    re.IGNORECASE
)
SECTION_START_PATTERN = re.compile(
    r'SECTION\s*(\d\s*\d\s*\d\s*\d\s*\d\s*\d)',
    re.IGNORECASE
)

IS_EXECUTED_IN_CLOUD = False
PDF_PAGE_COUNT_THRESHOLD = 200
MIN_NON_SYMBOL_COUNT = 1
Y1_POS = 3
SPECIFICATION_SECTION_LEN = 6
SECTION_START = 'start'
SECTION_END = 'end'
