"""Knowledge base for pattern sharing between agents."""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEntry:
    """An entry in the knowledge base."""
    key: str
    value: Dict[str, Any]
    source_agent: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: int = 86400  # 24 hours default
    tags: List[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds <= 0:
            return False
        age = (datetime.utcnow() - self.timestamp).total_seconds()
        return age > self.ttl_seconds


class KnowledgeBase:
    """Shared knowledge store for agents."""

    def __init__(self):
        """Initialize knowledge base."""
        self._knowledge: Dict[str, KnowledgeEntry] = {}
        self._tags_index: Dict[str, List[str]] = {}

    def store_pattern(
        self,
        key: str,
        value: Dict[str, Any],
        source_agent: str,
        tags: Optional[List[str]] = None,
        ttl_seconds: int = 86400,
    ) -> None:
        """Store a knowledge pattern.

        Args:
            key: Pattern key
            value: Pattern value/content
            source_agent: Source agent ID
            tags: Optional tags for categorization
            ttl_seconds: Time-to-live in seconds
        """
        tags = tags or []
        entry = KnowledgeEntry(
            key=key,
            value=value,
            source_agent=source_agent,
            tags=tags,
            ttl_seconds=ttl_seconds,
        )

        self._knowledge[key] = entry

        # Update tags index
        for tag in tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = []
            if key not in self._tags_index[tag]:
                self._tags_index[tag].append(key)

        logger.info(f"Stored knowledge pattern: {key} from {source_agent}")

    def query_patterns(
        self, criteria: Dict[str, Any]
    ) -> List[KnowledgeEntry]:
        """Query patterns by criteria.

        Args:
            criteria: Query criteria (key, tag, source_agent, etc.)

        Returns:
            List of matching entries
        """
        results = []

        for entry in self._knowledge.values():
            # Skip expired entries
            if entry.is_expired():
                continue

            # Apply criteria
            if "key" in criteria and entry.key != criteria["key"]:
                continue
            if "source_agent" in criteria and entry.source_agent != criteria["source_agent"]:
                continue
            if "tag" in criteria and criteria["tag"] not in entry.tags:
                continue

            results.append(entry)

        return results

    def get_pattern(self, key: str) -> Optional[KnowledgeEntry]:
        """Get a specific pattern by key.

        Args:
            key: Pattern key

        Returns:
            KnowledgeEntry if found and not expired, None otherwise
        """
        entry = self._knowledge.get(key)
        if entry and not entry.is_expired():
            return entry
        return None

    def get_related_patterns(
        self, pattern_key: str, match_tags: bool = True
    ) -> List[KnowledgeEntry]:
        """Get patterns related to a given pattern.

        Args:
            pattern_key: Key of reference pattern
            match_tags: If True, match by tags; if False, match by source agent

        Returns:
            List of related patterns
        """
        reference = self.get_pattern(pattern_key)
        if not reference:
            return []

        related = []

        for entry in self._knowledge.values():
            if entry.key == pattern_key or entry.is_expired():
                continue

            if match_tags:
                # Match by common tags
                if any(tag in entry.tags for tag in reference.tags):
                    related.append(entry)
            else:
                # Match by source agent
                if entry.source_agent == reference.source_agent:
                    related.append(entry)

        return related

    def share_with_agents(
        self, pattern_key: str, agent_ids: List[str]
    ) -> Dict[str, bool]:
        """Share a pattern with specific agents.

        Args:
            pattern_key: Key of pattern to share
            agent_ids: List of target agent IDs

        Returns:
            Dictionary of agent_id -> success
        """
        entry = self.get_pattern(pattern_key)
        if not entry:
            logger.warning(f"Pattern not found for sharing: {pattern_key}")
            return {aid: False for aid in agent_ids}

        results = {}
        for agent_id in agent_ids:
            # Record that this pattern was shared with this agent
            # In a full implementation, this would notify the agent
            results[agent_id] = True
            logger.debug(f"Shared pattern {pattern_key} with agent {agent_id}")

        return results

    def cleanup_expired(self) -> int:
        """Clean up expired entries.

        Returns:
            Number of entries cleaned up
        """
        expired_keys = [
            key for key, entry in self._knowledge.items()
            if entry.is_expired()
        ]

        for key in expired_keys:
            entry = self._knowledge.pop(key)
            # Remove from tags index
            for tag in entry.tags:
                if tag in self._tags_index:
                    self._tags_index[tag].remove(key)
                    if not self._tags_index[tag]:
                        del self._tags_index[tag]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired knowledge entries")

        return len(expired_keys)

    def get_all_patterns(self) -> List[KnowledgeEntry]:
        """Get all non-expired patterns.

        Returns:
            List of all valid patterns
        """
        return [e for e in self._knowledge.values() if not e.is_expired()]

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics.

        Returns:
            Dictionary with stats
        """
        total = len(self._knowledge)
        valid = sum(1 for e in self._knowledge.values() if not e.is_expired())
        expired = total - valid

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "total_tags": len(self._tags_index),
        }
