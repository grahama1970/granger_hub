"""
CLI Conversation Commands for Granger Hub

Purpose: Provides Typer-based CLI commands for managing multi-turn conversations
between modules with support for MCP generation via slash_mcp_mixin.

Third-party packages:
- typer: https://typer.tiangolo.com/
- rich: https://rich.readthedocs.io/en/stable/

Sample Input:
- Command: conversation start "planning-session" DataProducerModule OrchestratorModule
- Data: {"project": "Q4 Planning", "participants": ["Alice", "Bob"]}

Expected Output:
- Conversation ID and status updates
- Real-time message flow between modules
"""

import typer
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.columns import Columns

from ..core.conversation.conversation_manager import ConversationManager
from ..core.conversation.conversation_message import ConversationMessage
from ..core.modules import ModuleRegistry

# Create the conversation commands app
app = typer.Typer(name="conversation", help="Multi-turn conversation management")
console = Console()


@app.command("start")
def start_conversation(
    conversation_id: str = typer.Argument(..., help="Unique conversation identifier"),
    source_module: str = typer.Argument(..., help="Source module name"),
    target_module: str = typer.Argument(..., help="Target module name"),
    initial_message: str = typer.Option("Hello, let's start our conversation", help="Initial message content"),
    data_file: Optional[Path] = typer.Option(None, "--data", help="JSON file with additional data")
):
    """Start a new conversation between two modules."""
    # Load additional data if provided
    additional_data = {}
    if data_file and data_file.exists():
        with open(data_file) as f:
            additional_data = json.load(f)
    
    async def _start():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # Create initial message
        message = ConversationMessage.create(
            source=source_module,
            target=target_module,
            msg_type="start_conversation",
            content=initial_message,
            conversation_id=conversation_id,
            data=additional_data
        )
        
        # Start the conversation
        result = await manager.start_conversation(conversation_id, [source_module, target_module])
        
        if result:
            # Route the initial message
            response = await manager.route_message(message)
            return result, response
        return None, None
    
    try:
        result, response = asyncio.run(_start())
        
        if result:
            console.print(f"[green]✓[/green] Conversation started: {conversation_id}")
            console.print(f"Participants: {source_module} ↔ {target_module}")
            if response:
                console.print(f"Initial response: {response}")
        else:
            console.print(f"[red]✗[/red] Failed to start conversation")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("send")
