#!/usr/bin/env python3
import argparse
import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml

from sources.qq_groups import NapCatClient, fetch_group_messages, NapCatError
from output.aggregator import build_briefing
from output.email_sender import send_briefing, EmailSendError

ROOT = Path(__file__).parent


def setup_logging():
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = RotatingFileHandler(
        log_dir / "briefing.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=30,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def load_config(path="config.yaml"):
    config_path = ROOT / path
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        print("请复制 config.example.yaml 为 config.yaml 并填入真实配置")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state(path="state.json"):
    state_path = ROOT / path
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_run_ts": 0, "groups_state": {}}


def save_state(state, path="state.json"):
    state["last_run_ts"] = int(datetime.now().timestamp())
    state_path = ROOT / path
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="每日简报生成工具")
    parser.add_argument("--dry-run", action="store_true", help="生成简报但不发送邮件")
    parser.add_argument("--no-email", action="store_true", help="跳过邮件发送")
    args = parser.parse_args()

    log = setup_logging()
    log.info("===== 每日简报开始 =====")

    config = load_config()

    # 1. Fetch QQ group messages
    state = load_state()
    groups_summary = []
    qq_cfg = config.get("qq", {})

    if qq_cfg.get("groups"):
        try:
            client = NapCatClient(
                base_url=qq_cfg.get("napcat_http_url", "http://localhost:3000"),
                access_token=qq_cfg.get("access_token") or None,
            )
            groups_summary = fetch_group_messages(
                client=client,
                groups_config=qq_cfg["groups"],
                state=state,
                max_messages=config.get("briefing", {}).get("max_qq_messages", 200),
            )
            log.info("Got summaries for %d groups", len(groups_summary))
        except NapCatError as e:
            log.error("QQ fetch failed: %s", e)
        except Exception as e:
            log.error("Unexpected error in QQ fetch: %s", e)
    else:
        log.info("No QQ groups configured, skipping")

    # 2. Build briefing
    log.info("Building briefing...")
    html = build_briefing(groups_summary)

    # 3. Send email
    if not args.no_email:
        log.info("Sending email...")
        try:
            send_briefing(html, config)
            log.info("Email sent successfully")
        except EmailSendError as e:
            log.error("Email send failed: %s", e)
        except Exception as e:
            log.error("Unexpected error sending email: %s", e)
    else:
        log.info("--no-email flag set, skipping email")

    if args.dry_run:
        # Write HTML to file for inspection
        preview_path = ROOT / "preview.html"
        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)
        log.info("Dry run: HTML preview saved to %s", preview_path)

    # 4. Save state
    save_state(state)
    log.info("===== 每日简报结束 =====")


if __name__ == "__main__":
    main()
