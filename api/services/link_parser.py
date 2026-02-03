import re

# Matches [[note title]], [[task:id]], [[event:id]]
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")


def parse_links(content: str) -> list[dict]:
    """Parse wiki-links from markdown content.

    Returns list of dicts with keys: identifier, link_type
    - [[My Note]]              -> {"identifier": "My Note", "link_type": "note"}
    - [[task:task_abc]]        -> {"identifier": "task_abc", "link_type": "task"}
    - [[event:event_abc]]      -> {"identifier": "event_abc", "link_type": "event"}
    - [[task:task_abc|Review]] -> {"identifier": "task_abc", "link_type": "task"}
    """
    links = []
    for match in WIKI_LINK_PATTERN.finditer(content):
        raw = match.group(1).strip()

        # Strip display text if pipe syntax used: [[target|display]]
        if "|" in raw:
            raw = raw.split("|", 1)[0].strip()

        if ":" in raw:
            prefix, identifier = raw.split(":", 1)
            prefix = prefix.strip().lower()
            identifier = identifier.strip()
            if prefix in ("task", "event"):
                links.append({"identifier": identifier, "link_type": prefix})
            else:
                links.append({"identifier": raw, "link_type": "note"})
        else:
            links.append({"identifier": raw, "link_type": "note"})
    return links
