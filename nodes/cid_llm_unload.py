import urllib.parse
import urllib.request
import json
from ..utils import any_type


class CidLLMUnload:
    """
    Unloads the currently loaded model from an OpenAI-compatible LLM server (e.g. llama.cpp llama-server)
    to free up VRAM. Acts as a passthrough for the 'any' input.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_url": ("STRING", {"default": "http://127.0.0.1:8080"}),
                "passthrough": (any_type, {"forceInput": True, "tooltip": "Input of any type to pass through"}),
            }
        }

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("passthrough",)
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/LLM"

    MODEL_UNLOAD_ENDPOINT_CANDIDATES = ("models/unload", "v1/models/unload")

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
                if not response_body.strip():
                    return {}
                return json.loads(response_body)
        except Exception as exc:
            raise RuntimeError(f"{method} {url} failed: {exc}") from exc

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
            print(f"[CidLLMUnload] Warning: Could not fetch loaded models: {exc}")
            return []

    def main(self, base_url, passthrough):
        base_url_value = (base_url or "").strip().rstrip("/")
        if not base_url_value:
            print("[CidLLMUnload] Warning: base_url is empty. Skipping unload.")
            return (passthrough,)

        if not base_url_value.startswith("http://") and not base_url_value.startswith("https://"):
            print("[CidLLMUnload] Warning: base_url must start with http:// or https://. Skipping unload.")
            return (passthrough,)

        loaded_models = self._get_loaded_models(base_url_value)
        if not loaded_models:
            print("[CidLLMUnload] No models currently loaded or could not fetch models.")
            return (passthrough,)

        for model_name in loaded_models:
            print(f"[CidLLMUnload] Attempting to unload model '{model_name}'...")
            success = False
            for endpoint in self.MODEL_UNLOAD_ENDPOINT_CANDIDATES:
                unload_url = urllib.parse.urljoin(f"{base_url_value}/", endpoint)
                try:
                    self._request_json("POST", unload_url, payload={"model": model_name})
                    print(f"[CidLLMUnload] Successfully unloaded '{model_name}'.")
                    success = True
                    break
                except Exception as exc:
                    error_text = str(exc)
                    if "HTTP 404" in error_text or "HTTP 405" in error_text:
                        continue
                    print(f"[CidLLMUnload] Failed to unload '{model_name}' via {endpoint}: {exc}")
            
            if not success:
                print(f"[CidLLMUnload] Could not unload model '{model_name}' using any known endpoint.")

        return (passthrough,)
