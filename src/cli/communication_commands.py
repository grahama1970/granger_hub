"""
CLI Communication Commands for SPARTA

Purpose: Extends SPARTA CLI with commands for module communication, including schema negotiation and pipeline validation.
Third-party packages:
- typer: https://typer.tiangolo.com/
- rich: https://rich.readthedocs.io/en/stable/
- aiosqlite: https://aiosqlite.omnilib.dev/en/stable/
- asyncio, json, pathlib, typing, datetime: Python standard library

Sample Input:
- Command: comm negotiate SPARTA Marker --sample sample.json
- sample.json: {"file_id": "123", "path": "/data/file.pdf"}

Expected Output:
- Negotiated schema (JSON) displayed in console
- Progress updates in SQLite database (~/.sparta/progress.db)
"""

import typer
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import asyncio

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.live import Live
from rich.columns import Columns

from claude_module_communicator.module_communicator import ModuleCommunicator
from claude_module_communicator.schema_negotiator_dynamic import DynamicSchemaNegotiator
from claude_module_communicator.progress_tracker import AsyncProgressTracker, CommunicationStatus
from claude_module_communicator.progress_utils import track_module_communication


comm_app = typer.Typer(name="comm", help="Inter-module communication commands")
console = Console()


@comm_app.command("negotiate")
def negotiate_schema(
    source: str = typer.Argument(..., help="Source module name"),
    target: str = typer.Argument(..., help="Target module name"),
    sample_file: Path = typer.Option(..., "--sample", "-s", help="Sample data JSON file"),
    requirements: Optional[List[str]] = typer.Option(None, "--req", "-r", help="Specific requirements"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch progress in real-time"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save schema to file")
):
    """Negotiate schema between two modules."""
    async def negotiate_with_progress(session_id: str, tracker: AsyncProgressTracker) -> Dict[str, Any]:
        if not sample_file.exists():
            console.print(f"[red]Sample file not found: {sample_file}[/red]")
            raise typer.Exit(1)
        with open(sample_file) as f:
            sample_data = json.load(f)
            
        negotiator = DynamicSchemaNegotiator(source)
        await tracker.update_session_status(session_id, CommunicationStatus.NEGOTIATING)
        await tracker.add_progress_update(
            session_id, source, "negotiation_started", 0.0, "Starting schema negotiation"
        )
        schema = await negotiator.negotiate_schema(target, sample_data, requirements)
        schema_id = await tracker.save_negotiated_schema(source, target, schema)
        await tracker.update_session_status(
            session_id, CommunicationStatus.SCHEMA_AGREED, schema_negotiated=schema
        )
        return schema
    
    async def run_negotiation():
        async with AsyncProgressTracker() as tracker:
            session_id = await tracker.create_session(source, target)
            console.print(f"[green]Session ID:[/green] {session_id}")
            if watch:
                negotiate_task = asyncio.create_task(
                    track_module_communication(source, target, negotiate_with_progress, tracker)
                )
                with Live(console=console, refresh_per_second=2) as live:
                    async for progress in tracker.watch_session_progress(session_id):
                        table = Table(title=f"Schema Negotiation: {source} → {target}")
                        table.add_column("Time", style="cyan")
                        table.add_column("Module", style="magenta")
                        table.add_column("Event", style="yellow")
                        table.add_column("Message")
                        for update in progress["updates"]:
                            time = datetime.fromisoformat(update["created_at"]).strftime("%H:%M:%S")
                            table.add_row(
                                time, update["module_name"], update["progress_type"], update["message"] or ""
                            )
                        status_color = {
                            "completed": "green", "failed": "red", "negotiating": "yellow"
                        }.get(progress["session"]["status"], "white")
                        status_panel = Panel(
                            f"Status: [{status_color}]{progress['session']['status']}[/{status_color}]",
                            title="Current Status"
                        )
                        live.update(Columns([table, status_panel]))
                result = await negotiate_task
            else:
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                    task = progress.add_task("Negotiating schema...", total=None)
                    result = await track_module_communication(source, target, negotiate_with_progress, tracker)
                    progress.update(task, completed=True)
            
            if result["success"]:
                schema = result["result"]
                console.print("\n[green]✓ Schema negotiated![/green]")
                console.print(Panel(json.dumps(schema, indent=2), title="Negotiated Schema"))
                if output:
                    output.write_text(json.dumps(schema, indent=2))
                    console.print(f"\n[green]Schema saved to:[/green] {output}")
            else:
                console.print(f"\n[red]✗ Negotiation failed: {result['error']}[/red]")

    asyncio.run(run_negotiation())


