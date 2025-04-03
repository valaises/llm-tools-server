from dataclasses import dataclass

import aiohttp


@dataclass
class ToolContext:
    http_session: aiohttp.ClientSession