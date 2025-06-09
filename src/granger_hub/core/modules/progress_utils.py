"""
Utility Functions for Progress Tracking

Purpose: Provides helper functions for managing communication sessions and statistics.
Third-party packages:
- aiosqlite: https://aiosqlite.omnilib.dev/en/stable/
- loguru: https://loguru.readthedocs.io/en/stable/
- asyncio, json, datetime, typing: Python standard library

Sample Input:
- session_id: UUID string from AsyncProgressTracker.create_session
- module_name: "SPARTA"

Expected Output:
- Session progress (dict) with updates and status
- Communication statistics (dict) with success rate and duration
"""

import aiosqlite
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator

from loguru import logger
from .progress_tracker import AsyncProgressTracker, CommunicationStatus


async def get_session_progress(tracker: AsyncProgressTracker, session_id: str) -> Dict[str, Any]:
    """Get current progress for a session."""
    cursor = await tracker._db.execute("""
        SELECT * FROM communication_sessions WHERE session_id = ?
    """, (session_id,))
    session = await cursor.fetchone()
    if not session:
        return {"error": "Session not found"}
        
    cursor = await tracker._db.execute("""
        SELECT * FROM progress_updates 
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    """, (session_id,))
    updates = await cursor.fetchall()
    
    return {
        "session": dict(session),
        "updates": [dict(u) for u in updates],
        "is_complete": session["status"] in [
            CommunicationStatus.COMPLETED.value,
            CommunicationStatus.FAILED.value
        ]
    }
    
async def watch_session_progress(
    tracker: AsyncProgressTracker,
    session_id: str,
    poll_interval: float = 0.5
) -> AsyncGenerator[Dict[str, Any], None]:
    """Watch session progress in real-time."""
    last_update_count = 0
    while True:
        progress = await get_session_progress(tracker, session_id)
        if progress.get("is_complete"):
            yield progress
            break
        update_count = len(progress.get("updates", []))
        if update_count > last_update_count:
            yield progress
            last_update_count = update_count
        await asyncio.sleep(poll_interval)
        
