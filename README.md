# GoKAIDM – Gates of Krystalia AI DM

AI-led TTRPG companion for **Gates of Krystalia**, built entirely in Python 3.

This project contains all of the files necessary for AI to track between sessions, including being able to startup in and continue running.

Gates of Krystalia is a Table Top Role Playing Isekai based game by Andrea Ruggeri and published by Top Nothc International LTD.

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
| AI Dungeon Master | Configurable AI backend (GitHub Copilot / Anthropic Claude / OpenAI) |
| Image generation | MCP-based connections to Adobe Firefly **or** Gemini |

## Requirements

- Python 3.11+
- See `requirements.txt`

## Quick-start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the example config
cp config.example.json config.json

# 3. Authenticate with GitHub (skip if already signed in)
gh auth login

# 4. Start a new solo campaign
python main.py new-campaign "The Shattered Realm"

# 5. Open the interactive AI DM session
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
    "provider": "copilot",
    "model": "auto",
    "api_key_env": ""
  },
  "image": {
    "provider": "gemini",
    "api_key_env": "GEMINI_API_KEY"
  },
  "data_dir": "./data"
}
```

The Copilot provider uses stored Copilot or GitHub CLI credentials. You can
alternatively set `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, or `GITHUB_TOKEN`.
Anthropic and OpenAI providers continue to use the environment variable named by
`api_key_env`.

## License

MIT
