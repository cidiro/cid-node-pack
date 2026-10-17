import base64
import io
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from ..utils.json_utils import extract_json_from_string


class CidLLMChat:
    """
    Chat with an OpenAI-compatible LLM server (e.g. llama.cpp llama-server).
    Optionally constrains the response to a JSON Schema (structured output).
    """

    ALLOWED_ROLES = {"system", "developer", "user", "assistant", "tool"}
    HEALTH_TIMEOUT_S = 10
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response", "raw_response", "messages")
    OUTPUT_TOOLTIPS = (
        "Assistant's response text extracted from the first completion choice.",
        "Raw /v1/chat/completions JSON response.",
        "Updated conversation history including prior messages, current user prompt, and the assistant's response.",
    )
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/LLM"
    HEALTH_ENDPOINT_CANDIDATES = ("v1/health", "health", "v1/models")
    MODEL_LOAD_ENDPOINT_CANDIDATES = ("models/load", "v1/models/load")
    VISION_PROPS_ENDPOINT = "props"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": (
                            "User prompt text, sent as the last user message. "
                            "Wire from a text-producing node (e.g. a wildcard processor or JSON get node)."
                        ),
                    },
                ),
                "model": ("STRING", {"default": "local-model"}),
            },
            "optional": {
                "messages": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": (
                            "OpenAI-style messages JSON. "
                            "Accepts either an array of message objects "
                            '[{"role":"user","content":"..."}] or an object '
                            'with a "messages" array. The current user prompt is added as the last user message.'
                        ),
                    },
                ),
                "images": (
                    "IMAGE",
                    {
                        "tooltip": (
                            "Optional image(s) attached to the user prompt for vision-capable models. "
                            "A batch attaches multiple images."
                        ),
                    },
                ),
                "json_schema": (
                    "STRING",
                    {
                        "default": "",
                        "forceInput": True,
                        "tooltip": (
                            "Optional JSON Schema object constraining the response to structured JSON "
                            '(sent as response_format, e.g. {"type": "object", "properties": ...}). '
                            "Supported by llama.cpp llama-server, vLLM, LM Studio, and OpenAI. "
                            "Leave unconnected for unconstrained text output."
                        ),
                    },
                ),
                "base_url": ("STRING", {"default": "http://127.0.0.1:8080"}),
                "temperature": (
                    "FLOAT", 
                    {
                        "default": 0.6,
                        "min": 0.0,
                        "max": 2.0,
                        "step": 0.01,
                        "tooltip": "Temperature parameter for controlling randomness.",
                    },
                ),
                "top_p": (
                    "FLOAT",
                    {
                        "default": 0.95,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Nucleus sampling threshold.",
                    },
                ),
                "top_k": (
                    "INT",
                    {
                        "default": 20,
                        "min": -1,
                        "max": 100000,
                        "tooltip": "Top-k sampling value. -1 lets the server default apply.",
                    },
                ),
                "min_p": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 1.0,
                        "step": 0.01,
                        "tooltip": "Minimum probability sampling floor.",
                    },
                ),
                "presence_penalty": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "step": 0.01,
                        "tooltip": "Penalty for repeating existing topics.",
                    },
                ),
                "repeat_penalty": (
                    "FLOAT",
                    {
                        "default": 1.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "tooltip": "Token repetition penalty (1.0 means neutral).",
                    },
                ),
                "repeat_last_n": (
                    "INT",
                    {
                        "default": 64,
                        "min": -1,
                        "max": 131072,
                        "tooltip": "How many recent tokens repetition penalty applies to.",
                    },
                ),
                "dry_multiplier": (
                    "FLOAT",
                    {
                        "default": 0.0,
                        "min": 0.0,
                        "max": 10.0,
                        "step": 0.01,
                        "tooltip": "DRY decoding multiplier (0.0 disables DRY).",
                    },
                ),
                "max_completion_tokens": (
                    "INT",
                    {
                        "default": -1,
                        "min": -1,
                        "max": 131072,
                        "tooltip": (
                            "Maximum completion tokens. "
                            "Set to -1 or 0 to omit this field from the request."
                        ),
                    },
                ),
            },
        }

    def _normalize_base_url(self, base_url):
        normalized = (base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("Input 'base_url' cannot be empty.")
        if not normalized.startswith("http://") and not normalized.startswith("https://"):
            raise ValueError("Input 'base_url' must start with 'http://' or 'https://'.")
        return normalized

    def _parse_messages(self, messages):
        raw = (messages or "").strip()
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in 'messages': {exc}") from exc

        if isinstance(parsed, dict):
            if "messages" not in parsed:
                raise ValueError("When 'messages' is an object, it must contain a 'messages' array.")
            parsed = parsed["messages"]

        if not isinstance(parsed, list):
            raise TypeError("Input 'messages' must be a JSON array of messages or an object with a 'messages' array.")

        validated = []
        for index, message in enumerate(parsed):
            if not isinstance(message, dict):
                raise TypeError(f"Message at index {index} must be an object.")

            role = message.get("role")
            if not isinstance(role, str) or not role.strip():
                raise ValueError(f"Message at index {index} is missing a valid 'role'.")

            role = role.strip()
            if role not in self.ALLOWED_ROLES:
                allowed_roles = ", ".join(sorted(self.ALLOWED_ROLES))
                raise ValueError(
                    f"Message at index {index} has unsupported role '{role}'. Supported roles: {allowed_roles}."
                )

            if "content" not in message:
                raise ValueError(f"Message at index {index} is missing 'content'.")

            validated.append(message)

        return validated

    def _encode_images(self, images):
        """Convert a ComfyUI IMAGE tensor batch into base64 PNG data URLs."""
        if images is None:
            return []

        import numpy as np
        from PIL import Image

        data_urls = []
        for image in images:
            array = np.clip(255.0 * image.cpu().numpy(), 0, 255).astype(np.uint8)
            pil_image = Image.fromarray(array)
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            data_urls.append(f"data:image/png;base64,{encoded}")

        return data_urls

    def _build_messages(self, user_prompt, messages, image_urls=None):
        user_prompt_value = (user_prompt or "").strip()
        if not user_prompt_value:
            raise ValueError("Input 'user_prompt' cannot be empty.")

        provided_messages = self._parse_messages(messages)
        history = list(provided_messages) if provided_messages is not None else []

        if image_urls:
            content = [{"type": "text", "text": user_prompt_value}]
            content += [
                {"type": "image_url", "image_url": {"url": url}} for url in image_urls
            ]
            history.append({"role": "user", "content": content})
        else:
            history.append({"role": "user", "content": user_prompt_value})

        return history

    def _request_json(self, method, url, payload=None):
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                response_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"{method} {url} failed: {exc}") from exc

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{method} {url} returned invalid JSON: {exc}") from exc

    def _build_connection_refused_hint(self, url):
        try:
            host = (urllib.parse.urlparse(url).hostname or "").lower()
        except Exception:
            host = ""

        if host in {"127.0.0.1", "localhost", "::1"}:
            return (
                " If ComfyUI runs in Docker and llama-server runs on the host machine, "
                "127.0.0.1/localhost points to the container itself. "
                "Use 'http://host.docker.internal:8080' or your host LAN IP as 'base_url'."
            )
        return ""

    def _health_check(self, base_url_value):
        headers = {"Accept": "application/json"}
        non_404_errors = []
        missing_endpoint_count = 0

        for endpoint in self.HEALTH_ENDPOINT_CANDIDATES:
            url = urllib.parse.urljoin(f"{base_url_value}/", endpoint)
            request = urllib.request.Request(url=url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=self.HEALTH_TIMEOUT_S):
                    return
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                if exc.code in (404, 405):
                    missing_endpoint_count += 1
                    continue
                non_404_errors.append(f"GET {url} failed with HTTP {exc.code}: {error_body}")
                continue
            except urllib.error.URLError as exc:
                reason = exc.reason
                if isinstance(reason, ConnectionRefusedError) or (
                    isinstance(reason, OSError) and reason.errno == 111
                ):
                    hint = self._build_connection_refused_hint(url)
                    raise RuntimeError(f"GET {url} failed: {reason}.{hint}") from exc
                raise RuntimeError(f"GET {url} failed: {reason}") from exc
            except socket.timeout as exc:
                raise RuntimeError(f"GET {url} failed: timed out after {self.HEALTH_TIMEOUT_S}s") from exc
            except Exception as exc:
                raise RuntimeError(f"GET {url} failed: {exc}") from exc

        if missing_endpoint_count == len(self.HEALTH_ENDPOINT_CANDIDATES) and not non_404_errors:
            print("[CidLLMChat] Warning: No known health endpoint found, skipping preflight health check.")
            return

        if non_404_errors:
            raise RuntimeError(non_404_errors[0])

        raise RuntimeError("LLM server health check failed: no reachable endpoint.")

    def _get_loaded_models(self, base_url_value):
        """Fetch the list of currently loaded models from the server."""
        models_url = urllib.parse.urljoin(f"{base_url_value}/", "v1/models")
        try:
            response = self._request_json("GET", models_url)
            loaded_models = []
            for model in response.get("data", []):
                model_id = model.get("id")
                # llama-server in router mode might list all known models, even unloaded ones
                status = model.get("status", {})
                if model_id and status.get("value") != "unloaded":
                    loaded_models.append(model_id)
            return loaded_models
        except Exception as exc:
            print(f"[CidLLMChat] Warning: Could not fetch loaded models: {exc}")
            return []

    def _ensure_model_loaded(self, base_url_value, model_name):
        """Ensure requested model is loaded in VRAM, loading it when needed."""
        print(f"[CidLLMChat] Checking if model '{model_name}' is already loaded...")
        loaded_models = self._get_loaded_models(base_url_value)
        if model_name in loaded_models:
            print(f"[CidLLMChat] Model '{model_name}' is already loaded.")
            return

        print(f"[CidLLMChat] Model '{model_name}' not loaded. Requesting server to load it...")
        last_error = None

        for endpoint in self.MODEL_LOAD_ENDPOINT_CANDIDATES:
            load_url = urllib.parse.urljoin(f"{base_url_value}/", endpoint)
            try:
                self._request_json("POST", load_url, payload={"model": model_name})
                print(f"[CidLLMChat] Successfully loaded '{model_name}'.")
                return
            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                if "HTTP 404" in error_text or "HTTP 405" in error_text:
                    continue
                break

        if last_error is not None:
            print(
                f"[CidLLMChat] Warning: Could not pre-load model '{model_name}'. "
                f"Continuing; server may auto-load on first request. Last error: {last_error}"
            )

    @staticmethod
    def _extract_vision_flag(container):
        """Read a vision-capability boolean from a modalities/capabilities object."""
        if not isinstance(container, dict):
            return None

        modalities = container.get("modalities")
        if isinstance(modalities, dict) and "vision" in modalities:
            return bool(modalities["vision"])
        if isinstance(modalities, list):
            return "vision" in modalities

        capabilities = container.get("capabilities")
        if isinstance(capabilities, dict) and "vision" in capabilities:
            return bool(capabilities["vision"])
        if isinstance(capabilities, list):
            return "vision" in capabilities

        return None

    def _check_vision_capability(self, base_url_value, model_name):
        """Determine whether the loaded model supports image input.

        Returns True (capable), False (positively not capable), or None (unknown).
        Request failures are swallowed and reported as unknown so that older
        servers which don't expose capability info don't block valid models.
        """
        props_url = urllib.parse.urljoin(f"{base_url_value}/", self.VISION_PROPS_ENDPOINT)
        try:
            props = self._request_json("GET", props_url)
            flag = self._extract_vision_flag(props)
            if flag is not None:
                return flag
        except Exception as exc:
            print(f"[CidLLMChat] Warning: Could not read '{self.VISION_PROPS_ENDPOINT}' for vision capability: {exc}")

        models_url = urllib.parse.urljoin(f"{base_url_value}/", "v1/models")
        try:
            response = self._request_json("GET", models_url)
            for model in response.get("data", []):
                if model.get("id") == model_name:
                    flag = self._extract_vision_flag(model)
                    if flag is not None:
                        return flag
        except Exception as exc:
            print(f"[CidLLMChat] Warning: Could not read '/v1/models' for vision capability: {exc}")

        return None

    def _extract_assistant_text(self, completion_json):
        choices = completion_json.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Chat completion response is missing a non-empty 'choices' array.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ValueError("Chat completion response contains an invalid choice object.")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ValueError("Chat completion response choice is missing a valid 'message' object.")

        content = message.get("content")
        if isinstance(content, str):
            if content:
                return content

        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            text_content = "".join(parts)
            if text_content:
                return text_content

        reasoning_content = message.get("reasoning_content")
        if isinstance(reasoning_content, str):
            return reasoning_content

        if isinstance(reasoning_content, list):
            parts = []
            for part in reasoning_content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)

        return ""

    def _build_updated_messages(self, request_messages, completion_json, assistant_text):
        updated_messages = list(request_messages)
        assistant_message = {"role": "assistant", "content": assistant_text}

        choices = completion_json.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    assistant_message = dict(message)
                    if "role" not in assistant_message:
                        assistant_message["role"] = "assistant"
                    if "content" not in assistant_message:
                        assistant_message["content"] = assistant_text

        updated_messages.append(assistant_message)
        return updated_messages

    JSON_SCHEMA_TYPE_CHECKS = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }

    def _parse_json_schema(self, json_schema):
        """Parse the optional json_schema input into a schema object.

        Returns None when the input is empty. Tolerates markdown fences around
        the schema (common when pasting from documentation).
        """
        raw = extract_json_from_string(json_schema or "")
        if not raw.strip():
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid JSON in 'json_schema': {exc}. Provide a JSON Schema object "
                '(a JSON object describing the expected response, e.g. a schema with "type": "object"), '
                "or leave it empty."
            ) from exc

        if not isinstance(parsed, dict):
            raise ValueError("Input 'json_schema' must be a JSON Schema object (a JSON object at the top level).")

        return parsed

    def _build_payload(
        self,
        model_name,
        request_messages,
        parsed_schema,
        temperature,
        top_p,
        top_k,
        min_p,
        presence_penalty,
        repeat_penalty,
        repeat_last_n,
        dry_multiplier,
        max_completion_tokens,
    ):
        payload = {
            "model": model_name,
            "messages": request_messages,
            "stream": False,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "top_k": int(top_k),
            "min_p": float(min_p),
            "presence_penalty": float(presence_penalty),
            "repeat_penalty": float(repeat_penalty),
            "repeat_last_n": int(repeat_last_n),
            "dry_multiplier": float(dry_multiplier),
        }
        max_completion_tokens_value = int(max_completion_tokens)
        if max_completion_tokens_value > 0:
            payload["max_completion_tokens"] = max_completion_tokens_value

        if parsed_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "strict": True,
                    "schema": parsed_schema,
                },
            }

        return payload

    def _validate_structured_response(self, assistant_text, parsed_schema):
        """Best-effort check that a schema-constrained response is usable JSON.

        Servers that honor response_format guarantee conformance; this catches
        servers that silently ignore it, so downstream JSON nodes don't fail
        with a confusing parse error.
        """
        cleaned = extract_json_from_string(assistant_text or "")
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "A json_schema was requested, but the server returned a response that is not valid JSON "
                f"(parse error: {exc}). The server may not support schema-constrained output "
                "(response_format with type 'json_schema')."
            ) from exc

        declared_type = parsed_schema.get("type")
        if isinstance(declared_type, str):
            declared_type = [declared_type]
        if not isinstance(declared_type, list):
            return

        checks = [self.JSON_SCHEMA_TYPE_CHECKS[name] for name in declared_type if name in self.JSON_SCHEMA_TYPE_CHECKS]
        if checks and not any(check(parsed) for check in checks):
            raise RuntimeError(
                "A json_schema was requested, but the response's top-level JSON type does not match "
                f"the schema type '{parsed_schema.get('type')}'. The server may not support "
                "schema-constrained output (response_format with type 'json_schema')."
            )

    def main(
        self,
        user_prompt,
        model,
        messages="",
        images=None,
        json_schema="",
        base_url="http://127.0.0.1:8080",
        temperature=0.7,
        top_p=0.95,
        top_k=40,
        min_p=0.05,
        presence_penalty=0.0,
        repeat_penalty=1.0,
        repeat_last_n=64,
        dry_multiplier=0.0,
        max_completion_tokens=-1,
    ):
        model_name = (model or "").strip()
        if not model_name:
            raise ValueError("Input 'model' cannot be empty.")

        base_url_value = self._normalize_base_url(base_url)

        self._health_check(base_url_value)
        self._ensure_model_loaded(base_url_value, model_name)

        image_urls = self._encode_images(images)
        if image_urls:
            print(f"[CidLLMChat] Attaching {len(image_urls)} image(s) to the user prompt.")
            if self._check_vision_capability(base_url_value, model_name) is False:
                raise ValueError(
                    f"Model '{model_name}' is not vision-capable, but image input was provided. "
                    "Load a multimodal model (with an mmproj vision projector) to describe or "
                    "analyze images, or disconnect the 'images' input."
                )

        request_messages = self._build_messages(user_prompt, messages, image_urls)

        parsed_schema = self._parse_json_schema(json_schema)
        if parsed_schema is not None:
            print("[CidLLMChat] Structured output enabled: constraining the response with the provided json_schema.")

        payload = self._build_payload(
            model_name=model_name,
            request_messages=request_messages,
            parsed_schema=parsed_schema,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            min_p=min_p,
            presence_penalty=presence_penalty,
            repeat_penalty=repeat_penalty,
            repeat_last_n=repeat_last_n,
            dry_multiplier=dry_multiplier,
            max_completion_tokens=max_completion_tokens,
        )

        completion_url = urllib.parse.urljoin(f"{base_url_value}/", "v1/chat/completions")
        print(f"[CidLLMChat] Generating response with model '{model_name}'...")
        generation_started_at = time.perf_counter()
        try:
            completion_json = self._request_json(
                "POST",
                completion_url,
                payload=payload,
            )
        except RuntimeError as exc:
            if image_urls:
                raise RuntimeError(
                    f"{exc} This request included image input; the server may have rejected it "
                    f"because model '{model_name}' is not vision-capable or the server was started "
                    "without a multimodal (mmproj) projector."
                ) from exc
            raise
        generation_elapsed_ms = (time.perf_counter() - generation_started_at) * 1000.0

        usage = completion_json.get("usage") if isinstance(completion_json, dict) else None
        if isinstance(usage, dict):
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
            print(
                f"[CidLLMChat] Response generated in {generation_elapsed_ms:.1f} ms "
                f"(prompt_tokens={prompt_tokens}, completion_tokens={completion_tokens}, total_tokens={total_tokens})."
            )
        else:
            print(f"[CidLLMChat] Response generated in {generation_elapsed_ms:.1f} ms.")

        assistant_text = self._extract_assistant_text(completion_json)
        if parsed_schema is not None:
            self._validate_structured_response(assistant_text, parsed_schema)
        updated_messages = self._build_updated_messages(request_messages, completion_json, assistant_text)

        return (
            assistant_text,
            json.dumps(completion_json, ensure_ascii=False, indent=2),
            json.dumps(updated_messages, ensure_ascii=False, indent=2),
        )
