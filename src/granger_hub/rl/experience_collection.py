"""
Experience collection and offline training for RL agents.
Module: experience_collection.py
Description: Functions for experience collection operations

This module handles the collection, storage, and replay of experiences
for training RL agents in the ModuleCommunicator system.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

# Import rl_commons components
try:
    from rl_commons import DQNAgent, PPOAgent
    from rl_commons.core import ReplayBuffer, Experience
except ImportError as e:
    raise ImportError(
        "rl_commons not installed. Please install with: "
        "pip install git+https://github.com/grahama1970/rl_commons.git@master"
    ) from e

from granger_hub.rl.state_extraction import (
    extract_task_state,
    extract_pipeline_state,
    extract_error_state
)
from granger_hub.rl.reward_calculation import (
    calculate_module_selection_reward,
    calculate_pipeline_reward,
    calculate_resource_reward
)

# Default experience database path
EXPERIENCE_DB_PATH = Path("data/rl_experiences.db")


def initialize_experience_db(db_path: Optional[Path] = None) -> None:
    """
    Initialize the experience database.
    
    Args:
        db_path: Optional custom database path
    """
    db_path = db_path or EXPERIENCE_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create experiences table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            decision_type TEXT NOT NULL,
            state TEXT NOT NULL,
            action TEXT NOT NULL,
            reward REAL,
            next_state TEXT,
            done INTEGER DEFAULT 0,
            metadata TEXT,
            module TEXT,
            task_type TEXT,
            outcome TEXT
        )
    """)
    
    # Create index for efficient queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_experiences_type_time 
        ON experiences(decision_type, timestamp)
    """)
    
    # Create statistics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experience_stats (
            decision_type TEXT PRIMARY KEY,
            total_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            avg_reward REAL DEFAULT 0,
            last_updated TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def log_experience(
    decision_type: str,
    state: np.ndarray,
    action: Any,
    reward: float,
    next_state: Optional[np.ndarray] = None,
    done: bool = False,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Log an experience to the database.
    
    Args:
        decision_type: Type of decision (module_selection, pipeline_optimization, etc.)
        state: State vector
        action: Action taken
        reward: Reward received
        next_state: Next state (optional)
        done: Whether episode is complete
        metadata: Additional metadata
    
    Returns:
        Experience ID
    """
    db_path = EXPERIENCE_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Prepare data for storage
    exp_data = {
        'timestamp': datetime.now().isoformat(),
        'decision_type': decision_type,
        'state': json.dumps(state.tolist() if isinstance(state, np.ndarray) else state),
        'action': json.dumps(action if isinstance(action, (list, dict)) else str(action)),
        'reward': float(reward),
        'next_state': json.dumps(next_state.tolist() if next_state is not None else None),
        'done': int(done),
        'metadata': json.dumps(metadata or {}),
        'module': metadata.get('module') if metadata else None,
        'task_type': metadata.get('task_type') if metadata else None,
        'outcome': json.dumps(metadata.get('outcome')) if metadata and 'outcome' in metadata else None
    }
    
    # Insert experience
    cursor.execute("""
        INSERT INTO experiences (
            timestamp, decision_type, state, action, reward,
            next_state, done, metadata, module, task_type, outcome
        ) VALUES (
            :timestamp, :decision_type, :state, :action, :reward,
            :next_state, :done, :metadata, :module, :task_type, :outcome
        )
    """, exp_data)
    
    experience_id = cursor.lastrowid
    
    # Update statistics
    _update_stats(cursor, decision_type, reward, metadata)
    
    conn.commit()
    conn.close()
    
    return experience_id


