import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone, date
from urllib.parse import urlparse

import caldav
from icalendar import Calendar as iCalendar, Event as iEvent

from api.models.calendar import CalendarEvent

logger = logging.getLogger(__name__)


def _resolve_caldav_url(url: str, username: str, password: str) -> str:
    """Follow server redirects to discover the actual CalDAV endpoint.

    iCloud redirects caldav.icloud.com → pXX-caldav.icloud.com/USER_ID/principal/
    and the caldav library's niquests backend strips the Authorization header
    during that cross-host redirect, causing a 401.  By resolving the redirect
    chain ourselves (with allow_redirects=False) we can hand the final URL
    directly to DAVClient so it never needs to follow a cross-host redirect.
    """
    try:
        import niquests
    except ImportError:
        try:
            import requests as niquests
        except ImportError:
            return url

    # Try the URL as-is, then fall back to .well-known/caldav discovery
    parsed = urlparse(url)
    well_known = f"{parsed.scheme}://{parsed.netloc}/.well-known/caldav"

    for try_url in [url.rstrip("/") + "/", well_known]:
        try:
            resp = niquests.request(
                "PROPFIND",
                try_url,
                auth=(username, password),
                headers={"Depth": "0", "Content-Type": "application/xml"},
                allow_redirects=False,
                timeout=15,
            )
            if resp.status_code in (301, 302, 307, 308):
                location = resp.headers.get("Location")
                if location:
                    logger.info("CalDAV URL resolved: %s -> %s", try_url, location)
                    return location
            # 207 Multi-Status means the URL itself is valid, no redirect needed
            if resp.status_code == 207:
                return try_url
        except Exception:
            continue

    return url


def _make_caldav_client(url: str, username: str, password: str) -> caldav.DAVClient:
    """Create a DAVClient, resolving cross-host redirects first.

    Resolves the real server URL up-front so the library never has to
    follow a cross-host redirect (which strips auth headers).
    """
    resolved = _resolve_caldav_url(url, username, password)
    client = caldav.DAVClient(
        url=resolved, username=username, password=password, timeout=30
    )
    return client


