#!/usr/bin/python
# -*- coding: utf-8 -*-
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class ActionRequest:
    """Normalized action request from API/chat."""
    query: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    require_confirmation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPlan:
    """Tool invocation plan inferred from natural language."""
    intent: str
    tool_name: str
    args: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    reason: str = ""
    requires_confirmation: bool = False


@dataclass
class ActionResult:
    """Unified action execution result for frontend/API."""
    success: bool
    execution_id: str
    message: str
    status: str = "done"
    plan: Optional[ActionPlan] = None
    tool_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

