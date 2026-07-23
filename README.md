# GoKAIDM
Gates of Krystalia AI DM instance for Solo Games.

## Firefly MCP Server

GoKAIDM ships an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that
exposes Adobe Firefly image generation as a tool.  An AI host (e.g. Claude Desktop) can call
`generate_image` to create scene illustrations, character portraits, or any other artwork for
the game on the fly.

### Prerequisites

1. An [Adobe Developer Console](https://developer.adobe.com/console/) account with a project
   that has **Firefly API** OAuth Server-to-Server credentials.
2. [Go 1.25+](https://go.dev/dl/) installed.

### Building

```bash
go build -o GoKAIDM .
```

### Running

```bash
export FIREFLY_CLIENT_ID=<your_client_id>
export FIREFLY_CLIENT_SECRET=<your_client_secret>
./GoKAIDM
```

The server communicates over **stdio** (stdin / stdout), which is the standard transport for
MCP hosts.

### Claude Desktop configuration

Add the following block to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gokaidm-firefly": {
      "command": "/path/to/GoKAIDM",
      "env": {
        "FIREFLY_CLIENT_ID": "your_client_id",
        "FIREFLY_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

### Available tools

#### `generate_image`

Generates one or more images from a text description using Adobe Firefly v3.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | ✅ | Text description of the desired image. |
| `negative_prompt` | string | | Things to exclude from the image. |
| `num_variations` | number | | Number of variants to generate (1–4). Default: `1`. |
| `content_class` | string | | `"photo"` or `"art"`. Default: `"photo"`. |
| `width` | number | | Image width in pixels. Default: `1024`. |
| `height` | number | | Image height in pixels. Default: `1024`. |
| `style_presets` | string | | Comma-separated Firefly style presets, e.g. `"photo,studio_shot"`. |
| `style_strength` | number | | How strongly presets are applied (1–100). Default: `60`. |
| `seed` | number | | Seed to reproduce a specific result. |

Returns a JSON array of objects, each containing `seed`, `url`, and `presigned_url`.
