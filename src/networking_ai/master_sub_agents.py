"""
Master Agent's Sub-Agents - Specialized agents reporting to Master.

These agents help the Master Agent maintain a healthy AI networking platform:
- Traffic Analyzer: Monitors platform traffic patterns
- Audit Agent: Compliance and behavior auditing
- Security Agent: Security monitoring and threat detection
- Performance Optimizer: Optimizes platform performance
- R&D Agent: Research and development for new features
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage

from .config import config


# ============================================================================
# TRAFFIC ANALYZER AGENT
# ============================================================================

class TrafficPattern(Enum):
    """Traffic pattern types."""
    NORMAL = "normal"
    INCREASING = "increasing"
    DECREASING = "decreasing"
    SPIKE = "spike"
    ANOMALY = "anomaly"


@dataclass
class TrafficMetrics:
    """Traffic metrics snapshot."""
    timestamp: str
    total_requests: int
    unique_users: int
    active_agents: int
    avg_response_time: float
    error_rate: float
    peak_hour: int
    pattern: TrafficPattern
    recommendations: List[str] = field(default_factory=list)


class TrafficAnalyzerAgent:
    """
    Monitors platform traffic patterns and usage.

    Reports to Master Agent about:
    - User activity patterns
    - Peak usage times
    - Traffic anomalies
    - Resource requirements
    - Scalability needs
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize Traffic Analyzer Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.3,  # Analytical
        )
        self.traffic_history: List[TrafficMetrics] = []

        print("[TRAFFIC ANALYZER] Agent initialized and monitoring.")

    def analyze_current_traffic(
        self,
        total_requests: int,
        unique_users: int,
        active_agents: int,
        avg_response_time: float,
        error_rate: float,
    ) -> TrafficMetrics:
        """
        Analyze current traffic state.

        Args:
            total_requests: Total requests in period
            unique_users: Unique users active
            active_agents: Number of active agents
            avg_response_time: Average response time (ms)
            error_rate: Error rate (0-1)

        Returns:
            Traffic metrics with analysis
        """
        # Determine peak hour (simplified - would use real analytics)
        peak_hour = datetime.now().hour

        # Analyze pattern
        pattern = self._determine_pattern(total_requests)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            total_requests,
            avg_response_time,
            error_rate,
            pattern,
        )

        metrics = TrafficMetrics(
            timestamp=datetime.now().isoformat(),
            total_requests=total_requests,
            unique_users=unique_users,
            active_agents=active_agents,
            avg_response_time=avg_response_time,
            error_rate=error_rate,
            peak_hour=peak_hour,
            pattern=pattern,
            recommendations=recommendations,
        )

        self.traffic_history.append(metrics)

        print(f"\n[TRAFFIC ANALYZER] Current Analysis:")
        print(f"  Pattern: {pattern.value}")
        print(f"  Requests: {total_requests:,}")
        print(f"  Unique Users: {unique_users:,}")
        print(f"  Avg Response Time: {avg_response_time:.2f}ms")
        print(f"  Error Rate: {error_rate:.2%}")

        return metrics

    def _determine_pattern(self, current_requests: int) -> TrafficPattern:
        """Determine traffic pattern based on history."""
        if len(self.traffic_history) < 3:
            return TrafficPattern.NORMAL

        recent_avg = sum(m.total_requests for m in self.traffic_history[-3:]) / 3

        if current_requests > recent_avg * 2:
            return TrafficPattern.SPIKE
        elif current_requests > recent_avg * 1.2:
            return TrafficPattern.INCREASING
        elif current_requests < recent_avg * 0.8:
            return TrafficPattern.DECREASING
        elif abs(current_requests - recent_avg) > recent_avg * 0.5:
            return TrafficPattern.ANOMALY
        else:
            return TrafficPattern.NORMAL

    def _generate_recommendations(
        self,
        total_requests: int,
        avg_response_time: float,
        error_rate: float,
        pattern: TrafficPattern,
    ) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []

        # Response time recommendations
        if avg_response_time > 1000:
            recommendations.append("URGENT: Response time exceeds 1s - scale infrastructure")
        elif avg_response_time > 500:
            recommendations.append("WARNING: Response time elevated - monitor closely")

        # Error rate recommendations
        if error_rate > 0.05:
            recommendations.append("CRITICAL: Error rate above 5% - investigate immediately")
        elif error_rate > 0.02:
            recommendations.append("WARNING: Error rate elevated - review agent logs")

        # Pattern recommendations
        if pattern == TrafficPattern.SPIKE:
            recommendations.append("SPIKE detected - prepare for increased load")
        elif pattern == TrafficPattern.INCREASING:
            recommendations.append("Traffic growing - plan scaling strategy")
        elif pattern == TrafficPattern.ANOMALY:
            recommendations.append("ANOMALY detected - investigate unusual patterns")

        return recommendations

    def predict_traffic(self, hours_ahead: int = 24) -> Dict:
        """
        Predict future traffic using AI.

        Args:
            hours_ahead: Hours to predict ahead

        Returns:
            Traffic prediction
        """
        if len(self.traffic_history) < 5:
            return {"error": "Insufficient historical data"}

        # Prepare historical data
        history_summary = {
            "recent_patterns": [m.pattern.value for m in self.traffic_history[-10:]],
            "avg_requests": sum(m.total_requests for m in self.traffic_history) / len(self.traffic_history),
            "avg_users": sum(m.unique_users for m in self.traffic_history) / len(self.traffic_history),
        }

        system_prompt = """You are a Traffic Prediction AI. Analyze historical traffic patterns
and predict future traffic loads to help with capacity planning.

Provide predictions as JSON with:
- predicted_requests: int
- confidence: float (0-1)
- expected_pattern: string
- scaling_recommendation: string"""

        user_prompt = f"""Predict traffic for {hours_ahead} hours ahead:

Historical Data:
{json.dumps(history_summary, indent=2)}

Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Provide prediction as JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            prediction = json.loads(content)

        except Exception as e:
            prediction = {
                "predicted_requests": int(history_summary["avg_requests"] * 1.1),
                "confidence": 0.5,
                "expected_pattern": "normal",
                "scaling_recommendation": "Monitor closely",
            }

        return prediction

    def report_to_master(self) -> Dict:
        """Generate traffic report for Master Agent."""
        if not self.traffic_history:
            return {"error": "No traffic data available"}

        latest = self.traffic_history[-1]

        return {
            "agent": "TrafficAnalyzer",
            "timestamp": datetime.now().isoformat(),
            "current_metrics": {
                "pattern": latest.pattern.value,
                "total_requests": latest.total_requests,
                "unique_users": latest.unique_users,
                "avg_response_time": latest.avg_response_time,
                "error_rate": latest.error_rate,
            },
            "recommendations": latest.recommendations,
            "prediction": self.predict_traffic(24),
            "status": "healthy" if latest.error_rate < 0.02 else "needs_attention",
        }


# ============================================================================
# AUDIT AGENT
# ============================================================================

class AuditSeverity(Enum):
    """Audit issue severity."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditIssue:
    """Audit issue record."""
    issue_id: str
    severity: AuditSeverity
    category: str
    description: str
    agent_id: Optional[str]
    timestamp: str
    resolved: bool = False


