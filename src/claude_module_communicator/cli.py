#!/usr/bin/env python3
"""
CLI utilities for claude-module-communicator
"""

import json
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from . import ModuleCommunicator


def list_messages(target: Optional[str] = None, db_path: str = "~/.sparta/module_comm.db"):
    """List all messages or messages for a specific target."""
    db_path = Path(db_path).expanduser()
    
    if not db_path.exists():
        print(f"No database found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    
    if target:
        query = "SELECT * FROM messages WHERE target = ? ORDER BY timestamp DESC"
        cursor = conn.execute(query, (target,))
    else:
        query = "SELECT * FROM messages ORDER BY timestamp DESC"
        cursor = conn.execute(query)
    
    messages = cursor.fetchall()
    conn.close()
    
    if not messages:
        print(f"No messages found{' for ' + target if target else ''}")
        return
    
    print(f"\n📥 Found {len(messages)} message(s){' for ' + target if target else ''}:\n")
    
    for msg in messages:
        msg_id, source, target, content, timestamp = msg
        try:
            data = json.loads(content)
            msg_type = data.get('type', 'unknown')
            purpose = data.get('purpose', 'N/A')
        except:
            msg_type = 'raw'
            purpose = content[:50] + '...' if len(content) > 50 else content
        
        print(f"ID: {msg_id}")
        print(f"From: {source} → To: {target}")
        print(f"Time: {timestamp}")
        print(f"Type: {msg_type}")
        print(f"Purpose: {purpose}")
        print("-" * 60)


def show_message(msg_id: int, db_path: str = "~/.sparta/module_comm.db"):
    """Show full content of a specific message."""
    db_path = Path(db_path).expanduser()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    msg = cursor.fetchone()
    conn.close()
    
    if not msg:
        print(f"Message {msg_id} not found")
        return
    
    msg_id, source, target, content, timestamp = msg
    
    print(f"\n📧 Message {msg_id}")
    print(f"From: {source} → To: {target}")
    print(f"Time: {timestamp}")
    print("\n" + "="*60 + "\n")
    
    try:
        data = json.loads(content)
        print(json.dumps(data, indent=2))
    except:
        print(content)


def list_progress(module: Optional[str] = None, db_path: str = "~/.sparta/module_comm.db"):
    """List progress entries."""
    db_path = Path(db_path).expanduser()
    
    if not db_path.exists():
        print(f"No database found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    
    if module:
        query = "SELECT * FROM progress WHERE module = ? ORDER BY timestamp DESC"
        cursor = conn.execute(query, (module,))
    else:
        query = "SELECT * FROM progress ORDER BY timestamp DESC"
        cursor = conn.execute(query)
    
    progress_entries = cursor.fetchall()
    conn.close()
    
    if not progress_entries:
        print(f"No progress entries found{' for ' + module if module else ''}")
        return
    
    print(f"\n📊 Found {len(progress_entries)} progress entries{' for ' + module if module else ''}:\n")
    
    for entry in progress_entries:
        entry_id, module, task, completed, total, timestamp = entry
        percentage = (completed / total * 100) if total > 0 else 0
        
        print(f"Module: {module}")
        print(f"Task: {task}")
        print(f"Progress: {completed}/{total} ({percentage:.1f}%)")
        print(f"Time: {timestamp}")
        print("-" * 60)


def send_message(source: str, target: str, message: str, msg_type: str = "text", 
                db_path: str = "~/.sparta/module_comm.db"):
    """Send a message from CLI."""
    comm = ModuleCommunicator(source, db_path=db_path)
    
    data = {
        "type": msg_type,
        "timestamp": datetime.now().isoformat(),
        "message": message
    }
    
    msg_id = comm.send_message(source, target, data)
    print(f"✅ Message sent! ID: {msg_id}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Claude Module Communicator CLI")
    parser.add_argument("--db", default="~/.sparta/module_comm.db", 
                       help="Database path (default: ~/.sparta/module_comm.db)")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List messages
    list_parser = subparsers.add_parser("list", help="List messages")
    list_parser.add_argument("--target", help="Filter by target module")
    
    # Show message
    show_parser = subparsers.add_parser("show", help="Show message details")
    show_parser.add_argument("id", type=int, help="Message ID")
    
    # List progress
    progress_parser = subparsers.add_parser("progress", help="List progress entries")
    progress_parser.add_argument("--module", help="Filter by module")
    
    # Send message
    send_parser = subparsers.add_parser("send", help="Send a message")
    send_parser.add_argument("source", help="Source module")
    send_parser.add_argument("target", help="Target module")
    send_parser.add_argument("message", help="Message content")
    send_parser.add_argument("--type", default="text", help="Message type")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "list":
        list_messages(args.target, args.db)
    elif args.command == "show":
        show_message(args.id, args.db)
    elif args.command == "progress":
        list_progress(args.module, args.db)
    elif args.command == "send":
        send_message(args.source, args.target, args.message, args.type, args.db)


if __name__ == "__main__":
    main()