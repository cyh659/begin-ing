import logging
import re
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class NapCatError(Exception):
    pass


class NapCatClient:
    def __init__(self, base_url="http://localhost:3000", access_token=None):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        if access_token:
            self._session.headers["Authorization"] = f"Bearer {access_token}"

    def _request(self, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        for attempt in range(3):
            try:
                resp = self._session.post(url, json=data or {}, timeout=30)
                resp.raise_for_status()
                body = resp.json()
                if body.get("retcode") != 0 and body.get("status") != "ok":
                    raise NapCatError(f"API error: {body.get('msg', body.get('wording', 'unknown'))}")
                return body.get("data", body)
            except requests.ConnectionError:
                if attempt == 2:
                    raise NapCatError(f"Cannot connect to NapCat at {self.base_url}")
                time.sleep(1)
            except requests.RequestException as e:
                if attempt == 2:
                    raise NapCatError(f"HTTP error: {e}")
                time.sleep(1)

    def get_group_list(self):
        return self._request("/get_group_list")

    def get_group_info(self, group_id):
        return self._request("/get_group_info", {"group_id": int(group_id)})

    def get_group_msg_history(self, group_id, message_seq=0, count=100):
        return self._request("/get_group_msg_history", {
            "group_id": int(group_id),
            "message_seq": int(message_seq),
            "count": count,
        })


def _parse_sender(sender):
    """Parse sender field which may be a dict or '@{key=value; ...}' string."""
    if isinstance(sender, dict):
        return sender
    if isinstance(sender, str):
        result = {}
        for match in re.finditer(r'(\w+)=([^;]+)', sender):
            result[match.group(1)] = match.group(2).strip()
        return result
    return {}


def fetch_group_messages(client, groups_config, state, max_messages=200):
    summaries = []
    now = datetime.now()
    cutoff_ts = (now - timedelta(hours=24)).timestamp()

    for group_cfg in groups_config:
        group_id = str(group_cfg["group_id"])
        group_name = group_cfg.get("name", group_id)

        try:
            summary = _fetch_single_group(client, group_id, group_name, state, cutoff_ts, max_messages)
            summaries.append(summary)
        except NapCatError as e:
            logger.error("Failed to fetch group %s: %s", group_name, e)
            summaries.append({
                "group_id": group_id,
                "group_name": group_name,
                "error": str(e),
                "message_count": 0,
                "active_members": 0,
                "summary_text": "",
                "priority": "low",
                "priority_tag": "",
                "topics": [],
                "actions": [],
                "conclusions": [],
            })

    return summaries


def _fetch_single_group(client, group_id, group_name, state, cutoff_ts, max_messages):
    gs = state.setdefault("groups_state", {}).setdefault(group_id, {})
    last_seq = gs.get("last_message_seq", 0)

    all_messages = []
    current_seq = 0

    # Fetch first page
    data = client.get_group_msg_history(group_id, message_seq=last_seq, count=min(max_messages, 200))
    messages = data.get("messages", [])

    if messages:
        all_messages.extend(messages)
        # Track newest seq for state update
        current_seq = max(m["message_seq"] for m in messages if "message_seq" in m)

        # Paginate if needed while messages are within 24h
        while len(messages) >= 100 and len(all_messages) < max_messages:
            oldest_time = min(m.get("time", 0) for m in messages)
            if oldest_time < cutoff_ts:
                break
            last_msg = messages[0]
            seq = last_msg.get("message_seq", 0) - 1
            if seq <= 0:
                break
            data = client.get_group_msg_history(group_id, message_seq=seq, count=100)
            messages = data.get("messages", [])
            all_messages.extend(messages)

    # Filter to last 24h
    recent = [m for m in all_messages if m.get("time", 0) >= cutoff_ts]

    # Deduplicate by message_id
    seen = set()
    deduped = []
    for m in recent:
        mid = m.get("message_id")
        if mid not in seen:
            seen.add(mid)
            deduped.append(m)

    # Use structured summarizer
    from sources.summarizer import generate_summary

    summary_text, meta = generate_summary(deduped, max_chars=150)

    # Count active senders for stats
    senders = set()
    for m in deduped:
        s = _parse_sender(m.get("sender", {}))
        uid = s.get("user_id", s.get("nickname", "?"))
        senders.add(uid)

    # Update state
    if current_seq > last_seq:
        gs["last_message_seq"] = current_seq

    logger.info("Group %s: %d msgs, %d members, priority=%s", group_name, meta['message_count'], len(senders), meta['priority'])

    return {
        "group_id": group_id,
        "group_name": group_name,
        "message_count": meta['message_count'],
        "active_members": len(senders),
        "summary_text": summary_text,
        "priority": meta['priority'],
        "priority_tag": meta['priority_tag'],
        "topics": meta['topics'],
        "actions": meta['actions'],
        "conclusions": meta['conclusions'],
    }
