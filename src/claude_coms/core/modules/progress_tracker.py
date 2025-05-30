"""
Progress tracking for module communication.

Purpose: Tracks progress of module communication sessions with async support.
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class CommunicationStatus(Enum):
    """Status of module communication."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AsyncProgressTracker:
    """Async progress tracker for module communications."""
    
    def __init__(self, db_path: str = ":memory:"):
        """Initialize the progress tracker.
        
        Args:
            db_path: Path to SQLite database for progress tracking
        """
        self.db_path = db_path
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    async def start_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start a new tracking session.
        
        Args:
            session_id: Unique identifier for the session
            metadata: Optional metadata for the session
        """
        self._sessions[session_id] = {
            "status": CommunicationStatus.PENDING,
            "start_time": datetime.now(),
            "metadata": metadata or {},
            "progress": 0.0
        }
    
    async def update_progress(self, session_id: str, progress: float, status: Optional[CommunicationStatus] = None) -> None:
        """Update progress for a session.
        
        Args:
            session_id: Session identifier
            progress: Progress percentage (0.0 to 100.0)
            status: Optional status update
        """
        if session_id in self._sessions:
            self._sessions[session_id]["progress"] = min(100.0, max(0.0, progress))
            if status:
                self._sessions[session_id]["status"] = status
    
    async def end_session(self, session_id: str, status: CommunicationStatus) -> None:
        """End a tracking session.
        
        Args:
            session_id: Session identifier
            status: Final status of the session
        """
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = status
            self._sessions[session_id]["end_time"] = datetime.now()
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session information or None if not found
        """
        return self._sessions.get(session_id)