@comm_app.command("verify")
def verify_compatibility(
    source: str = typer.Argument(..., help="Source module name"),
    target: str = typer.Argument(..., help="Target module name"),
    format_file: Path = typer.Option(..., "--format", "-f", help="Data format JSON file"),
    use_cached: bool = typer.Option(True, "--cached/--no-cached", help="Use cached schema if available")
):
    """Verify data format compatibility between modules."""
    async def run_verify():
        if not format_file.exists():
            console.print(f"[red]Format file not found: {format_file}[/red]")
            raise typer.Exit(1)
        with open(format_file) as f:
            format_data = json.load(f)
            
        async with AsyncProgressTracker() as tracker:
            if use_cached:
                cached_schema = await tracker.get_active_schema(source, target)
                if cached_schema:
                    console.print(f"[blue]Using cached schema v{cached_schema['version']}[/blue]")
                    
            session_id = await tracker.create_session(source, target)
            communicator = ModuleCommunicator(source)
            await tracker.add_progress_update(
                session_id, source, "compatibility_check", message="Checking format compatibility"
            )
            result = await communicator.verify_compatibility(target, format_data)
            
            if result.get("compatible"):
                await tracker.update_session_status(session_id, CommunicationStatus.COMPLETED)
                console.print("\n[green]✓ Format is compatible![/green]")
            else:
                await tracker.update_session_status(
                    session_id, CommunicationStatus.FAILED, error_message="Incompatible format"
                )
                console.print("\n[red]✗ Format is incompatible![/red]")
                
            table = Table(title="Compatibility Check Results")
            table.add_column("Check", style="cyan")
            table.add_column("Result", style="green" if result.get("compatible") else "red")
            table.add_row("Overall Compatible", "✓" if result.get("compatible") else "✗")
            table.add_row("Has All Fields", "✓" if result.get("has_all_fields") else "✗")
            table.add_row("Types Correct", "✓" if result.get("types_correct") else "✗")
            table.add_row("Has Issues", "✗" if result.get("has_issues") else "✓")
            console.print(table)
    
    asyncio.run(run_verify())


