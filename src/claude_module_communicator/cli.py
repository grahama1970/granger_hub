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
from .arango_expert import ArangoExpert


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


def execute_aql_query(aql: str, config_path: Optional[str] = None):
    """Execute an AQL query."""
    config = {
        "hosts": ["http://localhost:8529"],
        "database": "module_collaboration",
        "username": "root",
        "password": ""
    }
    
    if config_path:
        with open(config_path) as f:
            config = json.load(f)
    
    try:
        expert = ArangoExpert(config)
        cursor = expert.db.aql.execute(aql)
        
        results = list(cursor)
        print(f"\n📊 Query returned {len(results)} results:\n")
        
        for i, result in enumerate(results[:10]):  # Show first 10
            print(f"{i+1}. {json.dumps(result, indent=2)}")
            
        if len(results) > 10:
            print(f"\n... and {len(results) - 10} more results")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")


def analyze_graph(analysis_type: str, config_path: Optional[str] = None):
    """Analyze the module graph."""
    config = {
        "hosts": ["http://localhost:8529"],
        "database": "module_collaboration", 
        "username": "root",
        "password": ""
    }
    
    if config_path:
        with open(config_path) as f:
            config = json.load(f)
    
    try:
        expert = ArangoExpert(config)
        
        if analysis_type == "influencers":
            results = expert.find_influencers("module_graph", "communicates_with")
            print("\n🌟 Most Influential Modules:\n")
            for r in results[:10]:
                print(f"- {r['vertex']['name']}: {r['total_connections']} connections")
                
        elif analysis_type == "bridges":
            results = expert.find_bridges("module_graph", "communicates_with")
            print("\n🌉 Bridge Modules (connecting communities):\n")
            for r in results[:10]:
                print(f"- {r['vertex']['name']}: bridge score {r['bridge_score']:.2f}")
                
        elif analysis_type == "gaps":
            domain = input("Enter domain to analyze: ")
            collections = ["messages", "resources", "knowledge"]
            results = expert.find_knowledge_gaps(domain, collections)
            print(f"\n🔍 Knowledge Gaps for '{domain}':\n")
            for gap in results:
                print(f"- {gap['gap']}: {gap['coverage']*100:.1f}% coverage")
                print(f"  Recommendation: {gap['recommendation']}")
                
    except Exception as e:
        print(f"❌ Analysis failed: {e}")


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
    
    # ArangoDB query
    query_parser = subparsers.add_parser("query", help="Execute AQL query")
    query_parser.add_argument("aql", help="AQL query to execute")
    query_parser.add_argument("--arango-config", help="Path to ArangoDB config JSON")
    
    # Analyze graph
    analyze_parser = subparsers.add_parser("analyze-graph", help="Analyze module graph")
    analyze_parser.add_argument("--type", choices=["influencers", "bridges", "gaps"], 
                               help="Type of analysis")
    analyze_parser.add_argument("--arango-config", help="Path to ArangoDB config JSON")
    
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
    elif args.command == "query":
        execute_aql_query(args.aql, args.arango_config)
    elif args.command == "analyze-graph":
        analyze_graph(args.type, args.arango_config)


if __name__ == "__main__":
    main()