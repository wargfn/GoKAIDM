"""
GoKAIDM – Gates of Krystalia AI DM
CLI entry point.

Usage examples
--------------
python main.py new-campaign "The Shattered Realm"
python main.py list-campaigns
python main.py new-persona --campaign <id> --name "Aria" --class Ranger
python main.py new-location --campaign <id> --name "Ironveil Keep"
python main.py session --campaign <id>
python main.py import-pdf --ruleset <id> rulebook.pdf
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Ensure repo root is on path when running directly
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from gokaidm.config import load_config
from gokaidm.persistence import (
    CampaignStore,
    RulesetStore,
    PersonaStore,
    LocationStore,
    Campaign,
    Ruleset,
    Persona,
    Location,
)
from gokaidm.session.manager import SessionStore, SessionManager
from gokaidm.session.notation import EntryType
from gokaidm.ai.dm import AIDungeonMaster
from gokaidm.image.generator import ImageGenerator

console = Console()


def _get_stores(config: dict) -> tuple[CampaignStore, RulesetStore, PersonaStore, LocationStore, SessionStore]:
    data_dir = config.get("data_dir", "./data")
    return (
        CampaignStore(data_dir),
        RulesetStore(data_dir),
        PersonaStore(data_dir),
        LocationStore(data_dir),
        SessionStore(data_dir),
    )


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--config", "config_path", default="config.json", help="Path to config.json")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """Gates of Krystalia AI DM – TTRPG campaign manager."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)


# ---------------------------------------------------------------------------
# Campaign commands
# ---------------------------------------------------------------------------


@cli.command("new-campaign")
@click.argument("name")
@click.option("--description", "-d", default="", help="Campaign description")
@click.pass_context
def new_campaign(ctx: click.Context, name: str, description: str) -> None:
    """Create a new campaign."""
    config = ctx.obj["config"]
    campaign_store, ruleset_store, _, _, _ = _get_stores(config)

    # Create a default ruleset for this campaign
    ruleset = Ruleset(name=f"{name} Ruleset")
    ruleset_store.save(ruleset)

    campaign = Campaign(name=name, description=description, ruleset_id=ruleset.id)
    campaign_store.save(campaign)

    console.print(Panel(
        f"[bold green]Campaign created![/bold green]\n"
        f"Name: {campaign.name}\n"
        f"ID:   {campaign.id}\n"
        f"Ruleset ID: {ruleset.id}",
        title="New Campaign",
    ))


@cli.command("list-campaigns")
@click.pass_context
def list_campaigns(ctx: click.Context) -> None:
    """List all campaigns."""
    config = ctx.obj["config"]
    campaign_store, _, _, _, _ = _get_stores(config)
    campaigns = campaign_store.list_all()

    if not campaigns:
        console.print("[yellow]No campaigns found.[/yellow]")
        return

    table = Table(title="Campaigns", show_lines=True)
    table.add_column("ID", style="dim", width=36)
    table.add_column("Name", style="bold")
    table.add_column("Sessions")
    table.add_column("Created")

    for c in campaigns:
        table.add_row(c.id, c.name, str(len(c.session_ids)), c.created_at[:10])

    console.print(table)


@cli.command("show-campaign")
@click.argument("campaign_id")
@click.pass_context
def show_campaign(ctx: click.Context, campaign_id: str) -> None:
    """Show details of a campaign."""
    config = ctx.obj["config"]
    campaign_store, _, _, _, _ = _get_stores(config)
    try:
        c = campaign_store.load(campaign_id)
    except FileNotFoundError:
        c = campaign_store.load_by_name(campaign_id)

    console.print(Panel(
        f"[bold]{c.name}[/bold]\n\n"
        f"{c.description or '(no description)'}\n\n"
        f"ID: {c.id}\n"
        f"Ruleset: {c.ruleset_id or '(none)'}\n"
        f"Personas: {len(c.persona_ids)}\n"
        f"Locations: {len(c.location_ids)}\n"
        f"Sessions: {len(c.session_ids)}\n"
        f"Active quests: {[q['title'] for q in c.quests if q.get('status') == 'active']}",
        title="Campaign Details",
    ))


# ---------------------------------------------------------------------------
# Persona commands
# ---------------------------------------------------------------------------


