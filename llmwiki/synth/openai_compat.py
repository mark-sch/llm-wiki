"""OpenAI-compatible backend for local LLM synthesis (v1.0.0).

Provides ``OpenAISynthesizer``, a stdlib-only HTTP client for OpenAI-compatible
``/v1/chat/completions`` endpoints. This works with `llama-server` (llama.cpp),
vLLM, TGI, and any other server that implements the OpenAI chat protocol.

The dependency is **optional**: the default llmwiki install stays on stdlib +
``markdown``, and this module only touches ``urllib`` (also stdlib), so there
is nothing extra to install.

Design notes
------------
- **Privacy by default**: ``base_url`` defaults to 127.0.0.1. If the user
  points the backend at a remote host we log a warning once so they
  know they've left the local-only path.
- **Graceful fallback**: ``is_available()`` probes ``/v1/models`` with a
  short timeout. If the server is down ``synthesize_source_page()`` raises
  ``OpenAIUnavailableError``; the caller (``pipeline.synthesize_new_sessions``)
  catches that, logs a warning, and skips the file without crashing the
  sync.
- **Retries**: transient 5xx or ``socket.timeout`` errors retry with
  exponential backoff (default 3 attempts, 0.5/1.0/2.0s). Connection
  refused errors short-circuit — the server is simply not running.
- **No streaming**: we send ``stream: false`` because callers want the
  complete synthesised page back, not a token stream.
- **API key optional**: most local servers (llama-server, vLLM) do not
  require authentication. If ``api_key`` is set we emit
  ``Authorization: Bearer <api_key>``.

Configuration (``sessions_config.json`` / ``config.json``)::

    "synthesis": {
      "backend": "openai",
      "model":  "llama3.1:8b",
      "base_url": "http://127.0.0.1:8080/v1",
      "api_key": "",
      "timeout": 60,
      "max_retries": 3
    }

If ``base_url`` does not end with ``/v1`` we append it automatically so
``http://host:port`` works as well as ``http://host:port/v1``.
"""

from __future__ import annotations

import json
import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from llmwiki.synth.base import BaseSynthesizer

# ─── Constants ─────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_MODEL = "llama3.1:8b"
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.5

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

logger = logging.getLogger(__name__)


# ─── Exceptions ────────────────────────────────────────────────────────


class OpenAIError(RuntimeError):
    """Base class for OpenAI-compatible backend failures."""


class OpenAIUnavailableError(OpenAIError):
    """Raised when the server is unreachable (connection refused,
    DNS failure, or health check fails)."""


class OpenAIHTTPError(OpenAIError):
    """Raised when the server returns a non-2xx after exhausting retries."""

    def __init__(self, status: int, body: str):
        super().__init__(f"OpenAI-compatible server returned HTTP {status}: {body[:200]}")
        self.status = status
        self.body = body


# ─── Config ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OpenAIConfig:
    """Resolved configuration for :class:`OpenAISynthesizer`."""

    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_base: float = DEFAULT_BACKOFF_BASE

    @property
    def _normalized_base(self) -> str:
        """Return base_url with trailing /v1 if absent."""
        url = self.base_url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        return url

    @property
    def chat_url(self) -> str:
        return f"{self._normalized_base}/chat/completions"

    @property
    def models_url(self) -> str:
        return f"{self._normalized_base}/models"

    @property
    def is_local(self) -> bool:
        """True if base_url resolves to localhost (privacy check)."""
        try:
            host = urllib.parse.urlparse(self.base_url).hostname or ""
        except ValueError:
            return False
        return host in LOCAL_HOSTS


def load_openai_config(cfg: Optional[dict[str, Any]]) -> OpenAIConfig:
    """Build an :class:`OpenAIConfig` from the ``synthesis`` block of
    ``sessions_config.json``.

    Missing keys fall back to the module-level defaults so first-time
    users don't have to configure anything to try it out::

        { "synthesis": { "backend": "openai" } }

    is enough to reach a working local default.
    """
    synth = (cfg or {}).get("synthesis", {}) or {}
    model = synth.get("model") or DEFAULT_MODEL
    base_url = synth.get("base_url") or DEFAULT_BASE_URL
    api_key = str(synth.get("api_key", ""))
    timeout = int(synth["timeout"]) if "timeout" in synth else DEFAULT_TIMEOUT
    max_retries = (
        int(synth["max_retries"]) if "max_retries" in synth else DEFAULT_MAX_RETRIES
    )
    backoff_base = (
        float(synth["backoff_base"])
        if "backoff_base" in synth
        else DEFAULT_BACKOFF_BASE
    )

    if timeout <= 0:
        raise ValueError(f"synthesis.timeout must be positive, got {timeout}")
    if max_retries < 1:
        raise ValueError(f"synthesis.max_retries must be >= 1, got {max_retries}")

    resolved = OpenAIConfig(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
    )

    if not resolved.is_local:
        logger.warning(
            "OpenAI-compatible backend pointed at non-local host %s — transcript data "
            "will leave this machine. Set synthesis.base_url to http://127.0.0.1:8080 "
            "to restore privacy-by-default.",
            resolved.base_url,
        )

    return resolved


# ─── Synthesizer ───────────────────────────────────────────────────────