class AuditAgent:
    """
    Compliance and behavior auditing agent.

    Reports to Master Agent about:
    - Policy violations
    - Unusual agent behavior
    - Data access patterns
    - Compliance issues
    - Security concerns
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize Audit Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.2,  # Strict
        )
        self.audit_log: List[AuditIssue] = []
        self.policies = self._load_policies()

        print("[AUDIT AGENT] Initialized and monitoring compliance.")

    def _load_policies(self) -> Dict:
        """Load platform policies."""
        return {
            "max_response_time": 2000,  # ms
            "max_hallucination_score": 0.3,
            "min_grounding_percentage": 0.7,
            "max_consecutive_failures": 3,
            "privacy_compliance": "strict",
            "data_retention_days": 365,
        }

    def audit_agent_behavior(
        self,
        agent_id: str,
        interactions: List[Dict],
    ) -> List[AuditIssue]:
        """
        Audit an agent's behavior for compliance.

        Args:
            agent_id: Agent to audit
            interactions: Recent interactions

        Returns:
            List of audit issues found
        """
        issues = []

        # Check response times
        slow_responses = [i for i in interactions if i.get('response_time', 0) > self.policies['max_response_time']]
        if slow_responses:
            issues.append(AuditIssue(
                issue_id=f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                severity=AuditSeverity.WARNING,
                category="performance",
                description=f"Agent {agent_id} has {len(slow_responses)} slow responses",
                agent_id=agent_id,
                timestamp=datetime.now().isoformat(),
            ))

        # Check hallucination scores
        high_hallucination = [i for i in interactions if i.get('hallucination_score', 0) > self.policies['max_hallucination_score']]
        if high_hallucination:
            issues.append(AuditIssue(
                issue_id=f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                severity=AuditSeverity.CRITICAL,
                category="hallucination",
                description=f"Agent {agent_id} has {len(high_hallucination)} high hallucination scores",
                agent_id=agent_id,
                timestamp=datetime.now().isoformat(),
            ))

        # Check grounding
        poor_grounding = [i for i in interactions if i.get('grounding_percentage', 1.0) < self.policies['min_grounding_percentage']]
        if poor_grounding:
            issues.append(AuditIssue(
                issue_id=f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                severity=AuditSeverity.WARNING,
                category="grounding",
                description=f"Agent {agent_id} has {len(poor_grounding)} poorly grounded responses",
                agent_id=agent_id,
                timestamp=datetime.now().isoformat(),
            ))

        # Store issues
        self.audit_log.extend(issues)

        if issues:
            print(f"\n[AUDIT AGENT] Issues found for {agent_id}:")
            for issue in issues:
                print(f"  [{issue.severity.value.upper()}] {issue.description}")

        return issues

    def audit_data_access(
        self,
        user_id: str,
        accessed_data: List[Dict],
        requesting_agent: str,
    ) -> Optional[AuditIssue]:
        """
        Audit data access for privacy compliance.

        Args:
            user_id: User whose data was accessed
            accessed_data: Data that was accessed
            requesting_agent: Agent that requested access

        Returns:
            Audit issue if violation found
        """
        # Check for PII access without authentication
        for data in accessed_data:
            if data.get('contains_pii', False) and not data.get('authenticated', False):
                issue = AuditIssue(
                    issue_id=f"AUDIT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    severity=AuditSeverity.CRITICAL,
                    category="privacy_violation",
                    description=f"Agent {requesting_agent} accessed PII for user {user_id} without authentication",
                    agent_id=requesting_agent,
                    timestamp=datetime.now().isoformat(),
                )

                self.audit_log.append(issue)

                print(f"\n[AUDIT AGENT] CRITICAL PRIVACY VIOLATION:")
                print(f"  Agent: {requesting_agent}")
                print(f"  User: {user_id}")
                print(f"  Action: Immediate review required")

                return issue

        return None

    def generate_compliance_report(self) -> Dict:
        """Generate compliance report for Master Agent."""
        total_issues = len(self.audit_log)
        critical_issues = len([i for i in self.audit_log if i.severity == AuditSeverity.CRITICAL])
        unresolved_issues = len([i for i in self.audit_log if not i.resolved])

        # Group by category
        by_category = {}
        for issue in self.audit_log:
            by_category[issue.category] = by_category.get(issue.category, 0) + 1

        return {
            "agent": "AuditAgent",
            "timestamp": datetime.now().isoformat(),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "unresolved_issues": unresolved_issues,
            "issues_by_category": by_category,
            "compliance_status": "compliant" if critical_issues == 0 else "non_compliant",
            "recommendation": "No action needed" if critical_issues == 0 else "Immediate review required",
        }

    def report_to_master(self) -> Dict:
        """Generate audit report for Master Agent."""
        return self.generate_compliance_report()


# ============================================================================
# SECURITY AGENT
# ============================================================================

class SecurityThreat(Enum):
    """Security threat types."""
    INJECTION_ATTACK = "injection_attack"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_LEAK = "data_leak"
    BRUTE_FORCE = "brute_force"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"


@dataclass
class SecurityIncident:
    """Security incident record."""
    incident_id: str
    threat_type: SecurityThreat
    severity: str
    description: str
    source_ip: Optional[str]
    target_agent: Optional[str]
    timestamp: str
    mitigated: bool = False


class SecurityAgent:
    """
    Security monitoring and threat detection agent.

    Reports to Master Agent about:
    - Security threats
    - Attack attempts
    - Vulnerabilities
    - Unauthorized access
    - Suspicious patterns
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize Security Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.1,  # Very strict
        )
        self.incidents: List[SecurityIncident] = []
        self.blocked_ips: List[str] = []

        print("[SECURITY AGENT] Initialized and monitoring security.")

    def scan_input(self, user_input: str, user_id: str) -> Optional[SecurityIncident]:
        """
        Scan user input for security threats.

        Args:
            user_input: Input to scan
            user_id: User ID

        Returns:
            Security incident if threat detected
        """
        # Check for injection patterns
        injection_patterns = [
            'DROP TABLE',
            'DELETE FROM',
            '<script>',
            'eval(',
            'exec(',
            '__import__',
            'system(',
        ]

        for pattern in injection_patterns:
            if pattern.lower() in user_input.lower():
                incident = SecurityIncident(
                    incident_id=f"SEC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    threat_type=SecurityThreat.INJECTION_ATTACK,
                    severity="critical",
                    description=f"Potential injection attack detected: {pattern}",
                    source_ip=None,
                    target_agent=None,
                    timestamp=datetime.now().isoformat(),
                )

                self.incidents.append(incident)

                print(f"\n[SECURITY AGENT] THREAT DETECTED:")
                print(f"  Type: {incident.threat_type.value}")
                print(f"  User: {user_id}")
                print(f"  Action: Input blocked")

                return incident

        return None

    def monitor_access_patterns(
        self,
        agent_id: str,
        access_attempts: List[Dict],
    ) -> Optional[SecurityIncident]:
        """
        Monitor for suspicious access patterns.

        Args:
            agent_id: Agent to monitor
            access_attempts: Recent access attempts

        Returns:
            Security incident if suspicious activity detected
        """
        # Check for brute force
        failed_attempts = [a for a in access_attempts if not a.get('success', True)]

        if len(failed_attempts) > 5:
            incident = SecurityIncident(
                incident_id=f"SEC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                threat_type=SecurityThreat.BRUTE_FORCE,
                severity="high",
                description=f"Multiple failed access attempts from agent {agent_id}",
                source_ip=None,
                target_agent=agent_id,
                timestamp=datetime.now().isoformat(),
            )

            self.incidents.append(incident)

            print(f"\n[SECURITY AGENT] SUSPICIOUS ACTIVITY:")
            print(f"  Agent: {agent_id}")
            print(f"  Failed Attempts: {len(failed_attempts)}")
            print(f"  Action: Enhanced monitoring")

            return incident

        return None

    def detect_data_leak(
        self,
        response: str,
        contains_private_data: bool,
        authenticated: bool,
    ) -> Optional[SecurityIncident]:
        """
        Detect potential data leaks.

        Args:
            response: Response to check
            contains_private_data: Whether response contains private data
            authenticated: Whether user is authenticated

        Returns:
            Security incident if leak detected
        """
        if contains_private_data and not authenticated:
            incident = SecurityIncident(
                incident_id=f"SEC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                threat_type=SecurityThreat.DATA_LEAK,
                severity="critical",
                description="Attempted to send private data to unauthenticated user",
                source_ip=None,
                target_agent=None,
                timestamp=datetime.now().isoformat(),
            )

            self.incidents.append(incident)

            print(f"\n[SECURITY AGENT] DATA LEAK PREVENTED:")
            print(f"  Severity: CRITICAL")
            print(f"  Action: Response blocked")

            return incident

        return None

    def generate_security_report(self) -> Dict:
        """Generate security report for Master Agent."""
        total_incidents = len(self.incidents)
        critical_incidents = len([i for i in self.incidents if i.severity == "critical"])
        unmitigated = len([i for i in self.incidents if not i.mitigated])

        # Group by threat type
        by_threat = {}
        for incident in self.incidents:
            by_threat[incident.threat_type.value] = by_threat.get(incident.threat_type.value, 0) + 1

        return {
            "agent": "SecurityAgent",
            "timestamp": datetime.now().isoformat(),
            "total_incidents": total_incidents,
            "critical_incidents": critical_incidents,
            "unmitigated_incidents": unmitigated,
            "incidents_by_type": by_threat,
            "blocked_ips": len(self.blocked_ips),
            "security_status": "secure" if critical_incidents == 0 else "under_threat",
            "recommendation": "System secure" if critical_incidents == 0 else "Immediate security review required",
        }

    def report_to_master(self) -> Dict:
        """Generate security report for Master Agent."""
        return self.generate_security_report()


