#!/usr/bin/env python3
"""QQ Group Daily Briefing — One-Click Setup"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
NAPCAT_REPO = "NapNeko/NapCatQQ"
CONFIG_TEMPLATE = """\
qq:
  napcat_http_url: "http://localhost:3000"
  access_token: ""
  groups:
{groups}

email:
  smtp_server: "smtp.qq.com"
  smtp_port: 465
  sender: "{email}"
  password: "{password}"
  recipient: "{recipient}"
  subject_prefix: "每日简报"

briefing:
  max_qq_messages: 200
"""


def print_banner():
    print("")
    print("  ========================================")
    print("     QQ Group Daily Briefing - Setup")
    print("  ========================================")
    print("")


def check_python():
    print("[1/7] 检查 Python 环境...")
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 9):
        print("错误: 需要 Python 3.9+，当前版本: {}.{}".format(v.major, v.minor))
        sys.exit(1)
    print(f"  Python {v.major}.{v.minor}.{v.micro} [OK]")


def install_deps():
    print("[2/7] 安装 Python 依赖...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"]
        )
        print("  依赖安装完成 [OK]")
    except subprocess.CalledProcessError as e:
        print(f"  依赖安装失败: {e}")
        print("  请检查网络连接后重试，或手动执行:")
        print(f"    {sys.executable} -m pip install -r requirements.txt")
        sys.exit(1)


def detect_os():
    print("[3/7] 检测操作系统...")
    if sys.platform == "win32":
        print("  Windows [OK] — 支持全自动安装")
    elif sys.platform == "darwin":
        print("  macOS — 当前仅支持手动安装 NapCat，详见 README")
        print("  继续配置生成...")
    else:
        print("  Linux — 当前仅支持手动安装 NapCat (推荐 Docker)，详见 README")
        print("  继续配置生成...")


def find_qq_nt():
    """Find QQ NT installation path on Windows."""
    paths = [
        r"D:\QQ",
        r"C:\QQ",
        os.path.expandvars(r"%ProgramFiles%\Tencent\QQNT"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\QQNT"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tencent\QQNT"),
    ]
    for p in paths:
        qq_exe = os.path.join(p, "QQ.exe")
        if os.path.exists(qq_exe):
            return p
    return None


def install_napcat():
    print("[4/7] 安装 NapCatQQ...")
    if sys.platform != "win32":
        print("  非 Windows 系统，跳过自动安装。请手动安装 NapCatQQ。")
        return None

    qq_path = find_qq_nt()
    if not qq_path:
        print("  未检测到 QQ NT，跳过 NapCat 自动安装。")
        print("  请手动安装 QQ NT (https://im.qq.com) 和 NapCatQQ。")
        print("  继续配置向导...")
        return None
    print(f"  找到 QQ NT: {qq_path}")

    # Download latest NapCat release info
    import requests
    try:
        api_url = f"https://api.github.com/repos/{NAPCAT_REPO}/releases/latest"
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        release = resp.json()
    except Exception as e:
        print(f"  无法获取 NapCat 版本信息: {e}")
        print("  请手动下载: https://github.com/NapNeko/NapCatQQ/releases")
        return None

    # Find the full Node package
    download_url = None
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if "Shell.Windows.Node" in name and name.endswith(".zip"):
            download_url = asset.get("browser_download_url")
            break
    if not download_url:
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if "Shell.Windows.OneKey" in name and name.endswith(".zip"):
                download_url = asset.get("browser_download_url")
                break

    if not download_url:
        print("  未找到 NapCat 安装包，请手动下载")
        return None

    # Download
    napcat_dir = Path(os.path.expanduser("~")) / ".napcat"
    napcat_dir.mkdir(exist_ok=True)

    print(f"  下载 NapCatQQ ({release.get('tag_name', 'latest')})...")
    zip_path = napcat_dir / "napcat.zip"
    try:
        r = requests.get(download_url, timeout=300, stream=True)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  下载进度: {pct}%", end="", flush=True)
        print()
    except Exception as e:
        print(f"\n  下载失败: {e}")
        return None

    # Extract
    print("  解压中...")
    extract_dir = napcat_dir / "shell"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    shutil.unpack_archive(str(zip_path), str(extract_dir))
    zip_path.unlink()  # Remove zip

    # Find napcat config directory
    napcat_config_dir = None
    for root, dirs, files in os.walk(str(extract_dir)):
        if "napcat.mjs" in files and "config" in dirs:
            napcat_config_dir = Path(root) / "config"
            break

    # Configure OneBot HTTP API
    if napcat_config_dir:
        onebot_config = {
            "enableLocalFile2Url": True,
            "network": {
                "httpServers": [{
                    "name": "briefing-http",
                    "enable": True,
                    "host": "127.0.0.1",
                    "port": 3000,
                    "enableHeart": False,
                    "enablePost": False,
                    "postUrls": [],
                    "secret": "",
                    "token": ""
                }],
                "httpSseServers": [],
                "httpClients": [],
                "websocketServers": [],
                "websocketClients": [],
                "plugins": []
            },
            "musicSignUrl": "",
            "parseMultMsg": False,
            "imageDownloadProxy": "",
            "timeout": {"baseTimeout": 10000, "uploadSpeedKBps": 256, "downloadSpeedKBps": 256, "maxTimeout": 1800000}
        }
        config_path = napcat_config_dir / "onebot11.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(onebot_config, f, ensure_ascii=False, indent=2)
        print(f"  OneBot HTTP API 配置完成 (端口 3000)")

    # Save napcat path for later
    napcat_info_path = napcat_dir / "install_info.json"
    with open(napcat_info_path, "w") as f:
        json.dump({"extract_dir": str(extract_dir), "version": release.get("tag_name")}, f)

    print(f"  NapCatQQ 安装完成 [OK]")
    print(f"  安装路径: {extract_dir}")
    return str(extract_dir)


def config_wizard():
    print("\n[5/7] 配置向导\n")

    # Groups
    groups = []
    print("请输入要监控的 QQ 群号 (每行一个，输入空行结束):")
    while True:
        gid = input("  群号: ").strip()
        if not gid:
            break
        name = input("  群名称: ").strip()
        groups.append((gid, name))
    if not groups:
        print("未输入任何群，使用示例配置。")
        groups = [("123456789", "示例群")]

    # Email
    print("\n邮箱配置 (QQ邮箱 SMTP):")
    email = input("  发件邮箱 (如 123456@qq.com): ").strip()
    password = input("  SMTP 授权码 (16位, 非QQ密码): ").strip()
    recipient = input("  接收邮箱 (回车则同发件邮箱): ").strip()
    if not recipient:
        recipient = email

    # Generate config
    groups_yaml = "\n".join(f'    - group_id: "{gid}"\n      name: "{name}"' for gid, name in groups)
    config_content = CONFIG_TEMPLATE.format(
        groups=groups_yaml,
        email=email,
        password=password,
        recipient=recipient,
    )

    config_path = ROOT / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)
    print(f"\n  配置已保存到 {config_path} [OK]")


def launch_napcat_and_verify():
    print("\n[6/7] 启动 NapCatQQ...")
    if sys.platform != "win32":
        print("  请手动启动 NapCatQQ 并登录 QQ")
        input("  登录后按回车继续...")
        return

    napcat_info_path = Path(os.path.expanduser("~")) / ".napcat" / "install_info.json"
    if not napcat_info_path.exists():
        print("  NapCat 未安装，跳过")
        return

    with open(napcat_info_path) as f:
        info = json.load(f)
    extract_dir = info["extract_dir"]

    # Find launcher
    launcher = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f == "launcher-win10.bat" or f == "launcher.bat":
                launcher = Path(root) / f
                break
        if launcher:
            break

    if not launcher:
        print("  未找到 NapCat 启动器，请手动启动")
        return

    print(f"  启动 NapCat: {launcher}")
    print()
    print("  [!] 即将弹出 QQ 登录窗口，请扫码登录")
    print("  登录后 NapCat 会自动启动 HTTP API (端口 3000)")
    print()
    input("  按回车启动 NapCat...")

    subprocess.Popen(
        f'cmd.exe /c cd /d "{launcher.parent}" && "{launcher.name}"',
        shell=True,
    )

    # Wait for API
    import requests
    print("  等待 NapCat API 就绪...")
    for i in range(60):
        time.sleep(2)
        try:
            r = requests.post(
                "http://localhost:3000/get_login_info",
                json={},
                timeout=5,
            )
            if r.status_code == 200 and r.json().get("retcode") == 0:
                nickname = r.json()["data"]["nickname"]
                print(f"  NapCat 已连接! QQ: {nickname} [OK]")
                return True
        except Exception:
            pass
        if i % 5 == 0:
            print(f"  等待中... ({i*2}s)")
    print("  超时: 请确认 QQ 已扫码登录且 NapCat 正常运行")
    return False


def test_email():
    print("\n[7/7] 发送测试邮件...")
    import yaml
    from output.email_sender import send_briefing
    from output.aggregator import build_briefing

    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        print("  未找到 config.yaml，跳过")
        return

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    mock = [{
        "group_id": g["group_id"],
        "group_name": g.get("name", ""),
        "message_count": 1,
        "active_members": 1,
        "summary_text": "安装成功",
        "priority": "low",
        "priority_tag": "",
        "topics": ["安装测试"],
        "actions": [],
        "conclusions": ["每日简报安装成功！明天开始你将在指定时间收到群消息摘要。"],
    } for g in config.get("qq", {}).get("groups", [])]

    html = build_briefing(mock)
    send_briefing(html, config)
    print("  测试邮件已发送，请检查邮箱 [OK]")


def main():
    # Force UTF-8 output to avoid UnicodeEncodeError on Windows GBK terminals
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print_banner()

    # Phase 1: Auto install
    check_python()
    install_deps()
    detect_os()
    napcat_path = install_napcat()

    # Phase 2: Interactive config
    config_wizard()

    # Phase 3: Verify
    launch_napcat_and_verify()
    test_email()

    print()
    print("=" * 50)
    print("  安装完成!")
    print()
    print("  每日运行:")
    if sys.platform == "win32":
        print("    python daily_briefing.py")
        print()
        print("  设置定时任务 (Windows):")
        print('    schtasks /create /tn "DailyBriefing" /tr')
        print(f'      "{ROOT / "run_briefing.bat"}" /sc daily /st 19:00')
    else:
        print("    python daily_briefing.py")
        print()
        print("  设置定时任务 (crontab, 每天19:00):")
        print("    crontab -e")
        print(f"    0 19 * * * cd {ROOT} && python daily_briefing.py")
    print()
    print("  祝使用愉快!")
    print("=" * 50)


if __name__ == "__main__":
    main()
