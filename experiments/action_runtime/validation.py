#!/usr/bin/python
# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class ExecuteRequestModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    query: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=100)
    user_id: Optional[str] = Field(default=None, max_length=100)
    require_confirmation: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfirmRequestModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    execution_id: str = Field(..., min_length=1, max_length=64)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CancelRequestModel(BaseModel):
    model_config = ConfigDict(extra='ignore')

    execution_id: str = Field(..., min_length=1, max_length=64)
    reason: str = Field(default="", max_length=500)

