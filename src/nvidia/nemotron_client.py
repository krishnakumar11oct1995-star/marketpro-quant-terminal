import json
from typing import Optional, AsyncGenerator
from src.core.config import Config
from src.core.logger import Logger


class NemotronClient:
    MODEL = "gemma4:e4b"

    def __init__(self):
        self.config = Config()
        self.log = Logger()
        raw = self.config.get("ai_model")
        self.model = raw if raw else self.MODEL
        self.log.info(f"AI model from config: '{raw}' -> using: '{self.model}'")
        self.base_url = self.config.get("ollama_url", "http://localhost:11434")
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            import ollama
            self._client = ollama
        except ImportError:
            self.log.warn("Ollama not installed - AI agents disabled")

    def chat(self, messages: list[dict], stream: bool = False) -> Optional[str]:
        if not self._client:
            return "AI backend not available. Install Ollama and pull gemma4:e4b."
        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                stream=stream
            )
            if stream:
                return response
            return response["message"]["content"]
        except Exception as e:
            self.log.error(f"Ollama chat error: {e}")
            return f"AI Error: {e}"

    def analyze_stock(self, symbol: str, context: dict) -> str:
        prompt = f"""You are a professional financial analyst. Analyze {symbol} with the following data and provide a concise investment thesis:

Price: ${context.get('price', 'N/A')}
P/E: {context.get('pe', 'N/A')}
Market Cap: {context.get('market_cap', 'N/A')}
Sector: {context.get('sector', 'N/A')}
Change%: {context.get('change_pct', 'N/A')}%

Provide:
1. Technical Outlook (trend, support, resistance)
2. Fundamental Assessment
3. Key Risks
4. Recommendation (Buy/Hold/Sell)"""
        return self.chat([{"role": "user", "content": prompt}])

    def get_agent_response(self, persona: str, persona_desc: str, query: str, market_data: str) -> str:
        messages = [
            {"role": "system", "content": f"You are {persona}. {persona_desc} Keep responses concise and actionable. Use the provided market data."},
            {"role": "user", "content": f"Market Data:\n{market_data}\n\nQuery: {query}"}
        ]
        return self.chat(messages)