# ============================================================================
# PERFORMANCE OPTIMIZER AGENT
# ============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    timestamp: str
    avg_agent_response_time: float
    cache_hit_rate: float
    rag_query_time: float
    embedding_generation_time: float
    total_throughput: int
    bottlenecks: List[str]
    optimization_suggestions: List[str]


class PerformanceOptimizerAgent:
    """
    Optimizes platform performance.

    Reports to Master Agent about:
    - Performance bottlenecks
    - Optimization opportunities
    - Resource usage
    - Caching efficiency
    - System health
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize Performance Optimizer Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.4,
        )
        self.metrics_history: List[PerformanceMetrics] = []

        print("[PERFORMANCE OPTIMIZER] Initialized and monitoring performance.")

    def analyze_performance(
        self,
        agent_response_times: List[float],
        cache_hits: int,
        cache_misses: int,
        rag_query_times: List[float],
        embedding_times: List[float],
        total_requests: int,
    ) -> PerformanceMetrics:
        """
        Analyze current performance metrics.

        Args:
            agent_response_times: List of response times
            cache_hits: Cache hit count
            cache_misses: Cache miss count
            rag_query_times: RAG query times
            embedding_times: Embedding generation times
            total_requests: Total requests processed

        Returns:
            Performance metrics with analysis
        """
        # Calculate averages
        avg_response = sum(agent_response_times) / len(agent_response_times) if agent_response_times else 0
        cache_hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        avg_rag = sum(rag_query_times) / len(rag_query_times) if rag_query_times else 0
        avg_embedding = sum(embedding_times) / len(embedding_times) if embedding_times else 0

        # Identify bottlenecks
        bottlenecks = []
        if avg_response > 1000:
            bottlenecks.append("High agent response time")
        if cache_hit_rate < 0.5:
            bottlenecks.append("Low cache hit rate")
        if avg_rag > 500:
            bottlenecks.append("Slow RAG queries")
        if avg_embedding > 200:
            bottlenecks.append("Slow embedding generation")

        # Generate optimization suggestions
        suggestions = self._generate_optimizations(
            avg_response, cache_hit_rate, avg_rag, avg_embedding
        )

        metrics = PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            avg_agent_response_time=avg_response,
            cache_hit_rate=cache_hit_rate,
            rag_query_time=avg_rag,
            embedding_generation_time=avg_embedding,
            total_throughput=total_requests,
            bottlenecks=bottlenecks,
            optimization_suggestions=suggestions,
        )

        self.metrics_history.append(metrics)

        print(f"\n[PERFORMANCE OPTIMIZER] Analysis:")
        print(f"  Avg Response Time: {avg_response:.2f}ms")
        print(f"  Cache Hit Rate: {cache_hit_rate:.1%}")
        print(f"  Bottlenecks: {len(bottlenecks)}")

        return metrics

    def _generate_optimizations(
        self,
        avg_response: float,
        cache_hit_rate: float,
        avg_rag: float,
        avg_embedding: float,
    ) -> List[str]:
        """Generate optimization suggestions."""
        suggestions = []

        if avg_response > 1000:
            suggestions.append("Implement request batching to reduce overhead")
            suggestions.append("Add response caching for common queries")

        if cache_hit_rate < 0.5:
            suggestions.append("Increase cache size and TTL")
            suggestions.append("Implement predictive caching for frequent queries")

        if avg_rag > 500:
            suggestions.append("Optimize RAG indexing with better embeddings")
            suggestions.append("Add query result caching")

        if avg_embedding > 200:
            suggestions.append("Use smaller embedding model for non-critical tasks")
            suggestions.append("Batch embedding generation")

        return suggestions

    def optimize_caching_strategy(self) -> Dict:
        """
        Optimize caching strategy using AI.

        Returns:
            Caching optimization recommendations
        """
        if len(self.metrics_history) < 3:
            return {"error": "Insufficient data for optimization"}

        recent_cache_rates = [m.cache_hit_rate for m in self.metrics_history[-10:]]
        avg_cache_rate = sum(recent_cache_rates) / len(recent_cache_rates)

        system_prompt = """You are a Performance Optimization AI specializing in caching strategies.
