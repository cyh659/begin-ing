"""Structured group message summarizer with priority detection and action extraction."""
import re
from collections import Counter, defaultdict
import jieba

# Priority detection keywords
HIGH_KEYWORDS = {'紧急', '马上', '立刻', '立即', '必须', '重要', '尽快', '加急', '火速', 'ASAP', '赶紧', '赶快'}
MEDIUM_KEYWORDS = {'需要', '请', '帮忙', '注意', '提醒', '别忘了', '各位', '大家'}

# Action item extraction patterns: (regex, label)
# Order matters — group action checked before request_action
GROUP_KEYWORDS = {'大家', '各位', '所有人', '全员'}
ACTION_REGEX = [
    (r'(@.{1,20}?)\s*[：:]\s*(.{5,60}?)(?:[。！\n]|$)', 'mention_action'),
    (r'(大家|各位|所有人|@all|@everyone)[，,\s]{0,6}(注意|记得|别忘了|帮忙|需要|做|完成|处理|提交|准备)(.{2,50})', 'group_action'),
    (r'(?:请|麻烦|需要|让)\s*(.{1,20}?)\s*(?:去\s*)?(做|处理|完成|提交|发布|部署|修复|改|更新|检查|确认|通知|安排|准备|写|整理|交|发|回复|联系)(.{2,40})', 'request_action'),
]

# Deadline extraction patterns
DEADLINE_REGEX = [
    (r'(今天|明天|后天)', 'day'),
    (r'(周[一二三四五六日]|下周[一二三四五六日])', 'weekday'),
    (r'(\d{1,2}月\d{1,2}[日号])', 'date'),
    (r'(\d{1,2}[点时：:]\d{0,2})', 'time'),
    (r'(DDL|deadline|截止|之前|前|到期)', 'keyword'),
]

# Conclusion markers
CONCLUSION_MARKERS = {'结论', '总结', '决定', '确认', '定了', '就这样', '同意', '通过', 'OK', '好的', '没问题', '可以', '行'}


def _parse_sender(sender):
    """Parse sender from dict or PowerShell-style string."""
    if isinstance(sender, dict):
        return sender
    if isinstance(sender, str):
        result = {}
        for m in re.finditer(r'(\w+)=([^;]+)', sender):
            result[m.group(1)] = m.group(2).strip()
        return result
    return {}


def _get_nickname(msg):
    s = _parse_sender(msg.get('sender', {}))
    return s.get('card') or s.get('nickname') or s.get('user_id', '?')


def _get_content(msg):
    return msg.get('raw_message', '') or msg.get('message', '')


def detect_priority(messages):
    """Return (level_str, label_str) based on priority keyword count."""
    all_text = ' '.join(_get_content(m) for m in messages)
    high = sum(1 for w in HIGH_KEYWORDS if w in all_text)
    med = sum(1 for w in MEDIUM_KEYWORDS if w in all_text)
    if high >= 2:
        return 'high', '⚠️高'
    elif high >= 1 or med >= 3:
        return 'medium', '🔶中'
    return 'low', ''


def extract_actions(messages):
    """Extract action items with speaker, task, deadline from messages."""
    actions = []
    seen = set()
    for m in messages:
        content = _get_content(m)
        if not content or len(content) < 4:
            continue
        nickname = _get_nickname(m)

        for pattern, _ptype in ACTION_REGEX:
            match = re.search(pattern, content)
            if match:
                # Determine who and what
                if _ptype == 'mention_action':
                    who = match.group(1).replace('@', '').strip()
                    task = match.group(2).strip()
                elif _ptype == 'request_action':
                    who = match.group(1).strip()
                    task = match.group(2) + match.group(3)
                    # If the extracted "who" is actually a group keyword, treat as group action
                    if any(gk in who for gk in GROUP_KEYWORDS):
                        who = '全员'
                    # Sanitize: strip leading time/date words from who
                    who = re.sub(r'^(今天|明天|后天|周[一二三四五六日]|下周|下个月|下午|上午|晚上|早上|中午|明早|今晚)\s*', '', who)
                    if not who or len(who) < 1:
                        who = '全员'
                else:  # group_action
                    who = '全员'
                    task = match.group(2) + match.group(3)

                task = task.strip().rstrip('，。！,.')

                # Find deadline in same message
                deadline = ''
                for dp, _ in DEADLINE_REGEX:
                    dm = re.search(dp, content)
                    if dm:
                        deadline = dm.group(0)
                        break

                key = f'{who}|{task[:20]}'
                if key not in seen and len(task) >= 2:
                    seen.add(key)
                    actions.append({
                        'speaker': who,
                        'task': task[:60],
                        'deadline': deadline,
                        'source_nickname': nickname,
                    })
                break
    return actions[:4]