def load_experiences(
    decision_type: Optional[str] = None,
    limit: int = 1000,
    since: Optional[datetime] = None,
    min_reward: Optional[float] = None
) -> List[Experience]:
    """
    Load experiences from the database.
    
    Args:
        decision_type: Filter by decision type
        limit: Maximum number of experiences to load
        since: Load experiences since this datetime
        min_reward: Minimum reward threshold
    
    Returns:
        List of Experience objects
    """
    initialize_experience_db()
    
    conn = sqlite3.connect(str(EXPERIENCE_DB_PATH))
    cursor = conn.cursor()
    
    # Build query
    query = "SELECT * FROM experiences WHERE 1=1"
    params = {}
    
    if decision_type:
        query += " AND decision_type = :decision_type"
        params['decision_type'] = decision_type
    
    if since:
        query += " AND timestamp >= :since"
        params['since'] = since.isoformat()
    
    if min_reward is not None:
        query += " AND reward >= :min_reward"
        params['min_reward'] = min_reward
    
    query += " ORDER BY timestamp DESC LIMIT :limit"
    params['limit'] = limit
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Convert to Experience objects
    experiences = []
    for row in rows:
        state = np.array(json.loads(row[3]))
        action = json.loads(row[4])
        reward = row[5]
        next_state = json.loads(row[6]) if row[6] else None
        if next_state:
            next_state = np.array(next_state)
        done = bool(row[7])
        
        exp = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done
        )
        experiences.append(exp)
    
    conn.close()
    return experiences


