import json
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)


class AIService:
    async def generate_text(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
        )

        if not response.choices:
            raise RuntimeError("AI returned no response")

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("AI returned empty response")
        return content

    async def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        json_prompt = f"{prompt}\n\nReturn ONLY valid JSON. No markdown, no code fences."
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": json_prompt})

        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )

        if not response.choices:
            raise RuntimeError("AI returned no response for JSON")

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("AI returned empty JSON response")

        result = json.loads(content)
        if not isinstance(result, dict):
            raise RuntimeError("AI returned non-object JSON")
        return result


ai_service = AIService()