Analyze cache performance and recommend improvements.

Provide recommendations as JSON with:
- cache_size_recommendation: string
- ttl_recommendation: string
- eviction_policy: string
- priority_caching: list of strings"""

        user_prompt = f"""Optimize caching strategy:

Current cache hit rate: {avg_cache_rate:.1%}
Recent performance: {recent_cache_rates}

Provide optimization recommendations as JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            recommendations = json.loads(content)

        except Exception as e:
            recommendations = {
                "cache_size_recommendation": "Increase by 50%",
                "ttl_recommendation": "Increase to 1 hour for stable data",
                "eviction_policy": "LRU with priority for frequent queries",
                "priority_caching": ["User profiles", "Common queries", "Semantic embeddings"],
            }

        return recommendations

    def report_to_master(self) -> Dict:
        """Generate performance report for Master Agent."""
        if not self.metrics_history:
            return {"error": "No performance data available"}

        latest = self.metrics_history[-1]

        return {
            "agent": "PerformanceOptimizer",
            "timestamp": datetime.now().isoformat(),
            "current_metrics": {
                "avg_response_time": latest.avg_agent_response_time,
                "cache_hit_rate": latest.cache_hit_rate,
                "throughput": latest.total_throughput,
            },
            "bottlenecks": latest.bottlenecks,
            "suggestions": latest.optimization_suggestions,
            "status": "optimal" if len(latest.bottlenecks) == 0 else "needs_optimization",
        }


