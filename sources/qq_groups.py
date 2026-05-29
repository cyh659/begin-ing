import logging
import re
import time
from collections import Counter
from datetime import datetime, timedelta

import requests
import jieba

logger = logging.getLogger(__name__)

# 中文停用词（常用高频词）
STOPWORDS = set(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 "
    "会 着 没有 看 好 自己 这 他 她 它 们 那 什么 怎么 哪 为什么 可以 "
    "啊 吧 吗 呢 哦 嗯 哈哈 呵呵 还是 如果 因为 所以 然后 但是 而且 "
    "不过 已经 知道 觉得 感觉 应该 可能 也许 大概 这个 那个 这些 那些 "
    "一个 一下 一些 有点 的话 一下 还是 大家 真的 今天 明天 昨天 "
    "现在 刚才 刚刚 一直 总是 老是 经常 特别 非常 比较 很 太 好 多 少 "
    "大 小 新 旧 高 低 快 慢 早 晚 出 来 去 进 过 到 做 干 搞 弄 "
    "了 的 是 吗 么 吧 呢 啊 哦 嗯".split()
)


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
                "top_talkers": [],
                "keyword_highlights": [],
                "sample_messages": [],
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

    # Generate summary
    senders = Counter()
    all_text = []

    for m in deduped:
        sender = _parse_sender(m.get("sender", {}))
        nickname = sender.get("nickname", sender.get("user_id", "unknown"))
        senders[nickname] += 1
        raw = m.get("raw_message", "") or m.get("message", "")
        all_text.append(raw)

    # Top talkers
    top_talkers = [f"{name}({cnt})" for name, cnt in senders.most_common(5)]

    # Keyword extraction via jieba
    combined_text = " ".join(all_text)
    words = jieba.lcut(combined_text)
    word_freq = Counter(
        w.strip() for w in words
        if len(w.strip()) >= 2 and w.strip() not in STOPWORDS
    )
    keywords = [w for w, _ in word_freq.most_common(10)]

    # Sample messages: pick longest ones or those with question marks
    interesting = sorted(
        deduped,
        key=lambda m: len(m.get("raw_message", "") or m.get("message", "")),
        reverse=True,
    )
    samples = []
    for m in interesting[:5]:
        sender = _parse_sender(m.get("sender", {}))
        nickname = sender.get("nickname", sender.get("user_id", "unknown"))
        content = m.get("raw_message", "") or m.get("message", "")
        if content:
            samples.append({
                "sender": nickname,
                "content": content[:200],
                "time": datetime.fromtimestamp(m.get("time", 0)).strftime("%H:%M"),
            })

    # Update state
    if current_seq > last_seq:
        gs["last_message_seq"] = current_seq

    logger.info("Group %s: %d messages, %d members, keywords=%s", group_name, len(deduped), len(senders), keywords[:5])

    return {
        "group_id": group_id,
        "group_name": group_name,
        "message_count": len(deduped),
        "active_members": len(senders),
        "top_talkers": top_talkers,
        "keyword_highlights": keywords,
        "sample_messages": samples,
    }
