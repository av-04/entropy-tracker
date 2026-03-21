"""
Alert Engine — evaluates alert rules against module scores.

Fires alerts when modules cross configurable thresholds:
- entropy_score > 85 → CRITICAL
- knowledge_score > 90 → CRITICAL
- bus_factor == 1 → HIGH
- trend_per_month > 5 → WATCH
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from entropy.scoring.scorer import ModuleScore

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """A single alert rule defined by a condition string."""
    condition: str
    severity: str  # CRITICAL, HIGH, WATCH


@dataclass
class Alert:
    """A fired alert."""

    id: str = field(default_factory=lambda: str(uuid4()))
    module_path: str = ""
    severity: str = ""
    message: str = ""
    fired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "module_path": self.module_path,
            "severity": self.severity,
            "message": self.message,
            "fired_at": self.fired_at.isoformat(),
            "resolved": self.resolved,
        }


# Default alert rules matching the plan priorities to aggressively eliminate noise
DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule(condition="entropy_score > 85", severity="CRITICAL"),
    AlertRule(condition="knowledge_score > 90 and entropy_score > 40", severity="CRITICAL"),
    AlertRule(condition="bus_factor == 1 and entropy_score > 35", severity="HIGH"),
    AlertRule(condition="trend_per_month > 5 and entropy_score > 30", severity="WATCH"),
]

def _evaluate_condition(condition: str, score: ModuleScore) -> bool:
    """
    Safely evaluate a condition string against a score object.
    Supports basic numeric comparisons and 'and'/'or'.
    """
    allowed_names = {
        "entropy_score": float(score.entropy_score),
        "knowledge_score": float(score.knowledge_score),
        "dep_score": float(score.dep_score),
        "churn_score": float(score.churn_score),
        "age_score": float(score.age_score),
        "bus_factor": int(score.bus_factor),
        "trend_per_month": float(score.trend_per_month),
    }

    # very simple safe eval
    try:
        # replace identifiers with values
        expr = condition.lower()
        for name, val in allowed_names.items():
            expr = re.sub(rf'\b{name}\b', str(val), expr)
            
        # evaluate the final boolean expression safely
        return eval(expr, {"__builtins__": None}, {})
    except Exception as e:
        logger.error(f"Failed to evaluate rule condition '{condition}': {e}")
        return False


def _build_message(rule: AlertRule, module_path: str) -> str:
    """Creates a human-readable message from a matched rule."""
    return f"Module {module_path} violated rule: {rule.condition}"


class AlertEngine:
    """Evaluate alert rules against a set of module scores."""

    def __init__(self, rules: list[AlertRule] | None = None):
        self.rules = rules or DEFAULT_ALERT_RULES

    def evaluate(self, scores: dict[str, ModuleScore]) -> list[Alert]:
        """
        Check all modules against all rules.
        Returns a list of fired alerts.
        """
        alerts: list[Alert] = []

        for path, score in scores.items():
            for rule in self.rules:
                if _evaluate_condition(rule.condition, score):
                    alert = Alert(
                        module_path=path,
                        severity=rule.severity,
                        message=_build_message(rule, path),
                    )
                    alerts.append(alert)
                    logger.info("Alert fired: [%s] %s", rule.severity, alert.message)

        return alerts
