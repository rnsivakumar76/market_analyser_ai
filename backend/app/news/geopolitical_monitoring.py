"""
Geopolitical Analysis Performance Monitoring
Tracks performance metrics and health indicators
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    execution_time_ms: float
    cache_hit: bool
    events_processed: int
    sentiment_score: float
    error_occurred: bool
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class GeopoliticalMonitor:
    """Monitor and track geopolitical analysis performance"""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history_size = 100
        self.start_time = time.time()
        
    def start_execution_timer(self) -> float:
        """Start execution timer"""
        return time.time()
    
    def end_execution_timer(self, start_time: float) -> float:
        """End execution timer and return duration in milliseconds"""
        return (time.time() - start_time) * 1000
    
    def record_execution(self, 
                        execution_time_ms: float,
                        cache_hit: bool,
                        events_processed: int,
                        sentiment_score: float,
                        error_occurred: bool = False,
                        error_message: Optional[str] = None) -> None:
        """Record execution metrics"""
        
        metrics = PerformanceMetrics(
            execution_time_ms=execution_time_ms,
            cache_hit=cache_hit,
            events_processed=events_processed,
            sentiment_score=sentiment_score,
            error_occurred=error_occurred,
            error_message=error_message
        )
        
        self.metrics_history.append(metrics)
        
        # Maintain history size
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        logger.info(f"Recorded execution: {execution_time_ms:.2f}ms, cache_hit={cache_hit}, events={events_processed}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        if not self.metrics_history:
            return {
                'total_executions': 0,
                'avg_execution_time_ms': 0,
                'cache_hit_rate': 0,
                'error_rate': 0,
                'uptime_seconds': time.time() - self.start_time
            }
        
        recent_metrics = self.metrics_history[-20:]  # Last 20 executions
        
        execution_times = [m.execution_time_ms for m in recent_metrics]
        cache_hits = [m.cache_hit for m in recent_metrics]
        errors = [m.error_occurred for m in recent_metrics]
        
        return {
            'total_executions': len(self.metrics_history),
            'recent_executions': len(recent_metrics),
            'avg_execution_time_ms': sum(execution_times) / len(execution_times),
            'min_execution_time_ms': min(execution_times),
            'max_execution_time_ms': max(execution_times),
            'cache_hit_rate': sum(cache_hits) / len(cache_hits),
            'error_rate': sum(errors) / len(errors),
            'uptime_seconds': time.time() - self.start_time,
            'last_execution': recent_metrics[-1].timestamp if recent_metrics else None
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        summary = self.get_performance_summary()
        
        # Determine health status
        health_status = "HEALTHY"
        health_issues = []
        
        if summary['avg_execution_time_ms'] > 2000:
            health_status = "DEGRADED"
            health_issues.append("High execution time")
        
        if summary['cache_hit_rate'] < 0.5:
            health_status = "DEGRADED"
            health_issues.append("Low cache hit rate")
        
        if summary['error_rate'] > 0.1:
            health_status = "UNHEALTHY"
            health_issues.append("High error rate")
        
        if summary['recent_executions'] < 5:
            health_status = "DEGRADED"
            health_issues.append("Low execution count")
        
        return {
            'status': health_status,
            'issues': health_issues,
            'performance': summary,
            'recommendations': self._get_recommendations(summary, health_issues)
        }
    
    def _get_recommendations(self, summary: Dict[str, Any], issues: List[str]) -> List[str]:
        """Get performance recommendations"""
        recommendations = []
        
        if "High execution time" in issues:
            recommendations.append("Consider optimizing sentiment analysis algorithm")
            recommendations.append("Implement more aggressive caching")
        
        if "Low cache hit rate" in issues:
            recommendations.append("Increase cache TTL duration")
            recommendations.append("Implement pre-warming strategies")
        
        if "High error rate" in issues:
            recommendations.append("Review error logs and fix underlying issues")
            recommendations.append("Implement better error handling")
        
        if "Low execution count" in issues:
            recommendations.append("System may not be receiving regular traffic")
            recommendations.append("Check API Gateway configuration")
        
        if not issues:
            recommendations.append("System is performing well")
        
        return recommendations
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """Get error analysis"""
        error_metrics = [m for m in self.metrics_history if m.error_occurred]
        
        if not error_metrics:
            return {
                'total_errors': 0,
                'error_rate': 0,
                'common_errors': [],
                'recent_errors': []
            }
        
        # Analyze common errors
        error_messages = [m.error_message for m in error_metrics if m.error_message]
        error_counts = {}
        for msg in error_messages:
            error_counts[msg] = error_counts.get(msg, 0) + 1
        
        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        recent_errors = error_metrics[-5:]  # Last 5 errors
        
        return {
            'total_errors': len(error_metrics),
            'error_rate': len(error_metrics) / len(self.metrics_history),
            'common_errors': common_errors,
            'recent_errors': [
                {
                    'timestamp': m.timestamp,
                    'message': m.error_message,
                    'execution_time_ms': m.execution_time_ms
                }
                for m in recent_errors
            ]
        }


class GeopoliticalAlertManager:
    """Manage alerts for geopolitical analysis system"""
    
    def __init__(self):
        self.alert_thresholds = {
            'execution_time_ms': 3000,
            'error_rate': 0.2,
            'cache_hit_rate': 0.3
        }
        
    def check_alerts(self, monitor: GeopoliticalMonitor) -> List[Dict[str, Any]]:
        """Check for performance alerts"""
        alerts = []
        summary = monitor.get_performance_summary()
        
        # Execution time alert
        if summary['avg_execution_time_ms'] > self.alert_thresholds['execution_time_ms']:
            alerts.append({
                'type': 'PERFORMANCE',
                'severity': 'WARNING',
                'message': f"High execution time: {summary['avg_execution_time_ms']:.2f}ms",
                'threshold': self.alert_thresholds['execution_time_ms'],
                'current_value': summary['avg_execution_time_ms'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Error rate alert
        if summary['error_rate'] > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'ERROR_RATE',
                'severity': 'CRITICAL',
                'message': f"High error rate: {summary['error_rate']:.2%}",
                'threshold': self.alert_thresholds['error_rate'],
                'current_value': summary['error_rate'],
                'timestamp': datetime.now().isoformat()
            })
        
        # Cache hit rate alert
        if summary['cache_hit_rate'] < self.alert_thresholds['cache_hit_rate']:
            alerts.append({
                'type': 'CACHE_PERFORMANCE',
                'severity': 'WARNING',
                'message': f"Low cache hit rate: {summary['cache_hit_rate']:.2%}",
                'threshold': self.alert_thresholds['cache_hit_rate'],
                'current_value': summary['cache_hit_rate'],
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