class CalDAVSyncService:
    async def list_calendars(self, url: str, username: str, password: str) -> list[dict]:
        """Connect to CalDAV server and return available calendars."""
        def _list():
            client = _make_caldav_client(url, username, password)
            principal = client.principal()
            calendars = principal.calendars()
            result = []
            for cal in calendars:
                props = cal.get_properties([caldav.dav.DisplayName()])
                name = str(props.get("{DAV:}displayname", "Untitled"))
                color = ""
                try:
                    color_props = cal.get_properties(
                        [caldav.elements.ical.CalendarColor()]
                    )
                    color = str(
                        color_props.get(
                            "{http://apple.com/ns/ical/}calendar-color", ""
                        )
                    )
                except Exception:
                    pass
                result.append({
                    "id": str(cal.url),
                    "name": name,
                    "color": color,
                })
            return result

        return await asyncio.to_thread(_list)

    async def full_sync(
        self,
        db,
        settings_map: dict,
    ) -> dict:
        """Full bidirectional sync: push local changes, pull remote events."""
        url = settings_map.get("caldav_server_url", "")
        username = settings_map.get("caldav_username", "")
        password = settings_map.get("caldav_password", "")
        selected_cals = settings_map.get("selected_calendars", [])
        past_days = int(settings_map.get("calendar_sync_range_past_days", "30"))
        future_days = int(settings_map.get("calendar_sync_range_future_days", "90"))

        if not url or not username or not password:
            return {"synced_events": 0, "created": 0, "updated": 0, "deleted": 0,
                    "errors": ["CalDAV credentials not configured"], "last_sync": None}

        stats = {"synced_events": 0, "created": 0, "updated": 0, "deleted": 0, "errors": []}
        now = datetime.now(timezone.utc)

        try:
            client, calendars = await self._connect_and_get_calendars(
                url, username, password, selected_cals
            )
        except Exception as e:
            logger.exception("CalDAV connection failed")
            return {**stats, "errors": [f"Connection failed: {e}"],
                    "last_sync": now.isoformat()}

        # Phase 1: Push local changes to server
        await self._push_local_changes(db, calendars, settings_map, stats)

        # Phase 2: Pull remote events
        start_range = now - timedelta(days=past_days)
        end_range = now + timedelta(days=future_days)
        seen_external_ids = set()

        for cal in calendars:
            try:
                events = await asyncio.to_thread(
                    cal.date_search, start_range, end_range, expand=True
                )
            except Exception as e:
                stats["errors"].append(f"Search failed for calendar: {e}")
                continue

            cal_url = str(cal.url)
            for remote_event in events:
                try:
                    await self._upsert_from_remote(
                        db, remote_event, cal_url, seen_external_ids, stats
                    )
                except Exception as e:
                    stats["errors"].append(f"Failed to process event: {e}")

        # Phase 3: Delete local events not seen during pull (only caldav-sourced)
        await self._delete_missing_events(db, seen_external_ids, stats)

        await db.commit()
        stats["synced_events"] = stats["created"] + stats["updated"]
        stats["last_sync"] = now.isoformat()
        return stats

    async def push_single_event(self, event: CalendarEvent, settings_map: dict) -> dict:
        """Push a new local event to the CalDAV server."""
        url = settings_map.get("caldav_server_url", "")
        username = settings_map.get("caldav_username", "")
        password = settings_map.get("caldav_password", "")
        selected_cals = settings_map.get("selected_calendars", [])

        if not url or not username or not password or not selected_cals:
            return {}

        try:
            client, calendars = await self._connect_and_get_calendars(
                url, username, password, selected_cals
            )
            if not calendars:
                return {}

            cal = calendars[0]  # push to first selected calendar
            vcal = self._event_to_vcalendar(event)
            vcal_str = vcal.to_ical().decode("utf-8")

            def _save():
                new_event = cal.save_event(vcal_str)
                return {
                    "uid": str(event.id),
                    "href": str(new_event.url),
                    "etag": getattr(new_event, "etag", None) or "",
                }

            return await asyncio.to_thread(_save)
        except Exception as e:
            logger.exception("Failed to push event to CalDAV")
            return {"error": str(e)}

    async def update_remote_event(self, event: CalendarEvent, settings_map: dict):
        """Update an existing event on the CalDAV server."""
        url = settings_map.get("caldav_server_url", "")
        username = settings_map.get("caldav_username", "")
        password = settings_map.get("caldav_password", "")

        if not url or not username or not password or not event.caldav_href:
            return

        try:
            def _update():
                client = _make_caldav_client(url, username, password)
                try:
                    remote_event = caldav.Event(client=client, url=event.caldav_href)
                    remote_event.load()
                except Exception:
                    return

                ical = iCalendar.from_ical(remote_event.data)
                for component in ical.walk():
                    if component.name == "VEVENT":
                        component["SUMMARY"] = event.title
                        if "DESCRIPTION" in component:
                            del component["DESCRIPTION"]
                        if event.description:
                            component["DESCRIPTION"] = event.description
                        if "LOCATION" in component:
                            del component["LOCATION"]
                        if event.location:
                            component["LOCATION"] = event.location
                        if "DTSTART" in component:
                            del component["DTSTART"]
                        if "DTEND" in component:
                            del component["DTEND"]
                        if event.all_day:
                            component.add("DTSTART", event.start_time.date())
                            if event.end_time:
                                component.add("DTEND", event.end_time.date())
                        else:
                            component.add("DTSTART", event.start_time)
                            if event.end_time:
                                component.add("DTEND", event.end_time)
                        break

                remote_event.data = ical.to_ical().decode("utf-8")
                remote_event.save()

            await asyncio.to_thread(_update)
        except Exception as e:
            logger.exception("Failed to update remote event")

    async def delete_remote_event(self, event: CalendarEvent, settings_map: dict):
        """Delete an event from the CalDAV server."""
        url = settings_map.get("caldav_server_url", "")
        username = settings_map.get("caldav_username", "")
        password = settings_map.get("caldav_password", "")

        if not url or not username or not password or not event.caldav_href:
            return

        try:
            def _delete():
                client = _make_caldav_client(url, username, password)
                remote_event = caldav.Event(client=client, url=event.caldav_href)
                remote_event.load()
                remote_event.delete()

            await asyncio.to_thread(_delete)
        except Exception as e:
            logger.exception("Failed to delete remote event")

    # ── Internal helpers ──

    async def _connect_and_get_calendars(
        self, url: str, username: str, password: str, selected_cals: list[str]
    ):
        def _connect():
            client = _make_caldav_client(url, username, password)
            principal = client.principal()
            all_cals = principal.calendars()
            if selected_cals:
                filtered = [c for c in all_cals if str(c.url) in selected_cals]
                return client, filtered if filtered else all_cals
            return client, all_cals

        return await asyncio.to_thread(_connect)

    async def _push_local_changes(self, db, calendars, settings_map, stats):
        """Push locally modified events that haven't been synced yet."""
        if not calendars:
            return

        from sqlalchemy import select, and_

        # Find local events that have been updated since last sync
        query = select(CalendarEvent).where(
            and_(
                CalendarEvent.calendar_source == "local",
                CalendarEvent.caldav_href.is_(None),
                CalendarEvent.external_id.is_(None),
            )
        )
        result = await db.execute(query)
        local_events = list(result.scalars().all())

        for event in local_events:
            try:
                push_result = await self.push_single_event(event, settings_map)
                if push_result and "href" in push_result:
                    event.caldav_href = push_result["href"]
                    event.etag = push_result.get("etag", "")
                    event.external_id = event.id
                    event.calendar_source = "caldav"
                    event.synced_at = datetime.now(timezone.utc)
                    stats["created"] += 1
                elif push_result and "error" in push_result:
                    stats["errors"].append(f"Push failed for '{event.title}': {push_result['error']}")
                elif not push_result:
                    stats["errors"].append(f"Push skipped for '{event.title}': no CalDAV calendars selected or credentials missing")
            except Exception as e:
                stats["errors"].append(f"Push failed for '{event.title}': {e}")

    async def _upsert_from_remote(self, db, remote_event, cal_url, seen_external_ids, stats):
        """Parse a remote CalDAV event and upsert into DB."""
        from sqlalchemy import select

        try:
            ical_data = remote_event.data
            if isinstance(ical_data, bytes):
                ical_data = ical_data.decode("utf-8")
        except Exception:
            ical_data = str(remote_event.data)

        ical = iCalendar.from_ical(ical_data)

        for component in ical.walk():
            if component.name != "VEVENT":
                continue

            uid = str(component.get("UID", ""))
            if not uid:
                continue

            # Expanded recurring instances share the same UID but have a
            # RECURRENCE-ID distinguishing each occurrence.  Build a stable
            # external_id so each instance gets its own DB row.
            recurrence_id = component.get("RECURRENCE-ID")
            if recurrence_id:
                rid_val = recurrence_id.dt
                external_id = f"{uid}_{rid_val.isoformat()}"
            else:
                external_id = uid

            seen_external_ids.add(external_id)

            summary = str(component.get("SUMMARY", "Untitled"))
            description = str(component.get("DESCRIPTION", "")) if component.get("DESCRIPTION") else ""
            location = str(component.get("LOCATION", "")) if component.get("LOCATION") else ""

            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")

            all_day = False
            start_time = None
            end_time = None

            if dtstart:
                dt_val = dtstart.dt
                if isinstance(dt_val, date) and not isinstance(dt_val, datetime):
                    all_day = True
                    start_time = datetime(dt_val.year, dt_val.month, dt_val.day, tzinfo=timezone.utc)
                else:
                    if dt_val.tzinfo is None:
                        start_time = dt_val.replace(tzinfo=timezone.utc)
                    else:
                        start_time = dt_val.astimezone(timezone.utc).replace(tzinfo=None)
                        start_time = start_time.replace(tzinfo=timezone.utc)

            if dtend:
                dt_val = dtend.dt
                if isinstance(dt_val, date) and not isinstance(dt_val, datetime):
                    end_time = datetime(dt_val.year, dt_val.month, dt_val.day, tzinfo=timezone.utc)
                else:
                    if dt_val.tzinfo is None:
                        end_time = dt_val.replace(tzinfo=timezone.utc)
                    else:
                        end_time = dt_val.astimezone(timezone.utc).replace(tzinfo=None)
                        end_time = end_time.replace(tzinfo=timezone.utc)

            if not start_time:
                continue

            href = str(remote_event.url) if remote_event.url else ""
            etag = getattr(remote_event, "etag", None) or ""

            # Check if event already exists
            result = await db.execute(
                select(CalendarEvent).where(CalendarEvent.external_id == external_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing - server wins
                existing.title = summary
                existing.description = description
                existing.location = location
                existing.start_time = start_time
                existing.end_time = end_time
                existing.all_day = all_day
                existing.caldav_href = href
                existing.etag = etag
                existing.calendar_id = cal_url
                existing.synced_at = datetime.now(timezone.utc)
                stats["updated"] += 1
            else:
                # Create new
                new_event = CalendarEvent(
                    title=summary,
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                    all_day=all_day,
                    location=location,
                    calendar_source="caldav",
                    calendar_id=cal_url,
                    external_id=external_id,
                    caldav_href=href,
                    etag=etag,
                    synced_at=datetime.now(timezone.utc),
                )
                db.add(new_event)
                stats["created"] += 1

    async def _delete_missing_events(self, db, seen_external_ids, stats):
        """Remove local caldav events that no longer exist on the server."""
        from sqlalchemy import select

        result = await db.execute(
            select(CalendarEvent).where(
                CalendarEvent.calendar_source == "caldav",
                CalendarEvent.external_id.isnot(None),
            )
        )
        all_caldav_events = list(result.scalars().all())

        for event in all_caldav_events:
            if event.external_id not in seen_external_ids:
                await db.delete(event)
                stats["deleted"] += 1

    def _event_to_vcalendar(self, event: CalendarEvent) -> iCalendar:
        """Convert a local CalendarEvent to iCalendar format."""
        cal = iCalendar()
        cal.add("prodid", "-//Sundial//EN")
        cal.add("version", "2.0")

        vevent = iEvent()
        vevent.add("uid", event.external_id or event.id)
        vevent.add("summary", event.title)
        if event.description:
            vevent.add("description", event.description)
        if event.location:
            vevent.add("location", event.location)

        if event.all_day:
            vevent.add("dtstart", event.start_time.date())
            if event.end_time:
                vevent.add("dtend", event.end_time.date())
        else:
            vevent.add("dtstart", event.start_time)
            if event.end_time:
                vevent.add("dtend", event.end_time)

        vevent.add("dtstamp", datetime.now(timezone.utc))

        cal.add_component(vevent)
        return cal


caldav_sync_service = CalDAVSyncService()
