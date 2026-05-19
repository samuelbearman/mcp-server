# python-ssh-mcp

A simple MCP server for managing and running commands via SSH on multiple servers. 

## Running 

``` shell
uv run server.py
```

## Testing

``` shell

# Via the mcp inspector tool
npx @modelcontextprotocol/inspector uv run server.py
```

## Config File 

Example config file:

``` json
{
  "connections": [
    {
      "name": "test",
      "host": "test",
      "user": "test",
      "port": "22",
      "auth": {
        "path": "~/.ssh/id_rsa",
        "type": "key"
      }
    },
    {
      "name": "test2",
      "host": "test2",
      "user": "test2",
      "port": "22",
      "auth": {
        "path": "SOME_PASSWORD", # This is really insecure. Need to fix with ENV vars or something
        "type": "pasword"
      }
    }
  ]
}
```

`config.py` acts as a CLI tool as well for adding to this file

``` shell
uv run config.py --user test --name test --host test --connection-type key --port "22"
```

## Configuring with Claude Code

For a globally aware MCP server copy below into the `~/.claude.json` file. For project use cases look at Anthropics docs.

``` json
"mcpServers": {
  "python-ssh-mcp": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "/path/to/the/server.py"],
    "env": {}
  }
},
```
