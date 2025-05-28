from typing import List

from core.globals import DEFAULT_MCPL_SERVERS
from mcpl.repositories.repo_mcpl_servers import MCPLServersRepository, MCPLServer


async def get_active_servers(repo: MCPLServersRepository, user_id: int) -> List[MCPLServer]:
    servers = await repo.get_user_servers(user_id)
    default_servers = [
        MCPLServer(user_id=-1, address=s, is_active=True) for s in DEFAULT_MCPL_SERVERS
    ]
    servers.extend(default_servers)
    return [
        s for s in servers
        if s.is_active
    ]