# ============================================================================
# R&D AGENT (RESEARCH & DEVELOPMENT)
# ============================================================================

@dataclass
class ResearchProject:
    """Research project."""
    project_id: str
    title: str
    description: str
    objective: str
    status: str  # planning, in_progress, completed
    findings: List[str]
    recommendations: List[str]
    created_at: str


class RDAgent:
    """
    Research and Development agent.

    Reports to Master Agent about:
    - New feature opportunities
    - Technology innovations
    - User feedback analysis
    - Competitive analysis
    - Platform improvements
    """

    def __init__(self, llm: Optional[ChatAnthropic] = None):
        """Initialize R&D Agent."""
        self.llm = llm or ChatAnthropic(
            model=config.DEFAULT_MODEL,
            temperature=0.8,  # Creative
        )
        self.projects: List[ResearchProject] = []

        print("[R&D AGENT] Initialized and researching innovations.")

    def research_feature_opportunity(
        self,
        user_feedback: List[str],
        platform_gaps: List[str],
    ) -> ResearchProject:
        """
        Research new feature opportunities.

        Args:
            user_feedback: User feedback and requests
            platform_gaps: Identified platform gaps

        Returns:
            Research project with recommendations
        """
        system_prompt = """You are an R&D AI specializing in product innovation for
professional networking platforms.

Analyze feedback and gaps to propose innovative features.

Provide research as JSON with:
- title: string
- description: string
- objective: string
- key_findings: list of strings
- recommendations: list of strings
- implementation_priority: string (high/medium/low)"""

        user_prompt = f"""Research feature opportunities:

User Feedback:
{chr(10).join(f"- {f}" for f in user_feedback[:10])}

Platform Gaps:
{chr(10).join(f"- {g}" for g in platform_gaps[:10])}

Provide research findings as JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            research = json.loads(content)

            project = ResearchProject(
                project_id=f"RD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                title=research.get('title', 'Feature Research'),
                description=research.get('description', ''),
                objective=research.get('objective', ''),
                status="completed",
                findings=research.get('key_findings', []),
                recommendations=research.get('recommendations', []),
                created_at=datetime.now().isoformat(),
            )

        except Exception as e:
            project = ResearchProject(
                project_id=f"RD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                title="Platform Enhancement Research",
                description="Research based on user feedback and platform gaps",
                objective="Identify high-impact features",
                status="completed",
                findings=["User feedback indicates need for improvements"],
                recommendations=["Conduct deeper analysis"],
                created_at=datetime.now().isoformat(),
            )

        self.projects.append(project)

        print(f"\n[R&D AGENT] Research Complete:")
        print(f"  Project: {project.title}")
        print(f"  Findings: {len(project.findings)}")
        print(f"  Recommendations: {len(project.recommendations)}")

        return project

    def analyze_competition(self, competitors: List[str]) -> Dict:
        """
        Analyze competitive landscape.

        Args:
            competitors: List of competitor platforms

        Returns:
            Competitive analysis
        """
        system_prompt = """You are a Competitive Analysis AI. Analyze competitor platforms
