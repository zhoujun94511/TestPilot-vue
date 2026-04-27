#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Utility helpers for normalizing service-layer errors."""

from __future__ import annotations

import traceback
from typing import Any, Dict

from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    @staticmethod
    def handle_document_analysis_error(error: Exception, file_path: str) -> Dict[str, Any]:
        """Normalize document-analysis failures for upper layers."""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "file_path": file_path,
            "traceback": traceback.format_exc(),
        }

        logger.error("Document analysis error: %s", error_info)

        if "Unsupported file format" in str(error):
            return {
                "user_message": "Unsupported file format. Please upload a .txt, .md, .docx, or .csv file.",
                "message_key": "errors.document.unsupportedFormat",
                "message": "Unsupported file format. Please upload a .txt, .md, .docx, or .csv file.",
                "error_code": "UNSUPPORTED_FORMAT",
            }
        if "FileNotFoundError" in str(error):
            return {
                "user_message": "File not found. Please check the file path.",
                "message_key": "errors.document.fileNotFound",
                "message": "File not found. Please check the file path.",
                "error_code": "FILE_NOT_FOUND",
            }
        return {
            "user_message": "Document analysis failed. Please check the file contents and try again.",
            "message_key": "errors.document.analysisFailed",
            "message": "Document analysis failed. Please check the file contents and try again.",
            "error_code": "ANALYSIS_FAILED",
        }

    @staticmethod
    def handle_batch_processing_error(error: Exception, batch_info: Dict) -> Dict[str, Any]:
        """Normalize batch-processing failures for upper layers."""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "batch_info": batch_info,
            "traceback": traceback.format_exc(),
        }

        logger.error("Batch processing error: %s", error_info)

        batch_id = batch_info.get("batch_id", "unknown")
        return {
            "user_message": f"Batch {batch_id} processing failed.",
            "message_key": "errors.batch.processingFailed",
            "message": f"Batch {batch_id} processing failed.",
            "error_code": "BATCH_PROCESSING_FAILED",
            "retry_suggested": True,
        }

    @staticmethod
    def handle_llm_error(error: Exception, prompt: str) -> Dict[str, Any]:
        """Normalize LLM failures for upper layers."""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "prompt_length": len(prompt),
            "traceback": traceback.format_exc(),
        }

        logger.error("LLM error: %s", error_info)

        lowered = str(error).lower()
        if "timeout" in lowered:
            return {
                "user_message": "Request timed out. Please try again later.",
                "message_key": "errors.llm.timeout",
                "message": "Request timed out. Please try again later.",
                "error_code": "TIMEOUT",
                "retry_suggested": True,
            }
        if "rate limit" in lowered:
            return {
                "user_message": "Request rate is too high. Please try again later.",
                "message_key": "errors.llm.rateLimit",
                "message": "Request rate is too high. Please try again later.",
                "error_code": "RATE_LIMIT",
                "retry_suggested": True,
            }
        return {
            "user_message": "The AI service is temporarily unavailable. Please try again later.",
            "message_key": "errors.llm.unavailable",
            "message": "The AI service is temporarily unavailable. Please try again later.",
            "error_code": "LLM_ERROR",
            "retry_suggested": True,
        }
