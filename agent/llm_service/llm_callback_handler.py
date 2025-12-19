"""
LLM Callback Handler - Structured logging for LLM calls with OpenAI API format.

Ported from old_code with adapted imports for agent/ structure.
Provides observability for LLM requests/responses with redaction support.
"""
import json
import logging
import re
import time
from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Dict
from uuid import uuid4

from langchain_core.callbacks.base import BaseCallbackHandler

from agent.llm_service.llm_callback_utils import parse_log_to_blocks, build_messages_from_blocks
from agent.utils.logging import log_llm_call


class Verbosity(Enum):
    """Logging verbosity levels."""
    MINIMAL = 0    # only final answer + errors
    NORMAL = 1     # prompts + final answers + tool calls
    VERBOSE = 2    # include intermediate agent actions + tokens
    DEBUG = 3      # everything (full serialized objects)


def _redact(text: str, patterns: List[re.Pattern]) -> str:
    """Redact sensitive information from text using regex patterns."""
    if not text:
        return text
    for p in patterns:
        text = p.sub("[REDACTED]", text)
    return text


class LoggingLLMCallbackHandler(BaseCallbackHandler):
    """
    Callback handler for structured LLM logging in OpenAI API format.
    
    Features:
    - Multi-level verbosity control
    - Sensitive data redaction
    - OpenAI API format standardization
    - External sink support for metrics/monitoring
    """
    
    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        verbosity: Verbosity = Verbosity.NORMAL,
        redact_patterns: Optional[List[str]] = None,
        external_sink: Optional[callable] = None,  # function(record: dict) -> None
    ):
        self.verbosity = verbosity
        self.logger = logger or logging.getLogger("langchain_logger")
        self.external_sink = external_sink
        self.current_run_id: Optional[str] = None
        self.redact_patterns = [re.compile(p) for p in (redact_patterns or [])]
        self.llm_start_time: Optional[float] = None  # Track LLM call timing

    def _emit(self, level: str, message: str, meta: Optional[Dict[str, Any]] = None):
        """Emit structured log entry."""
        ts = datetime.utcnow().isoformat() + "Z"
        run_id = self.current_run_id or str(uuid4())
        log_entry = {
            "ts": ts,
            "run_id": run_id,
            "level": level,
            "message": _redact(message, self.redact_patterns),
            "meta": meta or {}
        }
        # write to python logger (string)
        if level == "ERROR":
            self.logger.error(json.dumps(log_entry, ensure_ascii=False, indent=4))
        elif level == "WARN":
            self.logger.warning(json.dumps(log_entry, ensure_ascii=False, indent=4))
        elif level == "DEBUG":
            self.logger.debug(json.dumps(log_entry, ensure_ascii=False, indent=4))
        else:
            self.logger.info(json.dumps(log_entry, ensure_ascii=False))

        # send to external sink if provided (structured)
        if self.external_sink:
            try:
                self.external_sink(log_entry)
            except Exception as e:
                # don't break main flow if sink fails
                self.logger.warning("external_sink failed: %s", str(e))

    # Lifecycle callbacks
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs):
        """Called when a chain/agent run starts."""
        self.current_run_id = kwargs.get("run_id") or str(uuid4())
        if self.verbosity.value >= Verbosity.NORMAL.value:
            self._emit("INFO", "chain_start", {
                "chain": serialized.get("name"), 
                "inputs": _redact(json.dumps(inputs), self.redact_patterns)
            })

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs):
        """Called when a chain/agent run ends."""
        if self.verbosity.value >= Verbosity.MINIMAL.value:
            self._emit("INFO", "chain_end", {
                "outputs": _redact(json.dumps(outputs), self.redact_patterns)
            })

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        """Called when LLM starts - log in OpenAI API format."""
        self.llm_start_time = time.time()  # Start timing
        
        if self.verbosity.value >= Verbosity.NORMAL.value:
            # Format request in OpenAI API standard format
            model = serialized.get("kwargs", {}).get("model_name", "unknown_model")

            # Extract messages from prompts
            messages = []
            for log in prompts:
                blocks = parse_log_to_blocks(log)
                msgs = build_messages_from_blocks(blocks)
                messages.extend(msgs)

            # Extract tools from kwargs
            tools = kwargs.get("invocation_params", {}).get("tools", [])

            # Create OpenAI API format request
            openai_request = {
                "model": model,
                "messages": messages,
                "tools": tools
            }

            # Add tool_choice if tools are present
            if tools:
                openai_request["tool_choice"] = "required"

            self._emit("INFO", "llm_start", {"request": openai_request})
        elif self.verbosity == Verbosity.MINIMAL:
            # minimal: maybe log only number of prompts
            self._emit("INFO", "llm_start_minimal", {"n_prompts": len(prompts)})

    def on_llm_new_token(self, token: str, **kwargs):
        """Called on each new token in streaming - only log if VERBOSE or DEBUG."""
        if self.verbosity.value >= Verbosity.VERBOSE.value:
            self._emit("DEBUG", "llm_token", {"token": _redact(token, self.redact_patterns)})

    def on_llm_end(self, response: Any, **kwargs):
        """Called when LLM completes - log in OpenAI API format."""
        # Calculate duration
        duration_ms = None
        if self.llm_start_time:
            duration_ms = (time.time() - self.llm_start_time) * 1000
            
        if self.verbosity.value >= Verbosity.NORMAL.value:
            try:
                # Create OpenAI API format response
                llm_output = getattr(response, "llm_output", None) or {}
                run_id = kwargs.get("run_id")
                run_id_str = str(run_id) if run_id else str(uuid4())
                
                model = llm_output.get("model_name", "unknown_model")
                token_usage = llm_output.get("token_usage", {})
                prompt_tokens = token_usage.get("prompt_tokens", 0)
                completion_tokens = token_usage.get("completion_tokens", 0)
                
                openai_response = {
                    "id": llm_output.get("id") or run_id_str,
                    "object": "chat.completion",
                    "created": int(datetime.utcnow().timestamp()),
                    "model": model,
                    "choices": [],
                    "usage": token_usage or {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    },
                    "system_fingerprint": None
                }

                # Extract choices from generations
                gens = getattr(response, "generations", None)
                if gens:
                    for i, gen_list in enumerate(gens):
                        for g in gen_list:
                            choice = {
                                "index": i,
                                "message": {
                                    "role": "assistant" if getattr(getattr(g, "message", {}), "type", "ai") == "ai" else "user",
                                    "content": _redact(getattr(getattr(g, "message", {}), "content", ""), self.redact_patterns),
                                    "tool_calls": getattr(getattr(g, "message", {}), "tool_calls", None)
                                },
                                "logprobs": getattr(getattr(getattr(g, "message", {}), "response_metadata", {}), "logprobs", None),
                                "finish_reason": getattr(getattr(getattr(g, "message", {}), "response_metadata", {}), "finish_reason", "stop")
                            }
                            openai_response["choices"].append(choice)

                self._emit("INFO", "llm_end", {"response": openai_response})
                
                # Use simplified logging helper
                log_llm_call(
                    self.logger,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    duration_ms=duration_ms
                )
                
            except Exception as e:
                # Fallback to simple text response if parsing fails
                self.logger.warning(f"Failed to format OpenAI response: {str(e)}")
                try:
                    text = str(response)
                    self._emit("INFO", "llm_end", {"response_text": _redact(text, self.redact_patterns)})
                except Exception:
                    self._emit("ERROR", "llm_end_error", {"error": "Failed to format response"})

    def on_llm_error(self, error: Exception, **kwargs):
        """Called when LLM errors."""
        self._emit("ERROR", "llm_error", {"error": str(error)})

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        """Called when tool starts."""
        if self.verbosity.value >= Verbosity.NORMAL.value:
            self._emit("INFO", "tool_start", {
                "tool": serialized.get("name"), 
                "input": _redact(input_str, self.redact_patterns)
            })

    def on_tool_end(self, output: str, **kwargs):
        """Called when tool ends."""
        if self.verbosity.value >= Verbosity.NORMAL.value:
            self._emit("INFO", "tool_end", {"output": _redact(output, self.redact_patterns)})

    def on_agent_action(self, action: Dict[str, Any], **kwargs):
        """Called on agent action - only log if VERBOSE."""
        if self.verbosity.value >= Verbosity.VERBOSE.value:
            self._emit("INFO", "agent_action", {
                "action": _redact(json.dumps(action), self.redact_patterns)
            })

    def on_agent_finish(self, finish: Dict[str, Any], **kwargs):
        """Called when agent finishes."""
        if self.verbosity.value >= Verbosity.MINIMAL.value:
            self._emit("INFO", "agent_finish", {
                "return_values": _redact(json.dumps(finish), self.redact_patterns)
            })