and identify opportunities for differentiation.

Provide analysis as JSON with:
- strengths_comparison: dict
- differentiation_opportunities: list of strings
- feature_gaps: list of strings
- strategic_recommendations: list of strings"""

        user_prompt = f"""Analyze competitive landscape:

Competitors: {', '.join(competitors)}

Our Platform: AI-native professional networking with privacy-first RAG,
multi-agent system, and anti-hallucination controls.

Provide competitive analysis as JSON."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = self.llm.invoke(messages)
            content = response.content

            # Parse JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            analysis = json.loads(content)

        except Exception as e:
            analysis = {
                "strengths_comparison": {"ai_native": "Unique advantage"},
                "differentiation_opportunities": ["Privacy-first approach", "Multi-agent intelligence"],
                "feature_gaps": ["Mobile app", "Video networking"],
                "strategic_recommendations": ["Focus on AI differentiation"],
            }

        return analysis

    def report_to_master(self) -> Dict:
        """Generate R&D report for Master Agent."""
        return {
            "agent": "R&D",
            "timestamp": datetime.now().isoformat(),
            "active_projects": len([p for p in self.projects if p.status == "in_progress"]),
            "completed_projects": len([p for p in self.projects if p.status == "completed"]),
            "recent_findings": [
                {
                    "title": p.title,
                    "recommendations": p.recommendations[:3],
                }
                for p in self.projects[-5:]
            ],
            "status": "active",
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_master_sub_agents() -> Dict[str, Any]:
    """
    Create all Master's sub-agents.

    Returns:
        Dictionary of initialized sub-agents
    """
    return {
        "traffic_analyzer": TrafficAnalyzerAgent(),
        "audit_agent": AuditAgent(),
        "security_agent": SecurityAgent(),
        "performance_optimizer": PerformanceOptimizerAgent(),
        "rd_agent": RDAgent(),
    }