def extract_conclusions(messages):
    """Extract conclusion/summary statements."""
    conclusions = []
    for m in messages[::-1]:  # newest first
        content = _get_content(m)
        if any(w in content for w in CONCLUSION_MARKERS) and len(content) >= 5:
            conclusions.append(content[:80])
            if len(conclusions) >= 2:
                break
    return conclusions


def build_topics(messages):
    """Cluster messages into topics via jieba keyword grouping."""
    word_msgs = defaultdict(list)
    for m in messages:
        content = _get_content(m)
        if not content or len(content) < 6:
            continue
        words = [w for w in jieba.lcut(content) if len(w) >= 2]
        for w in words[:2]:  # first 2 content words
            word_msgs[w].append(m)

    # Take top topics (most messages)
    ranked = sorted(word_msgs.items(), key=lambda x: len(x[1]), reverse=True)
    topics = []
    seen_topics = set()
    for word, msgs in ranked:
        if word in seen_topics or len(msgs) < 2:
            continue
        # Find related keywords in this cluster
        all_words = []
        for m in msgs:
            all_words.extend(w for w in jieba.lcut(_get_content(m)) if len(w) >= 2)
        top_words = [w for w, _ in Counter(all_words).most_common(3) if w != word]
        topic_label = word if not top_words else f'{word}/{top_words[0]}'
        if topic_label not in seen_topics:
            seen_topics.add(topic_label)
            topics.append(topic_label)
        if len(topics) >= 3:
            break
    return topics


def generate_summary(messages, max_chars=150):
    """
    Generate a structured, compact summary string.

    Format:
      优先级: ⚠️高
      议题: 部署 | 测试
      • 张三: 明天前完成部署 ⏰明天
      • 李四: 接口测试 ⏰周四
      结论: 方案已确认
    """
    if not messages:
        return '', {'priority': 'low', 'priority_tag': '', 'topics': [], 'actions': [], 'conclusions': []}

    priority, ptag = detect_priority(messages)
    actions = extract_actions(messages)
    conclusions = extract_conclusions(messages)
    topics = build_topics(messages)

    lines = []
    ch = 0  # character counter

    def add(line):
        nonlocal ch
        if ch + len(line) <= max_chars:
            lines.append(line)
            ch += len(line)
            return True
        return False

    # Priority
    if ptag:
        add(f'优先级: {ptag}')

    # Topics
    if topics:
        topic_str = ' | '.join(topics[:3])
        add(f'议题: {topic_str}')

    # Action items
    for a in actions:
        deadline_str = f' ⏰{a["deadline"]}' if a['deadline'] else ''
        action_line = f'• {a["speaker"]}: {a["task"][:50]}{deadline_str}'
        if not add(action_line):
            break

    # Conclusions
    for c in conclusions:
        if not add(f'结论: {c[:60]}'):
            break

    summary_text = '\n'.join(lines)

    meta = {
        'priority': priority,
        'priority_tag': ptag,
        'topics': topics,
        'actions': actions,
        'conclusions': conclusions,
        'message_count': len(messages),
    }

    return summary_text, meta