async def get_active_sessions(
    tracker: AsyncProgressTracker,
    module_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all active sessions, optionally filtered by module."""
    query = """
        SELECT * FROM communication_sessions
        WHERE status NOT IN (?, ?)
    """
    params = [CommunicationStatus.COMPLETED.value, CommunicationStatus.FAILED.value]
    if module_name:
        query += " AND (source_module = ? OR target_module = ?)"
        params.extend([module_name, module_name])
    query += " ORDER BY started_at DESC"
    
    cursor = await tracker._db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
    
async def get_communication_stats(
    tracker: AsyncProgressTracker,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get communication statistics."""
    query = "SELECT * FROM communication_sessions WHERE 1=1"
    params = []
    if start_date:
        query += " AND started_at >= ?"
        params.append(start_date.isoformat())
    if end_date:
        query += " AND started_at <= ?"
        params.append(end_date.isoformat())
        
    cursor = await tracker._db.execute(query, params)
    sessions = await cursor.fetchall()
    
    total = len(sessions)
    completed = sum(1 for s in sessions if s["status"] == CommunicationStatus.COMPLETED.value)
    failed = sum(1 for s in sessions if s["status"] == CommunicationStatus.FAILED.value)
    
    durations = []
    for session in sessions:
        if session["completed_at"] and session["started_at"]:
            start = datetime.fromisoformat(session["started_at"])
            end = datetime.fromisoformat(session["completed_at"])
            durations.append((end - start).total_seconds())
            
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    return {
        "total_sessions": total,
        "completed": completed,
        "failed": failed,
        "success_rate": (completed / total * 100) if total > 0 else 0,
        "average_duration_seconds": avg_duration,
        "active_sessions": total - completed - failed
    }
    
async def cleanup_old_sessions(tracker: AsyncProgressTracker, days_old: int = 7) -> None:
    """Clean up old completed sessions."""
    cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    await tracker._db.execute("""
        DELETE FROM progress_updates
        WHERE session_id IN (
            SELECT session_id FROM communication_sessions
            WHERE status IN (?, ?)
            AND completed_at < datetime(?, 'unixepoch')
        )
    """, (
        CommunicationStatus.COMPLETED.value,
        CommunicationStatus.FAILED.value,
        cutoff_date
    ))
    await tracker._db.execute("""
        DELETE FROM communication_sessions
        WHERE status IN (?, ?)
        AND completed_at < datetime(?, 'unixepoch')
    """, (
        CommunicationStatus.COMPLETED.value,
        CommunicationStatus.FAILED.value,
        cutoff_date
    ))
    await tracker._db.commit()
    logger.info(f"Cleaned up sessions older than {days_old} days")


async def track_module_communication(
    source_module: str,
    target_module: str,
    communication_func: Any,
    tracker: Optional[AsyncProgressTracker] = None
) -> Dict[str, Any]:
    """
    Track module communication with progress updates.
    
    Args:
        source_module: Source module name
        target_module: Target module name
        communication_func: Async function to execute
        tracker: Progress tracker instance (creates new if None)
        
    Returns:
        Communication result with session ID
    """
    if not tracker:
        tracker = AsyncProgressTracker()
        await tracker.initialize()
        close_tracker = True
    else:
        close_tracker = False
        
    try:
        session_id = await tracker.create_session(source_module, target_module)
        await tracker.add_progress_update(
            session_id,
            source_module,
            "communication_started",
            message=f"Initiating communication with {target_module}"
        )
        try:
            result = await communication_func(session_id, tracker)
            await tracker.update_session_status(session_id, CommunicationStatus.COMPLETED)
            return {"success": True, "session_id": session_id, "result": result}
        except Exception as e:
            await tracker.update_session_status(
                session_id, CommunicationStatus.FAILED, error_message=str(e)
            )
            return {"success": False, "session_id": session_id, "error": str(e)}
    finally:
        if close_tracker:
            await tracker.close()


# Additional functions for test compatibility

async def init_database(db_path: str) -> None:
    """Initialize database with required tables."""
    async with aiosqlite.connect(db_path) as db:
        # Create session stats table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_stats (
                session_id TEXT PRIMARY KEY,
                files_processed INTEGER DEFAULT 0,
                errors_encountered INTEGER DEFAULT 0,
                bytes_processed INTEGER DEFAULT 0,
                modules_active TEXT,
                start_time TEXT,
                end_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create file operations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                operation_type TEXT,
                file_path TEXT,
                status TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES session_stats (session_id)
            )
        """)
        
        # Create module communications table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS module_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_module TEXT,
                target_module TEXT,
                message_type TEXT,
                status TEXT,
                metrics TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES session_stats (session_id)
            )
        """)
        
        await db.commit()


