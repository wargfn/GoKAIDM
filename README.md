# GoKAIDM – Gates of Krystalia AI DM

AI-led TTRPG companion for **Gates of Krystalia**, built entirely in Python 3.

## Features

| Feature | Description |
|---|---|
| Campaign persistence | Save/load complete campaign state as JSON |
| Ruleset persistence | Import rules from PDF books or JSON |
| Persona persistence | Track player characters and NPCs |
| Location persistence | Track world locations and their connections |
| Solo play (primary) | Structured solo notation format journal |
| Group play | Multi-player session support built on the solo format |
| PDF resource loader | Extract rule text from PDF rulebooks via `pypdf` |
| AI Dungeon Master | Configurable AI backend (Anthropic Claude / OpenAI) |
| Image generation | MCP-based connections to Adobe Firefly **or** Gemini |

## Requirements

- Python 3.10+
- See `requirements.txt`

## Quick-start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the example config and fill in your API keys
cp config.example.json config.json

# 3. Start a new solo campaign
python main.py new-campaign "The Shattered Realm"

# 4. Open the interactive AI DM session
python main.py session --campaign "The Shattered Realm"
```

## Project layout

```
GoKAIDM/
├── main.py                  # CLI entry point
├── requirements.txt
├── config.example.json      # Template configuration
├── gokaidm/
│   ├── persistence/         # JSON-backed data stores
│   │   ├── campaign.py
│   │   ├── ruleset.py
│   │   ├── persona.py
│   │   └── location.py
│   ├── session/
│   │   ├── manager.py       # Solo & group session handling
│   │   └── notation.py      # Solo notation format
│   ├── ai/
│   │   └── dm.py            # AI Dungeon Master
│   ├── resources/
│   │   └── pdf_loader.py    # PDF → text extraction
│   └── image/
│       └── generator.py     # MCP image generation
└── tests/
```

## Solo notation format

Each session log entry follows the **Solo Oracle Notation** convention:

```
[YYYY-MM-DD HH:MM] <TYPE> | <ACTOR> | <CONTENT>
```

Types: `SCENE`, `ACTION`, `ORACLE`, `DM`, `NOTE`, `IMAGE`.

## Configuration

`config.json` keys:

```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-opus-4-5",
    "api_key_env": "ANTHROPIC_API_KEY"
  },
  "image": {
    "provider": "gemini",
    "api_key_env": "GEMINI_API_KEY"
  },
  "data_dir": "./data"
}
```

## License

MIT
