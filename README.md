# QQ群每日简报

每天早上/晚自动抓取指定 QQ 群昨日消息，用 jieba 提取关键词，生成简报发送到邮箱。

## 快速开始

```bash
git clone https://github.com/cyh659/begin-ing.git
cd begin-ing
python setup.py
```

按照终端提示完成 3 步：安装依赖 → 配置群号和邮箱 → 扫码登录 QQ。

随后每天手动运行，或设置定时任务 (默认 19:00)：

**Windows (Task Scheduler):**

```powershell
schtasks /create /tn "DailyBriefing" /tr "项目路径\run_briefing.bat" /sc daily /st 19:00
```

**Linux / macOS (crontab):**

```bash
crontab -e
# 添加: 0 19 * * * cd /path/to/project && python daily_briefing.py
```

## 依赖

| 组件 | 说明 |
|------|------|
| [NapCatQQ](https://github.com/NapNeko/NapCatQQ) | QQ 机器人框架 (OneBot v11) |
| QQ NT | Windows QQ 桌面版 ≥ 9.9.15 |
| Python 3.9+ | requests, jieba, pyyaml, markdown |

## 配置

复制 `config.example.yaml` 为 `config.yaml`，或运行 `python setup.py` 自动生成：

```yaml
qq:
  napcat_http_url: "http://localhost:3000"
  groups:
    - group_id: "1053013915"
      name: "我的群"

email:
  smtp_server: "smtp.qq.com"
  smtp_port: 465
  sender: "123456@qq.com"
  password: "你的QQ邮箱SMTP授权码"
  recipient: "123456@qq.com"
```

QQ 邮箱 SMTP 授权码获取：[mail.qq.com](https://mail.qq.com) → 设置 → 账户 → POP3/SMTP 服务。

## 简报效果

邮件以 HTML 格式发送，包含：

- 各群昨日消息数、活跃人数
- Top 5 发言者
- jieba 提取的热点关键词
- 精选消息片段

## 项目结构

```
├── setup.py              # 一键安装
├── daily_briefing.py     # 主程序
├── sources/
│   ├── qq_groups.py      # NapCat API 客户端 + jieba 摘要
│   └── zhihu.py          # 知乎热榜 (暂未启用)
├── output/
│   ├── aggregator.py     # Markdown → HTML
│   └── email_sender.py   # SMTP 邮件
├── config.example.yaml   # 配置模板
├── run_briefing.bat/sh   # 启动脚本
└── requirements.txt
```

## License

MIT