@cli.command("new-persona")
@click.option("--campaign", "campaign_id", required=True, help="Campaign ID or name")
@click.option("--name", required=True, help="Character name")
@click.option("--class", "char_class", default="Adventurer", help="Character class")
@click.option("--race", default="Human", help="Character race")
@click.option("--type", "persona_type", default="pc", help="pc | npc | creature")
@click.option("--backstory", default="", help="Character backstory")
@click.pass_context
def new_persona(
    ctx: click.Context,
    campaign_id: str,
    name: str,
    char_class: str,
    race: str,
    persona_type: str,
    backstory: str,
) -> None:
    """Create a new persona (PC or NPC) for a campaign."""
    config = ctx.obj["config"]
    campaign_store, _, persona_store, _, _ = _get_stores(config)

    try:
        campaign = campaign_store.load(campaign_id)
    except FileNotFoundError:
        campaign = campaign_store.load_by_name(campaign_id)

    persona = Persona(
        name=name,
        character_class=char_class,
        race=race,
        persona_type=persona_type,
        backstory=backstory,
        campaign_id=campaign.id,
    )
    persona_store.save(persona)

    # Link persona to campaign
    if persona.id not in campaign.persona_ids:
        campaign.persona_ids.append(persona.id)
    if not campaign.active_persona_id and persona_type == "pc":
        campaign.active_persona_id = persona.id
    campaign_store.save(campaign)

    console.print(Panel(
        f"[bold green]Persona created![/bold green]\n"
        f"Name:  {persona.name}\n"
        f"Class: {persona.character_class}\n"
        f"Race:  {persona.race}\n"
        f"ID:    {persona.id}",
        title="New Persona",
    ))


