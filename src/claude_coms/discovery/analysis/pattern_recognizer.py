"""
Pattern Recognizer - Extracts interaction patterns from research

Identifies common patterns and architectures from research findings.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import re

from ..research.research_agent import ResearchFinding
from ..analysis.optimization_analyzer import InteractionPattern


@dataclass
class PatternTemplate:
    """Template for recognizing patterns"""
    name: str
    keywords: List[str]
    module_hints: List[str]
    flow_type: str
    description: str


class PatternRecognizer:
    """Recognizes interaction patterns from research findings"""
    
    def __init__(self):
        # Define pattern templates
        self.pattern_templates = self._initialize_templates()
        
        # Module mapping based on context
        self.context_to_modules = {
            "pdf": ["marker"],
            "security": ["sparta"],
            "research": ["arxiv", "youtube_transcripts"],
            "ai": ["llm_call", "claude_max_proxy"],
            "ml": ["unsloth", "llm_call"],
            "storage": ["arangodb"],
            "visual": ["mcp_screenshot"],
            "report": ["test_reporter"]
        }
    
    async def recognize_patterns(
        self,
        findings: List[ResearchFinding]
    ) -> List[InteractionPattern]:
        """Extract interaction patterns from research findings"""
        patterns = []
        
        # Extract patterns from each finding
        for finding in findings:
            finding_patterns = self._extract_patterns_from_finding(finding)
            patterns.extend(finding_patterns)
        
        # Merge similar patterns
        merged_patterns = self._merge_similar_patterns(patterns)
        
        # Enrich patterns with modules
        enriched_patterns = self._enrich_patterns_with_modules(merged_patterns, findings)
        
        return enriched_patterns
    
    def _initialize_templates(self) -> List[PatternTemplate]:
        """Initialize pattern recognition templates"""
        return [
            PatternTemplate(
                name="Pipeline Pattern",
                keywords=["pipeline", "sequential", "workflow", "chain", "steps"],
                module_hints=["input", "process", "output"],
                flow_type="sequential",
                description="Sequential data processing pipeline"
            ),
            PatternTemplate(
                name="Map-Reduce Pattern",
                keywords=["parallel", "map", "reduce", "scatter", "gather", "concurrent"],
                module_hints=["splitter", "workers", "aggregator"],
                flow_type="parallel",
                description="Parallel processing with aggregation"
            ),
            PatternTemplate(
                name="Event-Driven Pattern",
                keywords=["event", "async", "message", "pub/sub", "queue", "stream"],
                module_hints=["event_source", "processor", "sink"],
                flow_type="event_driven",
                description="Asynchronous event processing"
            ),
            PatternTemplate(
                name="Circuit Breaker Pattern",
                keywords=["circuit breaker", "resilience", "fault", "fallback", "timeout"],
                module_hints=["monitor", "breaker", "fallback"],
                flow_type="sequential",
                description="Fault tolerance with circuit breaking"
            ),
            PatternTemplate(
                name="Saga Pattern",
                keywords=["saga", "transaction", "compensation", "distributed"],
                module_hints=["coordinator", "services", "compensator"],
                flow_type="sequential",
                description="Distributed transaction management"
            ),
            PatternTemplate(
                name="CQRS Pattern",
                keywords=["cqrs", "command", "query", "separation", "read", "write"],
                module_hints=["command_handler", "query_handler", "store"],
                flow_type="hybrid",
                description="Command Query Responsibility Segregation"
            ),
            PatternTemplate(
                name="Cache-Aside Pattern",
                keywords=["cache", "aside", "lazy", "loading", "invalidation"],
                module_hints=["cache", "datastore", "app"],
                flow_type="sequential",
                description="Caching with lazy loading"
            ),
            PatternTemplate(
                name="Bulkhead Pattern",
                keywords=["bulkhead", "isolation", "resource", "pool", "limit"],
                module_hints=["resource_pool", "limiter", "service"],
                flow_type="parallel",
                description="Resource isolation for fault containment"
            )
        ]
    
    def _extract_patterns_from_finding(
        self,
        finding: ResearchFinding
    ) -> List[InteractionPattern]:
        """Extract patterns from a single finding"""
        patterns = []
        content_lower = finding.content.lower()
        
        # Check against templates
        for template in self.pattern_templates:
            if self._matches_template(content_lower, template):
                pattern = InteractionPattern(
                    name=f"{template.name} from {finding.source}",
                    modules=[],  # Will be enriched later
                    flow_type=template.flow_type,
                    steps=[],  # Will be built later
                    metadata={
                        "source": finding.source,
                        "source_title": finding.title,
                        "template": template.name,
                        "confidence": self._calculate_confidence(content_lower, template)
                    }
                )
                patterns.append(pattern)
        
        # Also use patterns directly mentioned in findings
        for pattern_name in finding.patterns_found:
            if not any(p.metadata.get("template") == pattern_name for p in patterns):
                pattern = InteractionPattern(
                    name=f"{pattern_name} Pattern",
                    modules=[],
                    flow_type=self._infer_flow_type(pattern_name),
                    steps=[],
                    metadata={
                        "source": finding.source,
                        "pattern_name": pattern_name,
                        "direct_mention": True
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _matches_template(self, content: str, template: PatternTemplate) -> bool:
        """Check if content matches a pattern template"""
        # Count keyword matches
        matches = sum(1 for keyword in template.keywords if keyword in content)
        
        # Need at least 2 keyword matches or 1 exact name match
        return matches >= 2 or template.name.lower() in content
    
    def _calculate_confidence(self, content: str, template: PatternTemplate) -> float:
        """Calculate confidence score for pattern match"""
        # Count keyword occurrences
        keyword_score = sum(
            content.count(keyword) for keyword in template.keywords
        ) / len(template.keywords)
        
        # Normalize to 0-1
        return min(1.0, keyword_score / 3)
    
    def _infer_flow_type(self, pattern_name: str) -> str:
        """Infer flow type from pattern name"""
        pattern_lower = pattern_name.lower()
        
        if any(word in pattern_lower for word in ["parallel", "concurrent", "map"]):
            return "parallel"
        elif any(word in pattern_lower for word in ["event", "async", "stream"]):
            return "event_driven"
        elif any(word in pattern_lower for word in ["sequential", "pipeline", "chain"]):
            return "sequential"
        else:
            return "hybrid"
    
    def _merge_similar_patterns(
        self,
        patterns: List[InteractionPattern]
    ) -> List[InteractionPattern]:
        """Merge patterns that are similar"""
        merged = []
        processed = set()
        
        for i, pattern in enumerate(patterns):
            if i in processed:
                continue
                
            # Find similar patterns
            similar = [pattern]
            for j, other in enumerate(patterns[i+1:], i+1):
                if j not in processed and self._are_patterns_similar(pattern, other):
                    similar.append(other)
                    processed.add(j)
            
            # Merge if multiple similar patterns found
            if len(similar) > 1:
                merged_pattern = self._merge_patterns(similar)
                merged.append(merged_pattern)
            else:
                merged.append(pattern)
        
        return merged
    
    def _are_patterns_similar(
        self,
        p1: InteractionPattern,
        p2: InteractionPattern
    ) -> bool:
        """Check if two patterns are similar enough to merge"""
        # Same flow type and similar names
        if p1.flow_type != p2.flow_type:
            return False
        
        # Check name similarity
        name1_words = set(p1.name.lower().split())
        name2_words = set(p2.name.lower().split())
        
        common_words = name1_words.intersection(name2_words)
        similarity = len(common_words) / max(len(name1_words), len(name2_words))
        
        return similarity > 0.5
    
    def _merge_patterns(self, patterns: List[InteractionPattern]) -> InteractionPattern:
        """Merge multiple similar patterns"""
        # Use most common flow type
        flow_types = [p.flow_type for p in patterns]
        flow_type = max(set(flow_types), key=flow_types.count)
        
        # Combine names intelligently
        template_names = [
            p.metadata.get("template", "") 
            for p in patterns if p.metadata.get("template")
        ]
        
        if template_names:
            name = f"{template_names[0]} (merged from {len(patterns)} sources)"
        else:
            name = f"Merged Pattern ({len(patterns)} sources)"
        
        # Combine metadata
        sources = [p.metadata.get("source", "") for p in patterns]
        
        return InteractionPattern(
            name=name,
            modules=[],  # Will be enriched
            flow_type=flow_type,
            steps=[],
            metadata={
                "merged": True,
                "source_count": len(patterns),
                "sources": list(set(sources)),
                "confidence": max(p.metadata.get("confidence", 0.5) for p in patterns)
            }
        )
    
    def _enrich_patterns_with_modules(
        self,
        patterns: List[InteractionPattern],
        findings: List[ResearchFinding]
    ) -> List[InteractionPattern]:
        """Add appropriate modules to patterns based on context"""
        enriched = []
        
        for pattern in patterns:
            # Extract context from associated findings
            contexts = self._extract_contexts(pattern, findings)
            
            # Map contexts to modules
            modules = self._map_contexts_to_modules(contexts)
            
            # Add modules based on pattern type
            pattern_modules = self._get_pattern_specific_modules(pattern)
            modules.extend(pattern_modules)
            
            # Remove duplicates and limit
            pattern.modules = list(dict.fromkeys(modules))[:6]
            
            # Create steps
            pattern.steps = self._create_steps_for_pattern(pattern)
            
            enriched.append(pattern)
        
        return enriched
    
    def _extract_contexts(
        self,
        pattern: InteractionPattern,
        findings: List[ResearchFinding]
    ) -> Set[str]:
        """Extract contexts from findings related to pattern"""
        contexts = set()
        
        # Get source from pattern
        source_title = pattern.metadata.get("source_title", "")
        
        # Find related findings
        for finding in findings:
            if finding.title == source_title or any(
                p in pattern.name.lower() for p in finding.patterns_found
            ):
                # Extract contexts from content
                content_lower = finding.content.lower()
                
                for context, keywords in self.context_to_modules.items():
                    if any(kw in content_lower for kw in [context] + keywords):
                        contexts.add(context)
        
        return contexts
    
    def _map_contexts_to_modules(self, contexts: Set[str]) -> List[str]:
        """Map contexts to specific modules"""
        modules = []
        
        for context in contexts:
            if context in self.context_to_modules:
                modules.extend(self.context_to_modules[context])
        
        # Add default modules if none found
        if not modules:
            modules = ["llm_call", "test_reporter"]
        
        return modules
    
    def _get_pattern_specific_modules(
        self,
        pattern: InteractionPattern
    ) -> List[str]:
        """Get modules specific to pattern type"""
        template_name = pattern.metadata.get("template", "")
        
        module_suggestions = {
            "Pipeline Pattern": ["marker", "llm_call", "test_reporter"],
            "Map-Reduce Pattern": ["arxiv", "youtube_transcripts", "llm_call", "arangodb"],
            "Event-Driven Pattern": ["mcp_screenshot", "llm_call", "arangodb"],
            "Circuit Breaker Pattern": ["claude_max_proxy", "llm_call"],
            "Cache-Aside Pattern": ["arangodb", "llm_call"],
            "Saga Pattern": ["sparta", "arangodb", "test_reporter"],
            "CQRS Pattern": ["arangodb", "llm_call", "test_reporter"],
            "Bulkhead Pattern": ["claude_max_proxy", "llm_call", "unsloth"]
        }
        
        return module_suggestions.get(template_name, [])
    
    def _create_steps_for_pattern(self, pattern: InteractionPattern) -> List[Dict[str, Any]]:
        """Create workflow steps based on pattern type and modules"""
        steps = []
        modules = pattern.modules
        
        if not modules:
            return steps
        
        if pattern.flow_type == "parallel":
            # Parallel execution pattern
            # All modules execute in parallel, then aggregate
            for i, module in enumerate(modules[:-1]):
                steps.append({
                    "from_module": "coordinator",
                    "to_module": module,
                    "content": {"task": "parallel_process", "group": 1}
                })
            
            # Aggregation step
            if len(modules) > 1:
                steps.append({
                    "from_module": modules[0],
                    "to_module": modules[-1],
                    "content": {"task": "aggregate_results"}
                })
                
        elif pattern.flow_type == "event_driven":
            # Event-driven pattern
            # First module publishes, others subscribe
            steps.append({
                "from_module": "coordinator",
                "to_module": modules[0],
                "content": {"task": "publish_event"}
            })
            
            for module in modules[1:]:
                steps.append({
                    "from_module": modules[0],
                    "to_module": module,
                    "content": {"task": "handle_event", "async": True}
                })
                
        else:  # sequential or hybrid
            # Sequential pattern
            for i, module in enumerate(modules):
                from_module = "coordinator" if i == 0 else modules[i-1]
                steps.append({
                    "from_module": from_module,
                    "to_module": module,
                    "content": {"task": f"step_{i+1}"}
                })
        
        return steps


if __name__ == "__main__":
    # Test pattern recognizer
    import asyncio
    
    async def test_recognizer():
        recognizer = PatternRecognizer()
        
        # Create test findings
        findings = [
            ResearchFinding(
                source="arxiv",
                title="Microservice Pipeline Optimization",
                content="We present a sequential pipeline pattern for microservices with caching...",
                patterns_found=["pipeline", "cache"],
                relevance_score=0.9
            ),
            ResearchFinding(
                source="youtube",
                title="Parallel Processing at Scale",
                content="This talk covers parallel map-reduce patterns for distributed systems...",
                patterns_found=["parallel", "map_reduce"],
                relevance_score=0.85
            )
        ]
        
        # Recognize patterns
        patterns = await recognizer.recognize_patterns(findings)
        
        print(f"Recognized {len(patterns)} patterns:")
        for pattern in patterns:
            print(f"\n{pattern.name}:")
            print(f"  Type: {pattern.flow_type}")
            print(f"  Modules: {', '.join(pattern.modules)}")
            print(f"  Steps: {len(pattern.steps)}")
            print(f"  Confidence: {pattern.metadata.get('confidence', 'N/A')}")
    
    asyncio.run(test_recognizer())