class OpenAISynthesizer(BaseSynthesizer):
    """Synthesize wiki source pages via an OpenAI-compatible HTTP server.

    The implementation uses only ``urllib`` so no third-party HTTP client
    is required. Test injection uses the ``http_post`` / ``http_get``
    kwargs so ``unittest.mock`` or a hand-rolled fake can substitute the
    transport layer without a real socket.
    """

    def __init__(
        self,
        config: Optional[OpenAIConfig] = None,
        *,
        http_post: Optional[Any] = None,
        http_get: Optional[Any] = None,
    ):
        self.config = config or OpenAIConfig()
        self._http_post = http_post or _urlopen_post
        self._http_get = http_get or _urlopen_get

    # ---- BaseSynthesizer interface --------------------------------

    def is_available(self) -> bool:
        """Probe ``/v1/models`` with a 2-second timeout.

        Returns True iff the server responds 2xx. Any exception
        (connection refused, DNS failure, HTTP 5xx, etc.) is swallowed
        and returns False — callers should branch on this before calling
        :meth:`synthesize_source_page`.
        """
        try:
            status, _ = self._http_get(
                self.config.models_url,
                headers=self._auth_headers(),
                timeout=min(self.config.timeout, 2),
            )
            return 200 <= status < 300
        except Exception as exc:  # noqa: BLE001 — probe must never raise
            logger.debug("OpenAI-compatible availability probe failed: %s", exc)
            return False

    def synthesize_source_page(
        self,
        raw_body: str,
        meta: dict[str, Any],
        prompt_template: str,
    ) -> str:
        """Render ``prompt_template`` with the session body + metadata
        and send it to the OpenAI-compatible endpoint. Returns the model's
        raw completion text.

        Raises
        ------
        OpenAIUnavailableError
            The server could not be reached at all (connection refused,
            DNS failure, etc.). Callers should skip synthesis and move on.
        OpenAIHTTPError
            The server returned a non-2xx response after all retries.
        """
        prompt = _render_prompt(prompt_template, raw_body=raw_body, meta=meta)
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        data = self._call_chat_completions(payload)
        content = _extract_content(data)
        if not isinstance(content, str):
            raise OpenAIError(
                f"OpenAI-compatible server returned non-string content: {type(content).__name__}"
            )
        return content.strip()

    # ---- internals -----------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _call_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to /v1/chat/completions with retry + backoff."""
        last_exc: Optional[Exception] = None
        headers = self._auth_headers()
        for attempt in range(1, self.config.max_retries + 1):
            try:
                status, body = self._http_post(
                    self.config.chat_url,
                    payload,
                    headers=headers,
                    timeout=self.config.timeout,
                )
            except OpenAIUnavailableError:
                raise
            except (socket.timeout, urllib.error.URLError) as exc:
                last_exc = exc
                logger.warning(
                    "OpenAI-compatible request attempt %d/%d failed: %s",
                    attempt,
                    self.config.max_retries,
                    exc,
                )
                if attempt == self.config.max_retries:
                    raise OpenAIError(f"OpenAI-compatible call failed: {exc}") from exc
                time.sleep(self.config.backoff_base * (2 ** (attempt - 1)))
                continue

            if 200 <= status < 300:
                try:
                    return json.loads(body)
                except (ValueError, json.JSONDecodeError) as exc:
                    raise OpenAIError(
                        f"OpenAI-compatible server returned non-JSON body: {exc}"
                    ) from exc

            if 500 <= status < 600 and attempt < self.config.max_retries:
                logger.warning(
                    "OpenAI-compatible server %s returned %d; retrying (%d/%d)",
                    self.config.chat_url,
                    status,
                    attempt,
                    self.config.max_retries,
                )
                time.sleep(self.config.backoff_base * (2 ** (attempt - 1)))
                continue

            raise OpenAIHTTPError(status, body)

        raise OpenAIError(f"OpenAI-compatible call failed after retries: {last_exc}")


# ─── HTTP transport (stdlib) ──────────────────────────────────────────


def _urlopen_post(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, str]:
    """POST JSON and return (status, body) as text. Raises
    :class:`OpenAIUnavailableError` on connection refused / DNS failure."""
    body = json.dumps(payload).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    req_headers.update(headers)
    req = urllib.request.Request(
        url,
        data=body,
        headers=req_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError):
            raise OpenAIUnavailableError(
                f"OpenAI-compatible server refused connection at {url}. "
                "Is the server running?"
            ) from exc
        if isinstance(reason, socket.gaierror):
            raise OpenAIUnavailableError(
                f"OpenAI-compatible host DNS lookup failed for {url}: {reason}"
            ) from exc
        raise


def _urlopen_get(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, str]:
    """GET and return (status, body). Same error-mapping rules as POST."""
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ConnectionRefusedError):
            raise OpenAIUnavailableError(
                f"OpenAI-compatible server refused connection at {url}."
            ) from exc
        if isinstance(reason, socket.gaierror):
            raise OpenAIUnavailableError(
                f"OpenAI-compatible host DNS lookup failed for {url}: {reason}"
            ) from exc
        raise


# ─── Response parsing ─────────────────────────────────────────────────


def _extract_content(data: dict[str, Any]) -> Any:
    """Extract the assistant content from an OpenAI chat completions response."""
    choices = data.get("choices")
    if not choices or not isinstance(choices, list):
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    return message.get("content")


# ─── Prompt rendering ─────────────────────────────────────────────────


def _render_prompt(
    template: str, *, raw_body: str, meta: dict[str, Any]
) -> str:
    """Substitute ``{body}`` and ``{meta}`` placeholders in the template.

    We deliberately use ``str.replace`` (not ``.format``) because session
    bodies contain ``{}`` in code blocks — calling ``.format`` there would
    raise ``KeyError``.
    """
    meta_dump = json.dumps(meta, indent=2, default=str, sort_keys=True)
    return template.replace("{body}", raw_body).replace("{meta}", meta_dump)