@cli.command("list-personas")
@click.option("--campaign", "campaign_id", default=None, help="Filter by campaign ID")
@click.pass_context
def list_personas(ctx: click.Context, campaign_id: str | None) -> None:
    """List personas, optionally filtered by campaign."""
    config = ctx.obj["config"]
    _, _, persona_store, _, _ = _get_stores(config)
    personas = persona_store.list_all(campaign_id=campaign_id)

    if not personas:
        console.print("[yellow]No personas found.[/yellow]")
        return

    table = Table(title="Personas", show_lines=True)
    table.add_column("ID", style="dim", width=36)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Class")
    table.add_column("Level")
    table.add_column("HP")

    for p in personas:
        table.add_row(
            p.id, p.name, p.persona_type, p.character_class,
            str(p.level), f"{p.hit_points_current}/{p.hit_points_max}",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Location commands
# ---------------------------------------------------------------------------


@cli.command("new-location")
@click.option("--campaign", "campaign_id", required=True, help="Campaign ID or name")
@click.option("--name", required=True, help="Location name")
@click.option("--type", "location_type", default="settlement", help="Location type")
@click.option("--region", default="", help="Region / area name")
@click.option("--description", "-d", default="", help="Location description")
@click.pass_context
def new_location(
    ctx: click.Context,
    campaign_id: str,
    name: str,
    location_type: str,
    region: str,
    description: str,
) -> None:
    """Create a new location for a campaign."""
    config = ctx.obj["config"]
    campaign_store, _, _, location_store, _ = _get_stores(config)

    try:
        campaign = campaign_store.load(campaign_id)
    except FileNotFoundError:
        campaign = campaign_store.load_by_name(campaign_id)

    location = Location(
        name=name,
        location_type=location_type,
        region=region,
        description=description,
        campaign_id=campaign.id,
    )
    location_store.save(location)

    if location.id not in campaign.location_ids:
        campaign.location_ids.append(location.id)
    if not campaign.active_location_id:
        campaign.active_location_id = location.id
    campaign_store.save(campaign)

    console.print(Panel(
        f"[bold green]Location created![/bold green]\n"
        f"Name:   {location.name}\n"
        f"Type:   {location.location_type}\n"
        f"Region: {location.region or '—'}\n"
        f"ID:     {location.id}",
        title="New Location",
    ))


@cli.command("list-locations")
@click.option("--campaign", "campaign_id", default=None, help="Filter by campaign ID")
@click.pass_context
def list_locations(ctx: click.Context, campaign_id: str | None) -> None:
    """List locations, optionally filtered by campaign."""
    config = ctx.obj["config"]
    _, _, _, location_store, _ = _get_stores(config)
    locations = location_store.list_all(campaign_id=campaign_id)

    if not locations:
        console.print("[yellow]No locations found.[/yellow]")
        return

    table = Table(title="Locations", show_lines=True)
    table.add_column("ID", style="dim", width=36)
    table.add_column("Name", style="bold")
    table.add_column("Type")
    table.add_column("Region")
    table.add_column("Explored")

    for l in locations:
        table.add_row(l.id, l.name, l.location_type, l.region, "✓" if l.explored else "✗")

    console.print(table)


# ---------------------------------------------------------------------------
# Ruleset commands
# ---------------------------------------------------------------------------


@cli.command("import-pdf")
@click.argument("pdf_path")
@click.option("--ruleset", "ruleset_id", default=None, help="Ruleset ID to add entries to")
@click.option("--category", default="general", help="Category label for imported entries")
@click.option("--pages", default=None, help="Page range to import, e.g. '1-50'")
@click.pass_context
def import_pdf(
    ctx: click.Context,
    pdf_path: str,
    ruleset_id: str | None,
    category: str,
    pages: str | None,
) -> None:
    """Import rules / lore from a PDF into a Ruleset."""
    from gokaidm.resources.pdf_loader import PDFLoader

    config = ctx.obj["config"]
    _, ruleset_store, _, _, _ = _get_stores(config)

    # Resolve or create ruleset
    if ruleset_id:
        ruleset = ruleset_store.load(ruleset_id)
    else:
        ruleset = Ruleset(name=Path(pdf_path).stem)
        ruleset_store.save(ruleset)
        console.print(f"[yellow]Created new ruleset: {ruleset.name} ({ruleset.id})[/yellow]")

    page_range = None
    if pages:
        parts = pages.split("-")
        page_range = (int(parts[0]), int(parts[1]) if len(parts) > 1 else int(parts[0]))

    console.print(f"Loading PDF: [bold]{pdf_path}[/bold] ...")
    loader = PDFLoader(pdf_path)
    loader.load(page_range)
    entries = loader.to_ruleset_entries(category=category)

    for entry in entries:
        ruleset.entries.append({**entry, "id": str(uuid.uuid4()), "tags": []})

    ruleset_store.save(ruleset)
    console.print(f"[green]Imported {len(entries)} entries into ruleset '{ruleset.name}'.[/green]")


# ---------------------------------------------------------------------------
# Session command (interactive AI DM)
# ---------------------------------------------------------------------------


@cli.command("session")
@click.option("--campaign", "campaign_id", required=True, help="Campaign ID or name")
@click.option("--resume", "resume_id", default=None, help="Resume a session by ID")
@click.option("--group", is_flag=True, default=False, help="Group play session")
@click.pass_context
def session(
    ctx: click.Context,
    campaign_id: str,
    resume_id: str | None,
    group: bool,
) -> None:
    """Start or resume an interactive AI DM session."""
    config = ctx.obj["config"]
    campaign_store, ruleset_store, persona_store, location_store, session_store = _get_stores(config)

    # Load campaign
    try:
        campaign = campaign_store.load(campaign_id)
    except FileNotFoundError:
        campaign = campaign_store.load_by_name(campaign_id)

    # Load supporting objects
    ruleset = None
    if campaign.ruleset_id:
        try:
            ruleset = ruleset_store.load(campaign.ruleset_id)
        except FileNotFoundError:
            pass

    persona = None
    if campaign.active_persona_id:
        try:
            persona = persona_store.load(campaign.active_persona_id)
        except FileNotFoundError:
            pass

    location = None
    if campaign.active_location_id:
        try:
            location = location_store.load(campaign.active_location_id)
        except FileNotFoundError:
            pass

    # Initialise AI DM
    dm = AIDungeonMaster(config)
    dm.load_context(campaign=campaign, location=location, persona=persona, ruleset=ruleset)
    image_gen = ImageGenerator(config)

    # Start / resume session
    mgr = SessionManager(session_store)
    session_type = "group" if group else "solo"

    if resume_id:
        current_session = mgr.resume_session(resume_id)
        console.print(f"[cyan]Resuming session: {current_session.title}[/cyan]")
    else:
        existing = session_store.list_all(campaign_id=campaign.id)
        session_num = len(existing) + 1
        current_session = mgr.start_session(
            campaign_id=campaign.id,
            title=f"Session {session_num}",
            session_type=session_type,
            session_number=session_num,
        )
        console.print(Panel(
            f"[bold green]Session {session_num} started[/bold green]\n"
            f"Campaign: {campaign.name}\n"
            f"Type: {session_type.upper()}\n"
            f"Session ID: {current_session.id}",
            title="GoKAIDM",
        ))

        # Opening narration
        opening = dm.describe_scene(
            location.name if location else "an unknown location",
            atmosphere=location.atmosphere if location else "",
        )
        mgr.append_entry(EntryType.DM, opening, actor="AI DM")
        console.print(Panel(Markdown(opening), title="[bold cyan]AI DM[/bold cyan]"))

    # Add session ID to campaign
    if current_session.id not in campaign.session_ids:
        campaign.session_ids.append(current_session.id)
        campaign_store.save(campaign)

    # Interactive loop
    console.print(
        "\n[dim]Commands: [bold]q[/bold]=quit  [bold]note[/bold]=add note  "
        "[bold]image[/bold]=generate image  [bold]oracle[/bold]=ask oracle  "
        "[bold]log[/bold]=show log[/dim]\n"
    )

    while True:
        try:
            user_input = console.input("[bold yellow]> [/bold yellow]").strip()
        except (EOFError, KeyboardInterrupt):
            user_input = "q"

        if not user_input:
            continue

        lower = user_input.lower()

        # --- quit ---
        if lower in ("q", "quit", "exit"):
            summary = dm.summarise_session(mgr.get_active_log())
            ended = mgr.end_session(summary)
            console.print(Panel(
                f"[bold]Session ended.[/bold]\n\n{summary}",
                title="Session Summary",
            ))
            break

        # --- show log ---
        elif lower == "log":
            console.print(Panel(mgr.get_log_text(), title="Session Log"))

        # --- add note ---
        elif lower.startswith("note "):
            note_text = user_input[5:].strip()
            mgr.append_entry(EntryType.NOTE, note_text, actor="Player")
            console.print(f"[dim]Note added.[/dim]")

        # --- oracle ---
        elif lower.startswith("oracle "):
            question = user_input[7:].strip()
            mgr.append_entry(EntryType.ORACLE, question, actor="Player")
            answer = dm.roll_oracle(question)
            mgr.append_entry(EntryType.DM, answer, actor="Oracle")
            console.print(Panel(answer, title="[bold magenta]Oracle[/bold magenta]"))

        # --- image generation ---
        elif lower.startswith("image "):
            img_prompt = user_input[6:].strip()
            console.print("[dim]Generating image...[/dim]")
            result = image_gen.generate(img_prompt)
            if result.available:
                save_path = Path(config.get("data_dir", "./data")) / "images" / f"{current_session.id}_scene.png"
                result.save(save_path)
                mgr.append_entry(EntryType.IMAGE, str(save_path), actor="AI DM", metadata={"prompt": img_prompt})
                console.print(f"[green]Image saved to {save_path}[/green]")
            else:
                console.print("[yellow]Image generation unavailable (no API key configured).[/yellow]")

        # --- default: player action → AI DM narration ---
        else:
            mgr.append_entry(EntryType.ACTION, user_input, actor=persona.name if persona else "Player")
            response = dm.narrate(user_input)
            mgr.append_entry(EntryType.DM, response, actor="AI DM")
            console.print(Panel(Markdown(response), title="[bold cyan]AI DM[/bold cyan]"))


# ---------------------------------------------------------------------------
# Image generation command
# ---------------------------------------------------------------------------


@cli.command("generate-image")
@click.argument("prompt")
@click.option("--output", "-o", default=None, help="Output file path")
@click.pass_context
def generate_image(ctx: click.Context, prompt: str, output: str | None) -> None:
    """Generate a standalone image from a text prompt."""
    config = ctx.obj["config"]
    generator = ImageGenerator(config)
    result = generator.generate(prompt)

    if result.available:
        out_path = output or Path(config.get("data_dir", "./data")) / "images" / "generated.png"
        result.save(out_path)
        console.print(f"[green]Image saved to {out_path}[/green]")
    else:
        console.print("[yellow]Image generation unavailable (no API key configured).[/yellow]")
        console.print(f"[dim]Prompt: {result.prompt}[/dim]")


if __name__ == "__main__":
    cli()
