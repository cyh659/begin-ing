# QQ Group Daily Briefing

Automated daily summary of QQ group messages — keyword extraction via jieba, delivered to your email.

## Quick Start

```bash
git clone https://github.com/cyh659/begin-ing.git
cd begin-ing
python setup.py
```

Follow the terminal prompts: install deps → configure groups & email → scan QQ QR login.

## Schedule

### Windows (Task Scheduler)

```powershell
schtasks /create /tn "DailyBriefing" /tr "\path\to\run_briefing.bat" /sc daily /st 19:00
```

### Linux / macOS (crontab)

```bash
crontab -e
# Add: 0 19 * * * cd /path/to/project && python daily_briefing.py
```

## Dependencies

| Component | Description |
|-----------|-------------|
| [NapCatQQ](https://github.com/NapNeko/NapCatQQ) | QQ bot framework (OneBot v11) |
| QQ NT | Windows QQ Desktop ≥ 9.9.15 |
| Python 3.9+ | requests, jieba, pyyaml, markdown |

## Configuration

```yaml
qq:
  napcat_http_url: "http://localhost:3000"
  groups:
    - group_id: "1053013915"
      name: "Work Group"

email:
  smtp_server: "smtp.qq.com"
  smtp_port: 465
  sender: "123456@qq.com"
  password: "your-smtp-auth-code"
  recipient: "123456@qq.com"
```

## License

MIT
