"""
LLM Agent — optional LLM integration for decision-making and report generation.
Currently supports Gemini (free tier) and OpenAI.
"""
import json
from typing import Optional, Dict, Any


class LLMAgent:
    def __init__(self, config: dict):
        self.config = config
        self.llm_config = config.get('llm', {})
        self.provider = self.llm_config.get('provider', 'none')
        self.api_key = self.llm_config.get('api_key', '')
        self.model = self.llm_config.get('model', 'gemini-2.0-flash')
        self.enabled = self.provider != 'none' and bool(self.api_key)

    def _call_gemini(self, prompt: str) -> Optional[str]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            resp = model.generate_content(prompt)
            return resp.text
        except ImportError:
            return None
        except Exception as e:
            return f"Error: {e}"

    def _call_openai(self, prompt: str) -> Optional[str]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return resp.choices[0].message.content
        except ImportError:
            return None
        except Exception as e:
            return f"Error: {e}"

    def analyze(self, prompt: str) -> Optional[str]:
        if not self.enabled:
            return None
        if self.provider == 'gemini':
            return self._call_gemini(prompt)
        elif self.provider == 'openai':
            return self._call_openai(prompt)
        return None

    def summarize_signal(self, ticker: str, signal_data: Dict[str, Any]) -> Optional[str]:
        if not self.enabled:
            return None
        prompt = (
            f"You are a professional equity analyst. Summarize the following trading signal "
            f"for {ticker} in 2-3 sentences. Provide a clear verdict.BEO\n\n"
            f"{json.dumps(signal_data, indent=2)}"
        )
        return self.analyze(prompt)
