from api.config import settings


class CalendarSyncService:
    @property
    def google_configured(self) -> bool:
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    async def sync_google(self) -> dict:
        if not self.google_configured:
            return {"error": "Google Calendar not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."}
        return {"error": "Google Calendar sync not yet implemented."}

    async def sync_outlook(self) -> dict:
        return {"error": "Outlook Calendar sync not yet implemented."}


calendar_sync_service = CalendarSyncService()
