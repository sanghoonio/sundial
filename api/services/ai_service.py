from api.config import settings


class AIService:
    @property
    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def chat(self, message: str, note_id: str | None = None, context: str | None = None) -> dict:
        if not self.is_configured:
            return {"error": "AI not configured. Set ANTHROPIC_API_KEY in .env to enable AI features."}
        # Future: actual Claude API call using message, note_id, and context
        return {"error": "AI integration not yet implemented."}

    async def analyze_note(self, note_id: str, content: str) -> dict:
        if not self.is_configured:
            return {"error": "AI not configured. Set ANTHROPIC_API_KEY in .env to enable AI features."}
        # Future: summarize, extract tasks, suggest tags
        return {"error": "AI integration not yet implemented."}


ai_service = AIService()
