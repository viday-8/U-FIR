"""The only module that talks to an LLM. Provider chosen by LLM_PROVIDER."""
import json
import re

from .. import config


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


def chat_json(system: str, user: str) -> dict:
    if config.LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic
        msg = Anthropic().messages.create(
            model=config.LLM_MODEL, max_tokens=2000, system=system,
            messages=[{"role": "user", "content": user}])
        return _parse_json(msg.content[0].text)
    from openai import OpenAI
    resp = OpenAI(base_url=config.OPENAI_BASE_URL).chat.completions.create(
        model=config.LLM_MODEL, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return _parse_json(resp.choices[0].message.content)
