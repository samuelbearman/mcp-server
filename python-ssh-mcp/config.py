import argparse
import getpass
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class KeyAuth:
    path: str
    type: str = "key"


@dataclass
class PasswordAuth:
    password: str
    type: str = "password"


AuthConfig = KeyAuth | PasswordAuth


@dataclass
class ConnectionConfig:
    name: str
    host: str
    user: str
    port: int
    auth: AuthConfig


@dataclass
class Config:
    connections: list[ConnectionConfig]


def get_config_path() -> Path:
    config_dir = Path.home() / ".config/python-ssh-mcp/config.json"
    return config_dir


def load_config() -> Config:
    config_file = get_config_path()
    data = json.loads(config_file.read_text())
    connections = []
    for c in data["connections"]:
        auth_data = c["auth"]
        if auth_data["type"] == "key":
            key_path = auth_data["path"]
            if key_path.startswith("~/"):
                key_path = str(Path.home() / key_path[2:])
            auth: AuthConfig = KeyAuth(path=key_path)
        elif auth_data["type"] == "password":
            password = auth_data["password"]
            if password.startswith("$"):
                password = os.environ[password[1:]]
            auth = PasswordAuth(password=password)
        else:
            raise ValueError(f"Unknown auth type: {auth_data['type']}")
        connections.append(
            ConnectionConfig(
                name=c["name"],
                host=c["host"],
                user=c["user"],
                port=c.get("port", 22),
                auth=auth,
            )
        )
    return Config(connections=connections)


def add_new_config(connection: ConnectionConfig) -> bool:
    config_file = get_config_path()
    config_data = json.loads(config_file.read_text())

    for conn in config_data["connections"]:
        if conn["name"] == connection.name:
            logger.error(f"Connection with name '{connection.name}' already exists")
            return False

    config_data["connections"].append(asdict(connection))
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    return True


def config_main():
    parser = argparse.ArgumentParser(
        description="Configuration tool for adding SSH connection to the python-ssh-mcp server"
    )

    parser.add_argument(
        "--name", required=True, type=str, help="Name of the connection"
    )
    parser.add_argument(
        "--host", required=True, type=str, help="IP address or name of host"
    )
    parser.add_argument("--user", required=True, type=str, help="User to connect as")
    parser.add_argument("--port", required=True, type=str, help="SSH Port")
    parser.add_argument(
        "--connection-type",
        required=True,
        type=str,
        choices=["key", "password"],
        help="Authentication method (pey or password)",
    )

    args = parser.parse_args()

    if args.connection_type == "password":
        password = getpass.getpass("Enter password for connection")
        new_connection = ConnectionConfig(
            name=args.name,
            user=args.user,
            host=args.host,
            port=args.port,
            auth=PasswordAuth(password=password),
        )
        add_new_config(new_connection)

        return
    if args.connection_type == "key":
        new_connection = ConnectionConfig(
            name=args.name,
            user=args.user,
            host=args.host,
            port=args.port,
            auth=KeyAuth(path="~/.ssh/id_rsa"),
        )
        add_new_config(new_connection)

        return


if __name__ == "__main__":
    config_main()
