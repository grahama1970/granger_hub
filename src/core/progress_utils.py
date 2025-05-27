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


if __name__ == "__main__":
    async def test_utils():
        async with AsyncProgressTracker() as tracker:
            session_id = await tracker.create_session("SPARTA", "Marker")
            await tracker.add_progress_update(
                session_id, "SPARTA", "test_update", 0.5, "Test progress"
            )
            progress = await get_session_progress(tracker, session_id)
            assert progress["updates"][0]["progress_value"] == 0.5, f"Expected 0.5, got {progress['updates'][0]['progress_value']}"
            stats = await get_communication_stats(tracker)
            print(f"Progress: {json.dumps(progress, indent=2)}\nStats: {json.dumps(stats, indent=2)}")

    asyncio.run(test_utils())