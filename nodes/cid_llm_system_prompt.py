import json


class CidLLMSystemPrompt:
    """
    Helper node to build an OpenAI-style messages JSON string containing a single system prompt.
    """

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("messages",)
    OUTPUT_TOOLTIPS = (
        "OpenAI-style messages JSON array containing one system message.",
    )
    FUNCTION = "main"
    CATEGORY = "Cid Node Pack/LLM"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "system_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "System prompt text that will be emitted as a messages JSON string.",
                    },
                ),
            },
        }

    def main(self, system_prompt):
        prompt_value = (system_prompt or "").strip()
        if not prompt_value:
            raise ValueError("Input 'system_prompt' cannot be empty.")

        messages = [{"role": "system", "content": prompt_value}]
        return (json.dumps(messages, ensure_ascii=False, indent=2),)
