import json
import logging
import sys
import uuid
from typing import Any

import asyncssh
from fastmcp import FastMCP

from config import KeyAuth, load_config

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

WRITE_COMMANDS = {
    "rm",
    "rmdir",
    "mv",
    "cp",
    "mkdir",
    "touch",
    "chmod",
    "chown",
    "chgrp",
    "ln",
    "truncate",
    "dd",
    "tee",
    "install",
    "mkfs",
    "fdisk",
    "parted",
    "mkswap",
    "systemctl",
    "service",
    "initctl",
    "apt",
    "apt-get",
    "yum",
    "dnf",
    "pacman",
    "brew",
    "snap",
    "pip",
    "npm",
    "yarn",
    "cargo",
    "useradd",
    "userdel",
    "usermod",
    "groupadd",
    "groupdel",
    "passwd",
    "chpasswd",
    "mount",
    "umount",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "kill",
    "killall",
    "pkill",
    "iptables",
    "ip6tables",
    "ufw",
    "firewall-cmd",
    "crontab",
    "sed",
    "awk",
}

config = load_config()
sessions: dict[str, asyncssh.SSHClientConnection] = {}

mcp = FastMCP(
    "python-ssh-mcp",
    instructions=(
        "SSH MCP Server — manage SSH connections to pre-configured servers.\n"
        "Tools:\n"
        "- list_connections: show all configured servers\n"
        "- open_session(connection_name): connect and get a session_id\n"
        "- run_read_command(session_id, command): safe read-only commands\n"
        "- run_write_command(session_id, command): state-changing commands (requires approval)\n"
        "- close_session(session_id): disconnect"
    ),
)


def check_read_command(command: str) -> None:
    parts = command.split()
    first = parts[0] if parts else ""
    base = first.rsplit("/", 1)[-1]
    if base in WRITE_COMMANDS:
        raise ValueError(f"'{base}' is a write operation use run_write_command instead")
    if " > " in command or " >> " in command:
        raise ValueError(
            "Command contains output redirection use run_write_command instead"
        )


async def ssh_connect(name: str) -> asyncssh.SSHClientConnection:
    conn = next((c for c in config.connections if c.name == name), None)
    if conn is None:
        raise ValueError(f"No connection named '{name}' in config")
    kwargs: dict[str, Any] = {
        "host": conn.host,
        "port": conn.port,
        "username": conn.user,
        "known_hosts": None,
    }
    if isinstance(conn.auth, KeyAuth):
        kwargs["client_keys"] = [conn.auth.path]
    else:
        kwargs["password"] = conn.auth.password
    return await asyncssh.connect(**kwargs)


async def exec_command(session_id: str, command: str) -> str:
    connection = sessions.get(session_id)
    if connection is None:
        raise ValueError(f"No active session '{session_id}'")
    result = await connection.run(command, check=False)
    return json.dumps(
        {
            "exit_code": result.exit_status,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )


@mcp.tool(description="List all SSH connections defined in the config file")
async def list_connections() -> str:
    infos = []
    for c in config.connections:
        infos.append({"name": c.name, "host": c.host, "user": c.user, "port": c.port})
    return json.dumps(infos, indent=2)


@mcp.tool(
    description=(
        "Open an SSH session to a named connection from the config. "
        "Returns a session_id for use with other commands."
    )
)
async def open_session(
    connection_name: str,
) -> str:
    connection = await ssh_connect(connection_name)
    session_id = str(uuid.uuid4())
    sessions[session_id] = connection
    logger.info("Opened session %s for connection '%s'", session_id, connection_name)
    return session_id


@mcp.tool(description="Close an active SSH session")
async def close_session(
    session_id: str,
) -> str:
    connection = sessions.pop(session_id, None)
    if connection is None:
        raise ValueError(f"No active session '{session_id}'")
    connection.close()
    logger.info("Closed session %s", session_id)
    return "Session closed"


@mcp.tool(
    description="Run a read-only SSH command (ls, cat, grep, ps, df, etc.) on an active session"
)
async def run_read_command(
    session_id: str,
    command: str,
) -> str:
    check_read_command(command)
    return await exec_command(session_id, command)


@mcp.tool(
    description=(
        "Run a write SSH command that modifies system state "
        "(rm, mv, systemctl, apt, etc.) on an active session. "
        "Requires explicit user approval."
    )
)
async def run_write_command(
    session_id: str,
    command: str,
) -> str:
    return await exec_command(session_id, command)


def main() -> None:
    logger.info("Loaded %d connection(s) from config", len(config.connections))
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