def send_message(
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    source: str = typer.Argument(..., help="Source module"),
    target: str = typer.Argument(..., help="Target module"),
    content: str = typer.Argument(..., help="Message content"),
    msg_type: str = typer.Option("conversation_turn", help="Message type"),
    data_file: Optional[Path] = typer.Option(None, "--data", help="JSON file with additional data")
):
    """Send a message in an existing conversation."""
    # Load additional data if provided
    additional_data = {}
    if data_file and data_file.exists():
        with open(data_file) as f:
            additional_data = json.load(f)
    
    async def _send():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # Create message
        message = ConversationMessage.create(
            source=source,
            target=target,
            msg_type=msg_type,
            content=content,
            conversation_id=conversation_id,
            data=additional_data
        )
        
        # Route the message
        response = await manager.route_message(message)
        return response
    
    try:
        response = asyncio.run(_send())
        
        if response:
            console.print(f"[green]✓[/green] Message sent")
            console.print(f"Response: {response}")
        else:
            console.print(f"[red]✗[/red] Failed to send message")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_conversations(
    active_only: bool = typer.Option(False, "--active", help="Show only active conversations"),
    limit: int = typer.Option(10, "--limit", help="Number of conversations to show")
):
    """List all conversations."""
    async def _list():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # Get all conversations
        conversations = []
        for conv_id, conv in manager.conversations.items():
            status = "Active" if conv.is_active else "Completed"
            conversations.append({
                "id": conv_id,
                "participants": list(conv.participants),
                "status": status,
                "message_count": conv.message_count,
                "created": conv.created_at.isoformat() if hasattr(conv, 'created_at') else "Unknown"
            })
        
        # Filter if needed
        if active_only:
            conversations = [c for c in conversations if c["status"] == "Active"]
        
        return conversations[:limit]
    
    try:
        conversations = asyncio.run(_list())
        
        if not conversations:
            console.print("No conversations found")
            return
        
        # Create table
        table = Table(title="Conversations")
        table.add_column("ID", style="cyan")
        table.add_column("Participants", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Messages", style="magenta")
        table.add_column("Created", style="blue")
        
        for conv in conversations:
            participants = " ↔ ".join(conv["participants"])
            table.add_row(
                conv["id"],
                participants,
                conv["status"],
                str(conv["message_count"]),
                conv["created"]
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("history")
def show_history(
    conversation_id: str = typer.Argument(..., help="Conversation ID"),
    limit: int = typer.Option(20, "--limit", help="Number of messages to show"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, or chat")
):
    """Show conversation history."""
    async def _history():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # Get conversation
        conv = manager.conversations.get(conversation_id)
        if not conv:
            return None
        
        # Get history
        messages = conv.get_history(limit=limit)
        return messages
    
    try:
        messages = asyncio.run(_history())
        
        if not messages:
            console.print(f"No conversation found with ID: {conversation_id}")
            return
        
        if format == "json":
            # JSON format
            json_data = [msg.to_dict() for msg in messages]
            console.print_json(data=json_data)
            
        elif format == "chat":
            # Chat format
            for msg in messages:
                timestamp = msg.timestamp.strftime("%H:%M:%S")
                console.print(f"[dim]{timestamp}[/dim] [bold]{msg.source}[/bold] → [bold]{msg.target}[/bold]")
                console.print(f"  {msg.content}")
                if msg.data:
                    console.print(f"  [dim]Data: {json.dumps(msg.data, indent=2)}[/dim]")
                console.print()
                
        else:
            # Table format (default)
            table = Table(title=f"Conversation History: {conversation_id}")
            table.add_column("Time", style="cyan")
            table.add_column("Source", style="green")
            table.add_column("Target", style="yellow")
            table.add_column("Type", style="magenta")
            table.add_column("Content", style="white", overflow="fold")
            
            for msg in messages:
                table.add_row(
                    msg.timestamp.strftime("%H:%M:%S"),
                    msg.source,
                    msg.target,
                    msg.msg_type,
                    msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("end")
def end_conversation(
    conversation_id: str = typer.Argument(..., help="Conversation ID to end"),
    reason: str = typer.Option("Normal completion", "--reason", help="Reason for ending")
):
    """End an active conversation."""
    async def _end():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # End the conversation
        result = await manager.end_conversation(conversation_id, reason)
        return result
    
    try:
        result = asyncio.run(_end())
        
        if result:
            console.print(f"[green]✓[/green] Conversation ended: {conversation_id}")
            console.print(f"Reason: {reason}")
        else:
            console.print(f"[red]✗[/red] Failed to end conversation")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command("monitor")
def monitor_conversation(
    conversation_id: str = typer.Argument(..., help="Conversation ID to monitor"),
    refresh_rate: int = typer.Option(2, "--refresh", help="Refresh rate in seconds")
):
    """Monitor a conversation in real-time."""
    console.print(f"[yellow]Monitoring conversation: {conversation_id}[/yellow]")
    console.print(f"Refresh rate: {refresh_rate}s")
    console.print("[dim]Press Ctrl+C to stop monitoring[/dim]")
    
    # In a real implementation, this would connect to the conversation
    # and display real-time updates
    console.print("\n[red]Real-time monitoring not yet implemented[/red]")


@app.command("export")
def export_conversation(
    conversation_id: str = typer.Argument(..., help="Conversation ID to export"),
    output_file: Path = typer.Argument(..., help="Output file path"),
    format: str = typer.Option("json", "--format", help="Export format: json or markdown")
):
    """Export a conversation to a file."""
    async def _export():
        registry = ModuleRegistry()
        manager = ConversationManager(registry)
        
        # Get conversation
        conv = manager.conversations.get(conversation_id)
        if not conv:
            return None
        
        # Get all messages
        messages = conv.get_history()
        
        if format == "markdown":
            # Export as markdown
            content = f"# Conversation: {conversation_id}\n\n"
            content += f"**Participants:** {', '.join(conv.participants)}\n"
            content += f"**Status:** {'Active' if conv.is_active else 'Completed'}\n"
            content += f"**Messages:** {conv.message_count}\n\n"
            content += "## History\n\n"
            
            for msg in messages:
                content += f"### {msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                content += f"**{msg.source}** → **{msg.target}** ({msg.msg_type})\n\n"
                content += f"{msg.content}\n\n"
                if msg.data:
                    content += f"```json\n{json.dumps(msg.data, indent=2)}\n```\n\n"
            
            return content
            
        else:
            # Export as JSON
            data = {
                "conversation_id": conversation_id,
                "participants": list(conv.participants),
                "status": "active" if conv.is_active else "completed",
                "message_count": conv.message_count,
                "messages": [msg.to_dict() for msg in messages]
            }
            return json.dumps(data, indent=2, default=str)
    
    try:
        content = asyncio.run(_export())
        
        if content is None:
            console.print(f"[red]Conversation not found: {conversation_id}[/red]")
            raise typer.Exit(1)
        
        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content)
        
        console.print(f"[green]✓[/green] Exported conversation to: {output_file}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()