async def update_session_stats(
    db_path: str,
    session_id: str,
    files_processed: Optional[int] = None,
    errors_encountered: Optional[int] = None,
    bytes_processed: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    modules_active: Optional[List[str]] = None
) -> None:
    """Update session statistics."""
    async with aiosqlite.connect(db_path) as db:
        # Check if session exists
        cursor = await db.execute(
            "SELECT session_id FROM session_stats WHERE session_id = ?",
            (session_id,)
        )
        exists = await cursor.fetchone()
        
        if exists:
            # Update existing session
            updates = []
            params = []
            
            if files_processed is not None:
                updates.append("files_processed = ?")
                params.append(files_processed)
            if errors_encountered is not None:
                updates.append("errors_encountered = ?")
                params.append(errors_encountered)
            if bytes_processed is not None:
                updates.append("bytes_processed = ?")
                params.append(bytes_processed)
            if start_time is not None:
                updates.append("start_time = ?")
                params.append(start_time)
            if end_time is not None:
                updates.append("end_time = ?")
                params.append(end_time)
            if modules_active is not None:
                updates.append("modules_active = ?")
                params.append(json.dumps(modules_active))
            
            if updates:
                params.append(session_id)
                await db.execute(
                    f"UPDATE session_stats SET {', '.join(updates)} WHERE session_id = ?",
                    params
                )
        else:
            # Insert new session
            await db.execute("""
                INSERT INTO session_stats 
                (session_id, files_processed, errors_encountered, bytes_processed, 
                 start_time, end_time, modules_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                files_processed or 0,
                errors_encountered or 0,
                bytes_processed or 0,
                start_time,
                end_time,
                json.dumps(modules_active) if modules_active else None
            ))
        
        await db.commit()


async def get_session_statistics(db_path: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Get statistics for a session."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM session_stats WHERE session_id = ?",
            (session_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        result = dict(row)
        if result.get("modules_active"):
            result["modules_active"] = json.loads(result["modules_active"])
        
        return result


async def log_file_operation(
    db_path: str,
    session_id: str,
    operation_type: str,
    file_path: str,
    status: str,
    details: Dict[str, Any]
) -> None:
    """Log a file operation."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO file_operations 
            (session_id, operation_type, file_path, status, details, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (
            session_id,
            operation_type,
            file_path,
            status,
            json.dumps(details)
        ))
        await db.commit()


async def get_recent_file_operations(
    db_path: str,
    session_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent file operations for a session."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM file_operations 
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            result = dict(row)
            if result.get("details"):
                result["details"] = json.loads(result["details"])
            results.append(result)
        
        return results


async def get_operation_summary(db_path: str, session_id: str) -> Dict[str, Any]:
    """Get operation summary for a session."""
    async with aiosqlite.connect(db_path) as db:
        # Total operations
        cursor = await db.execute(
            "SELECT COUNT(*) FROM file_operations WHERE session_id = ?",
            (session_id,)
        )
        total_ops = (await cursor.fetchone())[0]
        
        # Successful operations
        cursor = await db.execute(
            "SELECT COUNT(*) FROM file_operations WHERE session_id = ? AND status = 'SUCCESS'",
            (session_id,)
        )
        success_ops = (await cursor.fetchone())[0]
        
        # Failed operations
        cursor = await db.execute(
            "SELECT COUNT(*) FROM file_operations WHERE session_id = ? AND status = 'FAILED'",
            (session_id,)
        )
        failed_ops = (await cursor.fetchone())[0]
        
        # Operation types
        cursor = await db.execute("""
            SELECT operation_type, COUNT(*) as count 
            FROM file_operations 
            WHERE session_id = ?
            GROUP BY operation_type
        """, (session_id,))
        
        op_types = {}
        for row in await cursor.fetchall():
            op_types[row[0]] = row[1]
        
        return {
            "total_operations": total_ops,
            "successful_operations": success_ops,
            "failed_operations": failed_ops,
            "operation_types": op_types
        }


async def cleanup_old_sessions(db_path: str, days_to_keep: int = 30) -> int:
    """Cleanup old sessions from database."""
    async with aiosqlite.connect(db_path) as db:
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        # Get sessions to delete
        cursor = await db.execute("""
            SELECT session_id FROM session_stats 
            WHERE datetime(start_time) < datetime(?, 'unixepoch')
        """, (cutoff_date,))
        
        sessions_to_delete = [row[0] for row in await cursor.fetchall()]
        
        if sessions_to_delete:
            # Delete file operations
            placeholders = ','.join('?' * len(sessions_to_delete))
            await db.execute(
                f"DELETE FROM file_operations WHERE session_id IN ({placeholders})",
                sessions_to_delete
            )
            
            # Delete module communications
            await db.execute(
                f"DELETE FROM module_communications WHERE session_id IN ({placeholders})",
                sessions_to_delete
            )
            
            # Delete sessions
            await db.execute(
                f"DELETE FROM session_stats WHERE session_id IN ({placeholders})",
                sessions_to_delete
            )
            
            await db.commit()
        
        return len(sessions_to_delete)


# Redefine track_module_communication for the new database schema
async def track_module_communication(
    db_path: str,
    session_id: str,
    source_module: str,
    target_module: str,
    message_type: str,
    status: str,
    metrics: Dict[str, Any]
) -> None:
    """Track communication between modules."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            INSERT INTO module_communications 
            (session_id, source_module, target_module, message_type, status, metrics)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            source_module,
            target_module,
            message_type,
            status,
            json.dumps(metrics)
        ))
        await db.commit()


if __name__ == "__main__":
    async def test_utils():
        # Test the new functions
        db_path = ":memory:"
        await init_database(db_path)
        
        session_id = "test_session_001"
        await update_session_stats(
            db_path=db_path,
            session_id=session_id,
            files_processed=10,
            errors_encountered=1,
            start_time=datetime.now().isoformat()
        )
        
        stats = await get_session_statistics(db_path, session_id)
        assert stats["files_processed"] == 10
        assert stats["errors_encountered"] == 1
        
        print(" All utils tests passed!")

    asyncio.run(test_utils())