@comm_app.command("pipeline")
def check_pipeline(
    modules: List[str] = typer.Argument(..., help="List of modules in pipeline order"),
    test_data: Optional[Path] = typer.Option(None, "--test", "-t", help="Test data to validate pipeline"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed results")
):
    """Check entire pipeline compatibility."""
    async def run_pipeline_check():
        async with AsyncProgressTracker() as tracker:
            results = []
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
                for i in range(len(modules) - 1):
                    source, target = modules[i], modules[i + 1]
                    task = progress.add_task(f"Checking {source} → {target}...", total=None)
                    session_id = await tracker.create_session(source, target)
                    negotiator = DynamicSchemaNegotiator(source)
                    cached_schema = await tracker.get_active_schema(source, target)
                    
                    if cached_schema:
                        compatible = True
                        details = f"Using cached schema v{cached_schema['version']}"
                    else:
                        sample_data = {"test": "data"}
                        if test_data and test_data.exists():
                            with open(test_data) as f:
                                sample_data = json.load(f)
                        try:
                            schema = await negotiator.negotiate_schema(target, sample_data)
                            await tracker.save_negotiated_schema(source, target, schema)
                            compatible = True
                            details = "Schema negotiated successfully"
                        except Exception as e:
                            compatible = False
                            details = str(e)
                            
                    await tracker.update_session_status(
                        session_id, CommunicationStatus.COMPLETED if compatible else CommunicationStatus.FAILED
                    )
                    results.append({"connection": f"{source} → {target}", "compatible": compatible, "details": details})
                    progress.update(task, completed=True)
                    
            console.print("\n[bold]Pipeline Compatibility Check[/bold]\n")
            all_compatible = all(r["compatible"] for r in results)
            console.print("[green]✓ All compatible![/green]\n" if all_compatible else "[red]✗ Issues found![/red]\n")
            
            table = Table(title="Connection Status")
            table.add_column("Connection", style="cyan")
            table.add_column("Status", justify="center")
            if detailed:
                table.add_column("Details")
                
            for result in results:
                status = "[green]✓[/green]" if result["compatible"] else "[red]✗[/red]"
                row = [result["connection"], status]
                if detailed:
                    row.append(result["details"])
                table.add_row(*row)
                
            console.print(table)
            stats = await tracker.get_communication_stats()
            console.print(f"\n[blue]Total Sessions:[/blue] {stats['total_sessions']}")
            console.print(f"[blue]Success Rate:[/blue] {stats['success_rate']:.1f}%")
    
    asyncio.run(run_pipeline_check())


@comm_app.command("status")
def communication_status(
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Filter by module name"),
    active_only: bool = typer.Option(False, "--active", "-a", help="Show only active sessions"),
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Show specific session details")
):
    """Show communication status and active sessions."""
    async def run_status():
        async with AsyncProgressTracker() as tracker:
            if session_id:
                progress = await tracker.get_session_progress(session_id)
                if "error" in progress:
                    console.print(f"[red]{progress['error']}[/red]")
                    raise typer.Exit(1)
                    
                session = progress["session"]
                console.print(Panel(f"Session: {session_id}", title="Session Details"))
                info_table = Table(show_header=False)
                info_table.add_column("Field", style="cyan")
                info_table.add_column("Value")
                info_table.add_row("Source", session["source_module"])
                info_table.add_row("Target", session["target_module"])
                info_table.add_row("Status", session["status"])
                info_table.add_row("Started", session["started_at"])
                if session["completed_at"]:
                    info_table.add_row("Completed", session["completed_at"])
                if session["error_message"]:
                    info_table.add_row("Error", session["error_message"])
                console.print(info_table)
                
                if progress["updates"]:
                    console.print("\n[bold]Progress Updates:[/bold]")
                    updates_table = Table()
                    updates_table.add_column("Time", style="cyan")
                    updates_table.add_column("Module")
                    updates_table.add_column("Type")
                    updates_table.add_column("Message")
                    for update in progress["updates"]:
                        time = datetime.fromisoformat(update["created_at"]).strftime("%H:%M:%S")
                        updates_table.add_row(
                            time, update["module_name"], update["progress_type"], update["message"] or ""
                        )
                    console.print(updates_table)
            else:
                if active_only:
                    sessions = await tracker.get_active_sessions(module)
                    title = "Active Communication Sessions"
                else:
                    query = "SELECT * FROM communication_sessions"
                    params = []
                    if module:
                        query += " WHERE source_module = ? OR target_module = ?"
                        params = [module, module]
                    query += " ORDER BY started_at DESC LIMIT 20"
                    cursor = await tracker._db.execute(query, params)
                    sessions = [dict(row) for row in await cursor.fetchall()]
                    title = "Recent Communication Sessions"
                    
                if not sessions:
                    console.print("[yellow]No sessions found[/yellow]")
                    return
                    
                table = Table(title=title)
                table.add_column("Session ID", style="cyan", no_wrap=True)
                table.add_column("Source", style="magenta")
                table.add_column("Target", style="magenta")
                table.add_column("Status")
                table.add_column("Started")
                table.add_column("Duration")
                
                for session in sessions:
                    start = datetime.fromisoformat(session["started_at"])
                    duration = str(datetime.fromisoformat(session["completed_at"]) - start).split('.')[0] if session["completed_at"] else "In Progress"
                    status_color = {
                        CommunicationStatus.COMPLETED.value: "green",
                        CommunicationStatus.FAILED.value: "red",
                        CommunicationStatus.NEGOTIATING.value: "yellow"
                    }.get(session["status"], "white")
                    table.add_row(
                        session["session_id"][:8] + "...",
                        session["source_module"],
                        session["target_module"],
                        f"[{status_color}]{session['status']}[/{status_color}]",
                        start.strftime("%Y-%m-%d %H:%M:%S"),
                        duration
                    )
                    
                console.print(table)
                stats = await tracker.get_communication_stats()
                console.print(f"\n[blue]Summary:[/blue]")
                console.print(f"  Total: {stats['total_sessions']}")
                console.print(f"  Active: {stats['active_sessions']}")
                console.print(f"  Success Rate: {stats['success_rate']:.1f}%")
                console.print(f"  Avg Duration: {stats['average_duration_seconds']:.1f}s")
    
    asyncio.run(run_status())


@comm_app.command("watch")
def watch_session(
    session_id: str = typer.Argument(..., help="Session ID to watch"),
    follow: bool = typer.Option(True, "--follow/--no-follow", "-f/-F", help="Follow progress updates")
):
    """Watch a communication session in real-time."""
    async def run_watch():
        async with AsyncProgressTracker() as tracker:
            if follow:
                console.print(f"[green]Watching session:[/green] {session_id}")
                console.print("[dim]Press Ctrl+C to stop[/dim]\n")
                try:
                    async for progress in tracker.watch_session_progress(session_id):
                        console.clear()
                        session = progress["session"]
                        console.print(Panel(
                            f"Session: {session_id}\n"
                            f"Status: {session['status']}\n"
                            f"{session['source_module']} → {session['target_module']}",
                            title="Live Session Monitor"
                        ))
                        if progress["updates"]:
                            table = Table(title="Progress Updates")
                            table.add_column("Time", style="cyan")
                            table.add_column("Module")
                            table.add_column("Event")
                            table.add_column("Progress")
                            table.add_column("Message")
                            for update in progress["updates"][:10]:
                                time = datetime.fromisoformat(update["created_at"]).strftime("%H:%M:%S")
                                progress_val = f"{update['progress_value']:.0%}" if update["progress_value"] else "-"
                                table.add_row(
                                    time, update["module_name"], update["progress_type"], progress_val, update["message"] or ""
                                )
                            console.print(table)
                        if progress["is_complete"]:
                            console.print(f"\n[green]Session completed![/green]")
                            break
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopped watching[/yellow]")
            else:
                progress = await tracker.get_session_progress(session_id)
                if "error" in progress:
                    console.print(f"[red]{progress['error']}[/red]")
                else:
                    console.print(json.dumps(progress, indent=2))
    
    asyncio.run(run_watch())


def add_communication_commands(app: typer.Typer) -> typer.Typer:
    """Add communication commands to the main SPARTA CLI app."""
    app.add_typer(comm_app, name="comm", help="Module communication commands")
    from sparta_mcp_server.cli.slash_mcp_mixin import add_slash_mcp_commands
    add_slash_mcp_commands(
        comm_app,
        command_prefix="comm",
        output_dir=".claude/commands/communication"
    )
    return app


if __name__ == "__main__":
    async def test_commands():
        sample_data = {"file_id": "123", "path": "/data/file.pdf"}
        with open("test_sample.json", "w") as f:
            json.dump(sample_data, f)
        async with AsyncProgressTracker() as tracker:
            session_id = await tracker.create_session("SPARTA", "Marker")
            negotiator = DynamicSchemaNegotiator("SPARTA")
            schema = await negotiator.negotiate_schema("Marker", sample_data)
            await tracker.save_negotiated_schema("SPARTA", "Marker", schema)
            retrieved = await tracker.get_active_schema("SPARTA", "Marker")
            assert retrieved["schema"] == schema, f"Expected {schema}, got {retrieved['schema']}"
            console.print(f"Schema: {json.dumps(schema, indent=2)}")
        Path("test_sample.json").unlink()

    asyncio.run(test_commands())