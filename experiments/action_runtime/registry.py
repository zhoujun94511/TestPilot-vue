#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Callable, Dict, Any


class ToolRegistry:
    """In-memory registry for experimental tools.

    Keep this registry isolated from core services to make the feature
    detachable with minimal side effects.
    """

    def __init__(self):
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self._risk_levels: Dict[str, str] = {}

    def register(self, name: str, handler: Callable[..., Dict[str, Any]], risk_level: str = "low") -> None:
        self._tools[name] = handler
        self._risk_levels[name] = risk_level

    def get(self, name: str) -> Callable[..., Dict[str, Any]] | None:
        return self._tools.get(name)

    def get_risk_level(self, name: str) -> str:
        return self._risk_levels.get(name, "low")

    def list_tools(self) -> Dict[str, str]:
        return {name: self._risk_levels.get(name, "low") for name in self._tools}

