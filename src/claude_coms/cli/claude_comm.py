#!/usr/bin/env python3
"""
Claude Module Communicator CLI - Typer Version.

This CLI provides commands for managing inter-module communication
using Claude Code instances.

Example:
    $ cmc-cli register my_module --class MyModule
    $ cmc-cli send my_module process --data '{"items": [1, 2, 3]}'
    $ cmc-cli discover --pattern data
    $ cmc-cli execute "Process the data and send results to analyzer"
"""

import typer
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.table import Table
from rich import print

from ..core import ModuleCommunicator
from .slash_mcp_mixin import add_slash_mcp_commands

# Create console for pretty output
console = Console()

# Create Typer app
app = typer.Typer(
    name="cmc-cli",
    help="Claude Module Communicator - Orchestrate inter-module communication",
    context_settings={"help_option_names": ["-h", "--help"]}
)

# Global state for the communicator
state = {"communicator": None, "verbose": False}


def get_communicator(
    registry: Optional[Path] = None,
    progress_db: Optional[Path] = None
):
    """Get or create the module communicator instance."""
    if state["communicator"] is None:
        state["communicator"] = ModuleCommunicator(
            registry_path=registry,
            progress_db=progress_db
        )
    return state["communicator"]


@app.callback()
def main_callback(
    registry: Optional[Path] = typer.Option(None, help="Path to module registry file"),
    progress_db: Optional[Path] = typer.Option(None, help="Path to progress database"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Configure global options for the communicator."""
    state["verbose"] = verbose
    # Initialize communicator with provided options
    # Only initialize when needed


@app.command()
def register(
    name: str = typer.Argument(..., help="Module name to register"),
    module_class: str = typer.Option(..., "--class", help="Module class name"),
    schema_file: Optional[Path] = typer.Option(None, "--schema", help="Path to schema file")
):
    """Register a new module."""
    comm = get_communicator()
    
    # Load schema if provided
    schema_data = {}
    if schema_file and schema_file.exists():
        with open(schema_file, 'r') as f:
            schema_data = json.load(f)
    
    # Dynamic import of module class
    try:
        # Assume module is in current path
        module_parts = module_class.split('.')
        if len(module_parts) > 1:
            module_name = '.'.join(module_parts[:-1])
            class_name = module_parts[-1]
        else:
            module_name = '__main__'
            class_name = module_class
        
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        
        # Create instance
        instance = cls()
        
        # Register
        comm.register_module(name, instance)
        
        console.print(f"[green]✓[/green] Registered module: {name}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to register module: {e}")
        raise typer.Exit(1)


@app.command()
def discover(
    pattern: Optional[str] = typer.Option(None, "--pattern", help="Filter modules by pattern")
):
    """Discover available modules."""
    comm = get_communicator()
    
    async def _discover():
        modules = await comm.discover_modules(pattern)
        return modules
    
    modules = asyncio.run(_discover())
    
    if not modules:
        console.print("No modules found")
        return
    
    # Create table
    table = Table(title="Available Modules")
    table.add_column("Name", style="cyan")
    table.add_column("Class", style="green")
    table.add_column("Capabilities", style="yellow")
    
    for module in modules:
        caps = ", ".join(module.get('capabilities', []))
        table.add_row(
            module['name'],
            module.get('class', 'Unknown'),
            caps
        )
    
    console.print(table)


@app.command()
def send(
    target: str = typer.Argument(..., help="Target module name"),
    action: str = typer.Argument(..., help="Action to perform"),
    data: Optional[str] = typer.Option(None, "--data", help="JSON data to send"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds")
):
    """Send a message to a target module."""
    comm = get_communicator()
    
    # Parse data if provided
    payload = {}
    if data:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON data")
            raise typer.Exit(1)
    
    async def _send():
        result = await comm.send_message(target, action, payload, timeout=timeout)
        return result
    
    try:
        result = asyncio.run(_send())
        
        if result.success:
            console.print(f"[green]✓[/green] Message sent successfully")
            if state["verbose"] and result.data:
                console.print("Response:")
                print(result.data)
        else:
            console.print(f"[red]✗[/red] Failed: {result.error}")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def execute(
    instruction: str = typer.Argument(..., help="Natural language instruction"),
    requester: Optional[str] = typer.Option(None, help="Requester module name"),
    task_type: Optional[str] = typer.Option(None, help="Task type hint"),
    params_file: Optional[Path] = typer.Option(None, "--params", help="JSON parameters file")
):
    """Execute a natural language instruction."""
    comm = get_communicator()
    
    # Load params if provided
    params = {}
    if params_file and params_file.exists():
        with open(params_file, 'r') as f:
            params = json.load(f)
    
    async def _execute():
        result = await comm.execute_instruction(
            instruction, 
            requester=requester,
            task_type=task_type,
            parameters=params
        )
        return result
    
    try:
        console.print(f"[yellow]Executing:[/yellow] {instruction}")
        result = asyncio.run(_execute())
        
        if result['success']:
            console.print("[green]✓[/green] Execution completed")
            console.print(f"Module used: {result.get('module', 'Unknown')}")
            if state["verbose"] and result.get('result'):
                console.print("Result:")
                print(result['result'])
        else:
            console.print(f"[red]✗[/red] Execution failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def broadcast(
    action: str = typer.Argument(..., help="Action to broadcast"),
    data: Optional[str] = typer.Option(None, "--data", help="JSON data to broadcast"),
    pattern: Optional[str] = typer.Option(None, "--pattern", help="Filter modules by pattern")
):
    """Broadcast a message to multiple modules."""
    comm = get_communicator()
    
    # Parse data if provided
    payload = {}
    if data:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            console.print("[red]Error:[/red] Invalid JSON data")
            raise typer.Exit(1)
    
    async def _broadcast():
        results = await comm.broadcast_message(action, payload, pattern=pattern)
        return results
    
    try:
        results = asyncio.run(_broadcast())
        
        console.print(f"[yellow]Broadcast results:[/yellow]")
        for module, result in results.items():
            if result.get('success'):
                console.print(f"  [green]✓[/green] {module}")
            else:
                console.print(f"  [red]✗[/red] {module}: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def graph():
    """Display the module dependency graph."""
    comm = get_communicator()
    
    async def _graph():
        graph_data = await comm.get_dependency_graph()
        return graph_data
    
    graph_data = asyncio.run(_graph())
    
    if not graph_data:
        console.print("No modules registered")
        return
    
    console.print("[cyan]Module Dependency Graph:[/cyan]")
    console.print("")
    
    for module, deps in graph_data.items():
        console.print(f"[green]{module}[/green]")
        if deps:
            for dep in deps:
                console.print(f"  → {dep}")
        else:
            console.print("  (no dependencies)")
        console.print("")


@app.command(name="check-compat")
def check_compatibility(
    source: str = typer.Argument(..., help="Source module name"),
    target: str = typer.Argument(..., help="Target module name")
):
    """Check compatibility between two modules."""
    comm = get_communicator()
    
    async def _check():
        compat = await comm.check_compatibility(source, target)
        return compat
    
    try:
        compat = asyncio.run(_check())
        
        console.print(f"[cyan]Compatibility check:[/cyan] {source} → {target}")
        console.print("")
        
        if compat['compatible']:
            console.print("[green]✓ Modules are compatible[/green]")
        else:
            console.print("[red]✗ Modules are not compatible[/red]")
            console.print(f"Reason: {compat.get('reason', 'Unknown')}")
            
        if state["verbose"] and compat.get('details'):
            console.print("\nDetails:")
            print(compat['details'])
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def progress(
    session_id: Optional[str] = typer.Option(None, "--session", help="Filter by session ID"),
    tail: int = typer.Option(10, "--tail", help="Number of recent entries to show")
):
    """Display communication progress."""
    comm = get_communicator()
    
    async def _progress():
        progress_data = await comm.get_progress(session_id=session_id, limit=tail)
        return progress_data
    
    progress_data = asyncio.run(_progress())
    
    if not progress_data:
        console.print("No progress data available")
        return
    
    # Create table
    table = Table(title="Communication Progress")
    table.add_column("Time", style="cyan")
    table.add_column("Session", style="green")
    table.add_column("Source", style="yellow")
    table.add_column("Target", style="yellow")
    table.add_column("Status", style="magenta")
    
    for entry in progress_data:
        table.add_row(
            entry.get('timestamp', 'Unknown'),
            entry.get('session_id', 'N/A'),
            entry.get('source', 'N/A'),
            entry.get('target', 'N/A'),
            entry.get('status', 'Unknown')
        )
    
    console.print(table)


@app.command()
def screenshot(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
    region: str = typer.Option("full", "--region", "-r", help="Screen region (full, left-half, right-half, etc.)"),
    quality: int = typer.Option(70, "--quality", "-q", help="JPEG quality (30-90)"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to capture instead of screen"),
    wait: int = typer.Option(3, "--wait", "-w", help="Wait seconds for dynamic content (URL only)"),
    describe: bool = typer.Option(False, "--describe", "-d", help="Get AI description of the screenshot"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Custom prompt for description")
):
    """Capture a screenshot and optionally describe it."""
    from ..core.modules import ScreenshotModule
    
    async def _capture_screenshot():
        # Create screenshot module
        module = ScreenshotModule()
        
        # Prepare capture data
        capture_data = {
            "action": "capture",
            "region": region,
            "quality": quality
        }
        
        if output:
            capture_data["output"] = output
        if url:
            capture_data["url"] = url
            capture_data["wait"] = wait
        
        # Capture screenshot
        console.print(f"[yellow]Capturing screenshot...[/yellow]")
        result = await module.process(capture_data)
        
        if not result.get("success"):
            console.print(f"[red]✗[/red] Screenshot failed: {result.get('error', 'Unknown error')}")
            return None
        
        file_path = result.get("result", {}).get("file")
        console.print(f"[green]✓[/green] Screenshot saved: {file_path}")
        
        # Optionally describe
        if describe and file_path:
            console.print(f"[yellow]Getting AI description...[/yellow]")
            desc_data = {
                "action": "describe",
                "file": file_path
            }
            if prompt:
                desc_data["prompt"] = prompt
            
            desc_result = await module.process(desc_data)
            
            if desc_result.get("success"):
                description = desc_result.get("result", {}).get("description", "No description available")
                console.print(f"\n[cyan]Description:[/cyan]\n{description}")
            else:
                console.print(f"[yellow]⚠[/yellow]  Could not describe image: {desc_result.get('error', 'Unknown error')}")
        
        return file_path
    
    try:
        file_path = asyncio.run(_capture_screenshot())
        if file_path and state["verbose"]:
            console.print(f"\nFull path: {file_path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def browser(
    action: str = typer.Argument(..., help="Browser action (navigate, click, fill, screenshot)"),
    url: Optional[str] = typer.Option(None, "--url", "-u", help="URL to navigate to"),
    selector: Optional[str] = typer.Option(None, "--selector", "-s", help="CSS selector for element"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Value for fill action"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path for screenshots"),
    headless: bool = typer.Option(True, "--headless/--headed", help="Run browser in headless mode"),
    timeout: int = typer.Option(30000, "--timeout", "-t", help="Timeout in milliseconds")
):
    """Perform browser automation actions."""
    from ..core.modules import BrowserAutomationModule
    
    async def _browser_action():
        # Create browser module
        module = BrowserAutomationModule()
        await module.start()
        
        try:
            # Prepare action data
            action_data = {
                "action": action,
                "headless": headless,
                "timeout": timeout
            }
            
            # Add parameters based on action
            if action == "navigate":
                if not url:
                    console.print("[red]Error:[/red] URL is required for navigate action")
                    return None
                action_data["url"] = url
                
            elif action in ["click", "fill", "hover"]:
                if not selector:
                    console.print("[red]Error:[/red] Selector is required for {action} action")
                    return None
                action_data["selector"] = selector
                if action == "fill":
                    action_data["value"] = value or ""
                    
            elif action == "screenshot":
                if output:
                    action_data["output_path"] = output
                if selector:
                    action_data["selector"] = selector
            
            # Execute action
            console.print(f"[yellow]Executing browser action: {action}...[/yellow]")
            result = await module.process(action_data)
            
            if result.get("success"):
                console.print(f"[green]✓[/green] Action completed successfully")
                if state["verbose"]:
                    console.print("Result:")
                    print(result.get("result", {}))
                return result.get("result")
            else:
                console.print(f"[red]✗[/red] Action failed: {result.get('error', 'Unknown error')}")
                return None
                
        finally:
            await module.stop()
    
    try:
        result = asyncio.run(_browser_action())
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command(name="test-browser")
def test_browser(
    url: str = typer.Argument(..., help="URL to test"),
    instruction: Optional[str] = typer.Option("Test this website thoroughly", "--instruction", "-i", help="Test instruction for Claude"),
    scenario: Optional[Path] = typer.Option(None, "--scenario", "-s", help="Path to test scenario file (JSON)"),
    output_dir: Optional[Path] = typer.Option("./test_results", "--output", "-o", help="Output directory for results"),
    headless: bool = typer.Option(True, "--headless/--headed", help="Run browser in headless mode"),
    focus: Optional[List[str]] = typer.Option(None, "--focus", "-f", help="Focus areas for testing (can be used multiple times)"),
    quick: bool = typer.Option(False, "--quick", "-q", help="Run quick test (page structure and accessibility only)")
):
    """Let Claude intelligently test a website."""
    from ..core.modules import BrowserTestModule
    
    async def _test_browser():
        # Create test module
        module = BrowserTestModule()
        await module.start()
        
        try:
            # Prepare test data
            if scenario:
                # Load scenario from file
                if not scenario.exists():
                    console.print(f"[red]Error:[/red] Scenario file not found: {scenario}")
                    return None
                    
                console.print(f"[yellow]Loading test scenario from {scenario}...[/yellow]")
                result = await module.process({
                    "action": "test_scenario",
                    "url": url,
                    "scenario_file": str(scenario),
                    "output_dir": str(output_dir),
                    "headless": headless
                })
            elif quick:
                # Quick test mode
                console.print(f"[yellow]Running quick test on {url}...[/yellow]")
                result = await module.process({
                    "action": "test_page",
                    "url": url,
                    "output_dir": str(output_dir),
                    "headless": headless
                })
            else:
                # Claude intelligent test mode
                console.print(f"[yellow]Claude is testing {url}...[/yellow]")
                console.print(f"[cyan]Instruction:[/cyan] {instruction}")
                if focus:
                    console.print(f"[cyan]Focus areas:[/cyan] {', '.join(focus)}")
                
                result = await module.process({
                    "action": "claude_test",
                    "url": url,
                    "instruction": instruction,
                    "focus_areas": focus or [],
                    "output_dir": str(output_dir),
                    "headless": headless
                })
            
            if result and result.get("success"):
                console.print(f"\n[green]✓[/green] Test completed successfully!")
                console.print(f"[green]Passed:[/green] {result.get('passed', 0)}")
                console.print(f"[red]Failed:[/red] {result.get('failed', 0)}")
                
                if result.get("claude_summary"):
                    console.print(f"\n[cyan]Claude's Summary:[/cyan]\n{result['claude_summary']}")
                
                if result.get("report_path"):
                    console.print(f"\n[yellow]Report saved to:[/yellow] {result['report_path']}")
                    console.print(f"Open the report to see detailed results with screenshots.")
                
                return result
            else:
                error = result.get("error", "Unknown error") if result else "Test module failed to start"
                console.print(f"[red]✗[/red] Test failed: {error}")
                return None
                
        finally:
            await module.stop()
    
    try:
        result = asyncio.run(_test_browser())
        if not result:
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def pdf(
    file: Path = typer.Argument(..., help="Path to PDF file"),
    page: int = typer.Option(1, "--page", "-p", help="Page number to navigate to"),
    extract_tables: bool = typer.Option(False, "--tables", "-t", help="Extract tables from page"),
    annotate: bool = typer.Option(False, "--annotate", "-a", help="Annotate tables in screenshot"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for screenshots")
):
    """Navigate PDF pages, take screenshots, and extract tables."""
    from ..core.modules import PDFNavigatorModule
    
    console.print(f"[cyan]PDF Navigator[/cyan] - Processing {file}")
    
    if not file.exists():
        console.print(f"[red]Error:[/red] PDF file not found: {file}")
        raise typer.Exit(1)
    
    async def _process_pdf():
        module = PDFNavigatorModule()
        
        # If output directory specified, change working directory
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            import os
            os.chdir(output_dir)
        
        try:
            result = await module.process({
                "action": "navigate",
                "file": str(file.absolute()),
                "page": page,
                "extract_tables": extract_tables,
                "annotate": annotate
            })
            
            if result.get("success"):
                console.print(f"[green]✓[/green] Successfully navigated to page {page}")
                console.print(f"[green]Screenshot saved:[/green] {result['screenshot']}")
                
                if result.get("tables"):
                    console.print(f"\n[cyan]Found {len(result['tables'])} table(s):[/cyan]")
                    for i, table in enumerate(result['tables']):
                        console.print(f"\n[yellow]Table {i+1}:[/yellow] {table.get('title', 'Untitled')}")
                        if table.get('location'):
                            console.print(f"  Location: {table['location']}")
                        if table.get('headers'):
                            console.print(f"  Headers: {', '.join(table['headers'])}")
                        if table.get('rows'):
                            console.print(f"  Rows: {len(table['rows'])}")
                
                if result.get("annotated_screenshot"):
                    console.print(f"\n[green]Annotated screenshot:[/green] {result['annotated_screenshot']}")
                
                # If tables were extracted, save them as JSON
                if extract_tables and result.get("tables"):
                    import json
                    table_file = Path(result['screenshot']).with_suffix('.json')
                    with open(table_file, 'w') as f:
                        json.dump({
                            "page": page,
                            "tables": result['tables'],
                            "page_context": result.get("page_context", "")
                        }, f, indent=2)
                    console.print(f"\n[green]Table data saved:[/green] {table_file}")
                
            else:
                console.print(f"[red]✗[/red] Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    try:
        asyncio.run(_process_pdf())
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print("[cyan]Claude Module Communicator CLI[/cyan]")
    console.print("Version: 0.4.0")
    console.print("Orchestrate inter-module communication with ease!")


@app.command()
def health():
    """Check system health."""
    comm = get_communicator()
    
    console.print("[cyan]System Health Check[/cyan]")
    console.print("")
    
    # Check registry
    if comm.registry:
        console.print("[green]✓[/green] Module registry initialized")
    else:
        console.print("[yellow]⚠[/yellow]  No module registry")
    
    # Check progress DB
    if comm.progress_tracker:
        console.print("[green]✓[/green] Progress tracking enabled")
    else:
        console.print("[yellow]⚠[/yellow]  Progress tracking disabled")
    
    # Check registered modules
    module_count = len(comm.modules) if hasattr(comm, 'modules') else 0
    if module_count > 0:
        console.print(f"[green]✓[/green] {module_count} modules registered")
    else:
        console.print("[yellow]⚠[/yellow]  No modules registered")


# Add slash command and MCP generation capabilities
add_slash_mcp_commands(app, command_prefix="generate")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == '__main__':
    main()
