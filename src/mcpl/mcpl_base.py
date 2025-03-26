from dataclasses import dataclass
from typing import List

from mcpl.globals import MCPL_SERVERS


@dataclass
class MCPLServer:
    name: str
    address: str


def mcpl_servers() -> List[MCPLServer]:
    return [
        MCPLServer(**s) for s in MCPL_SERVERS
    ]
