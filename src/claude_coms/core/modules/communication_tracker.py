"""
Communication progress tracker for ModuleCommunicator.

Purpose: Provides progress tracking functionality for module communications,
including message logging, task tracking, and statistics collection.
"""

import asyncio
import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, asdict
import uuid

from loguru import logger

# Import Task from task_executor to avoid duplication
if TYPE_CHECKING:
    from ..claude_coms.task_executor import Task


class ProgressTracker:
    """Tracks progress of module communications and tasks."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the progress tracker.
        
        Args:
            db_path: Path to SQLite database (uses in-memory if None)
        """
        self.db_path = str(db_path) if db_path else ":memory:"
        self._db: Optional[aiosqlite.Connection] = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure database is initialized."""
        if not self._initialized:
            await self._initialize_db()
    
    async def _initialize_db(self):
        """Initialize the database schema."""
        self._db = await aiosqlite.connect(self.db_path)
        
        # Create tables
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                action TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                response TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                instruction TEXT NOT NULL,
                requester TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT
            )
        """)
        
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                module_count INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                task_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0
            )
        """)
        
        await self._db.commit()
        self._initialized = True
    
    async def log_message(self, source: str, target: str, action: str, data: Dict[str, Any]) -> str:
        """Log a message being sent.
        
        Args:
            source: Source module name
            target: Target module name
            action: Action being performed
            data: Message data
            
        Returns:
            Message ID
        """
        await self._ensure_initialized()
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        await self._db.execute("""
            INSERT INTO messages (id, source, target, action, data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, source, target, action, json.dumps(data), timestamp))
        
        await self._db.commit()
        logger.debug(f"Logged message {message_id}: {source} -> {target}")
        
        return message_id
    
    async def log_response(self, source: str, target: str, response: Dict[str, Any]) -> None:
        """Log a response to a message.
        
        Args:
            source: Source module name (who sent the response)
            target: Target module name (who receives the response)
            response: Response data
        """
        await self._ensure_initialized()
        
        # Find the most recent message from target to source
        cursor = await self._db.execute("""
            SELECT id FROM messages 
            WHERE source = ? AND target = ? AND response IS NULL
            ORDER BY timestamp DESC
            LIMIT 1
        """, (target, source))
        
        row = await cursor.fetchone()
        if row:
            message_id = row[0]
            await self._db.execute("""
                UPDATE messages 
                SET response = ?, status = 'completed'
                WHERE id = ?
            """, (json.dumps(response), message_id))
            await self._db.commit()
            logger.debug(f"Logged response for message {message_id}")
    
    async def log_task(self, task: 'Task') -> None:
        """Log a new task.
        
        Args:
            task: Task to log
        """
        await self._ensure_initialized()
        
        await self._db.execute("""
            INSERT INTO tasks (id, instruction, requester, task_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.instruction,
            task.requester,
            task.type,
            task.status,
            task.created_at
        ))
        
        await self._db.commit()
        logger.debug(f"Logged task {task.id}: {task.instruction[:50]}...")
    
    async def log_task_completion(self, task_id: str, result: Dict[str, Any]) -> None:
        """Log task completion.
        
        Args:
            task_id: ID of the completed task
            result: Task result
        """
        await self._ensure_initialized()
        
        completed_at = datetime.now().isoformat()
        status = "completed" if result.get("status") == "completed" else "failed"
        
        await self._db.execute("""
            UPDATE tasks
            SET status = ?, completed_at = ?, result = ?
            WHERE id = ?
        """, (status, completed_at, json.dumps(result), task_id))
        
        await self._db.commit()
        logger.debug(f"Task {task_id} completed with status: {status}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics.
        
        Returns:
            Dictionary with statistics
        """
        await self._ensure_initialized()
        
        # Message stats
        cursor = await self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM messages
        """)
        message_stats = await cursor.fetchone()
        
        # Task stats
        cursor = await self._db.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
            FROM tasks
        """)
        task_stats = await cursor.fetchone()
        
        # Module stats
        cursor = await self._db.execute("""
            SELECT COUNT(DISTINCT source) + COUNT(DISTINCT target) as module_count
            FROM messages
        """)
        module_stats = await cursor.fetchone()
        
        return {
            "messages": {
                "total": message_stats[0] or 0,
                "completed": message_stats[1] or 0,
                "failed": message_stats[2] or 0
            },
            "tasks": {
                "total": task_stats[0] or 0,
                "completed": task_stats[1] or 0,
                "failed": task_stats[2] or 0,
                "pending": task_stats[3] or 0
            },
            "modules": {
                "active": module_stats[0] or 0
            }
        }
    
    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False


# Export classes
__all__ = ['ProgressTracker']