def train_agents_offline(
    agents: Dict[str, Any],
    batch_size: int = 32,
    epochs: int = 10,
    decision_types: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """
    Train agents offline using collected experiences.
    
    Args:
        agents: Dictionary of agent_name -> agent instance
        batch_size: Batch size for training
        epochs: Number of training epochs
        decision_types: Specific decision types to train on
    
    Returns:
        Training metrics for each agent
    """
    metrics = {}
    
    for agent_name, agent in agents.items():
        if hasattr(agent, 'train_offline'):
            # Load experiences for this agent type
            decision_type = _get_decision_type_for_agent(agent_name)
            if decision_types and decision_type not in decision_types:
                continue
            
            experiences = load_experiences(
                decision_type=decision_type,
                limit=10000,  # Load more for training
                min_reward=-float('inf')  # Include all experiences
            )
            
            if not experiences:
                continue
            
            # Add experiences to agent's replay buffer if it's a DQN agent
            if hasattr(agent, 'store_experience'):
                for exp in experiences:
                    agent.store_experience(exp)
            
            # Train the agent
            agent_metrics = {
                'episodes': len(experiences),
                'avg_reward': np.mean([exp.reward for exp in experiences]),
                'losses': []
            }
            
            # Different training methods for different agent types
            if hasattr(agent, 'train'):
                # DQN agents have a train method
                for epoch in range(epochs):
                    if hasattr(agent, 'can_train') and agent.can_train():
                        loss = agent.train(batch_size)
                        agent_metrics['losses'].append(loss if loss is not None else 0)
                    else:
                        # Not enough experiences yet
                        agent_metrics['losses'].append(0)
            elif hasattr(agent, 'update_policy'):
                # PPO agents use update_policy
                agent.update_policy()
                agent_metrics['losses'] = [0]  # PPO doesn't return loss easily'
            
            agent_metrics['final_loss'] = agent_metrics['losses'][-1] if agent_metrics['losses'] else 0
            metrics[agent_name] = agent_metrics
    
    return metrics


def get_experience_statistics(
    decision_type: Optional[str] = None,
    time_window: Optional[timedelta] = None
) -> Dict[str, Any]:
    """
    Get statistics about collected experiences.
    
    Args:
        decision_type: Filter by decision type
        time_window: Time window for statistics
    
    Returns:
        Dictionary of statistics
    """
    initialize_experience_db()
    
    conn = sqlite3.connect(str(EXPERIENCE_DB_PATH))
    cursor = conn.cursor()
    
    stats = {}
    
    # Get overall statistics
    if decision_type:
        cursor.execute("""
            SELECT COUNT(*), AVG(reward), MIN(reward), MAX(reward)
            FROM experiences
            WHERE decision_type = ?
        """, (decision_type,))
    else:
        cursor.execute("""
            SELECT COUNT(*), AVG(reward), MIN(reward), MAX(reward)
            FROM experiences
        """)
    
    count, avg_reward, min_reward, max_reward = cursor.fetchone()
    
    stats['total_experiences'] = count or 0
    stats['avg_reward'] = avg_reward or 0
    stats['min_reward'] = min_reward or 0
    stats['max_reward'] = max_reward or 0
    
    # Get per-type statistics
    cursor.execute("""
        SELECT decision_type, COUNT(*), AVG(reward)
        FROM experiences
        GROUP BY decision_type
    """)
    
    stats['by_type'] = {}
    for dt, cnt, avg_r in cursor.fetchall():
        stats['by_type'][dt] = {
            'count': cnt,
            'avg_reward': avg_r
        }
    
    # Get time-based statistics if requested
    if time_window:
        since = datetime.now() - time_window
        cursor.execute("""
            SELECT COUNT(*), AVG(reward)
            FROM experiences
            WHERE timestamp >= ?
        """, (since.isoformat(),))
        
        recent_count, recent_avg = cursor.fetchone()
        stats['recent'] = {
            'count': recent_count or 0,
            'avg_reward': recent_avg or 0,
            'time_window': str(time_window)
        }
    
    # Get module performance
    cursor.execute("""
        SELECT module, COUNT(*), AVG(reward)
        FROM experiences
        WHERE module IS NOT NULL
        GROUP BY module
    """)
    
    stats['by_module'] = {}
    for module, cnt, avg_r in cursor.fetchall():
        stats['by_module'][module] = {
            'count': cnt,
            'avg_reward': avg_r
        }
    
    conn.close()
    return stats


def _update_stats(cursor, decision_type: str, reward: float, metadata: Optional[Dict] = None):
    """Update experience statistics."""
    # Check if stats exist
    cursor.execute(
        "SELECT total_count, success_count, avg_reward FROM experience_stats WHERE decision_type = ?",
        (decision_type,)
    )
    row = cursor.fetchone()
    
    if row:
        total_count, success_count, avg_reward = row
        total_count += 1
        if reward > 0:
            success_count += 1
        # Update running average
        avg_reward = (avg_reward * (total_count - 1) + reward) / total_count
        
        cursor.execute("""
            UPDATE experience_stats
            SET total_count = ?, success_count = ?, avg_reward = ?, last_updated = ?
            WHERE decision_type = ?
        """, (total_count, success_count, avg_reward, datetime.now().isoformat(), decision_type))
    else:
        # Insert new stats
        cursor.execute("""
            INSERT INTO experience_stats (decision_type, total_count, success_count, avg_reward, last_updated)
            VALUES (?, 1, ?, ?, ?)
        """, (decision_type, 1 if reward > 0 else 0, reward, datetime.now().isoformat()))


def _get_decision_type_for_agent(agent_name: str) -> str:
    """Map agent name to decision type."""
    mapping = {
        'module_selector': 'module_selection',
        'pipeline_optimizer': 'pipeline_optimization',
        'resource_allocator': 'resource_allocation',
        'error_handler': 'error_handling'
    }
    return mapping.get(agent_name, agent_name)


# Module validation
if __name__ == "__main__":
    # Initialize database
    initialize_experience_db()
    print(" Experience database initialized")
    
    # Test logging experience
    test_state = np.array([0.5, 0.3, 0.8, 0.2, 0.6, 0.4, 0.7, 0.1, 0.9, 0.5])
    test_action = "marker"
    test_reward = 0.85
    test_next_state = np.array([0.6, 0.4, 0.7, 0.3, 0.5, 0.5, 0.8, 0.2, 0.9, 0.6])
    
    exp_id = log_experience(
        decision_type="module_selection",
        state=test_state,
        action=test_action,
        reward=test_reward,
        next_state=test_next_state,
        metadata={
            "module": "marker",
            "task_type": "pdf_extraction",
            "outcome": {"success": True, "latency": 120}
        }
    )
    print(f" Logged experience with ID: {exp_id}")
    
    # Test loading experiences
    experiences = load_experiences(limit=5)
    print(f" Loaded {len(experiences)} experiences")
    
    # Test statistics
    stats = get_experience_statistics()
    print(f" Experience statistics: {json.dumps(stats, indent=2)}")
    
    print("\n Experience collection module validated successfully!")