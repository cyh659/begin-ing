# QQ群每日简报

每天自动抓取指定 QQ 群昨日消息，jieba 提取关键词，生成 HTML 简报发送到邮箱。5 分钟了解群聊动态，无需翻看 99+ 未读。

---

## 你的电脑需要先装好

| 软件 | 下载 | 说明 |
|------|------|------|
| **Python** ≥ 3.9 | https://python.org → Download → 勾选 "Add to PATH" | 安装后终端输入 `py --version` 验证 (Windows 用 `py` 而不是 `python`) |
| **QQ NT 桌面版** | https://im.qq.com → Windows版 | 必须是新版 Electron QQ，不是 tim/轻聊版 |

---

## 第一步：下载项目

**方式一：直接下载 ZIP（推荐，无需装 Git）**

1. 浏览器打开 https://github.com/cyh659/begin-ing
2. 点击绿色 **Code** 按钮 → **Download ZIP**
3. 把下载的 `begin-ing-main.zip` 解压到任意位置（比如桌面）
4. 打开解压出的 `begin-ing-main` 文件夹
5. 在文件夹**地址栏**里直接输入 `powershell` 然后回车

```
此时会弹出一个蓝色终端窗口，光标所在位置就是项目目录。
```

**方式二：用 Git 克隆**

```bash
git clone https://github.com/cyh659/begin-ing.git
cd begin-ing
```

---

## 第二步：获取 SMTP 授权码

> 这一步需要浏览器操作，**和安装脚本并行做**以节省时间。

1. 浏览器打开 https://mail.qq.com ，登录你的 QQ 邮箱
2. 点击左上角 **齿轮图标** → **账户**
3. 往下滚到 **POP3/IMAP/SMTP服务** 区域
4. 如果 SMTP 服务显示 **已关闭**，点击 **开启**
5. 按提示用密保手机**发送短信**验证
6. 验证成功后，页面上会出现一串 **16 位字母**（类似 `eamuhxglmxmrdjie`）
7. **把这串授权码复制下来**，下一步要用

> ⚠️ 授权码 ≠ QQ 密码。是专门的 16 位字母数字组合。

---

## 第三步：运行一键安装

**如何打开终端：**

1. 打开项目文件夹（第一步解压出的 `begin-ing-main`）
2. 点击文件夹顶部的**地址栏**，删掉现有路径，输入 `powershell`
3. 回车 → 弹出一个蓝底白字的窗口
4. 在窗口里输入 `py setup.py`，回车

```
┌─────────────────────────────────────────────┐
│ 文件资源管理器                                │
│ ┌─────────────────────────────────────┐      │
│ │ C:\Users\xxx\Desktop\begin-ing-main │  ← 点这里，输入 powershell
│ └─────────────────────────────────────┘      │
│                                             │
│  📄 setup.py                                │
│  📄 daily_briefing.py                       │
│  📁 sources/                                │
│  📁 output/                                 │
└─────────────────────────────────────────────┘
```

> 不需要安装 PyCharm、VS Code 或任何编程软件，Windows 自带的 PowerShell 即可。

在终端中执行：

```bash
py setup.py
```
```

安装脚本会依次：

1. **检查 Python 环境** — 确认版本 ≥ 3.9
2. **安装 Python 依赖** — requests, jieba, pyyaml, markdown, lxml, curl_cffi
3. **检测操作系统** — 确认 Windows
4. **下载 NapCatQQ** — 自动从 GitHub 下载最新版，解压，配置 OneBot HTTP API（端口 3000）
5. **配置向导** — 交互式输入群号和邮箱（见下方说明）
6. **启动 NapCat + 扫码验证** — 弹出 QQ 登录窗口
7. **发送测试邮件** — 验证整个链路通畅

### 第三步-A：配置向导详解

脚本运行到 `[5/7] 配置向导` 时会依次问你：

**1. QQ 群号**

```
请输入要监控的 QQ 群号 (每行一个，输入空行结束):
  群号:      ← 输入群号
  群名称:     ← 起个好记的名字
  群号: 
  群名称:
  群号:                     ← 直接回车结束
```

> 如何找到群号？在 QQ 客户端右键群聊 → 查看群资料 → 群号那栏就是。

**2. 邮箱配置**

```
邮箱配置 (QQ邮箱 SMTP):
  发件邮箱:        ← 你的 QQ 号 + @qq.com
  SMTP 授权码:      ← 第二步获取的 16 位码
  接收邮箱:                          ← 回车则同发件邮箱
```

---

## 第四步：扫码登录 QQ

脚本运行到 `[6/7]` 时会启动 NapCat + QQ，**弹出一个 QQ 登录窗口**。

用手机 QQ **扫描屏幕上的二维码**，确认登录。

> 这个 QQ 登录窗口看起来和普通 QQ 一模一样，不同之处在于后台注入了 NapCat，可以在不影响你正常使用 QQ 的同时提供 API 接口。

登录后，脚本自动检测 API 是否连通（最多等待 60 秒）：

```
NapCat 已连接! QQ: 昵称 ✓
```

---

## 第五步：验证测试邮件

接着脚本发送一封测试邮件到你的 QQ 邮箱：

```
[7/7] 发送测试邮件...
  测试邮件已发送，请检查邮箱 ✓
```

打开 QQ 邮箱 App 或网页，应看到：

- **发件人**：你自己
- **主题**：`每日简报 — 2026-05-29`
- **内容**：包含你配置的群名称和示例消息

**收到邮件 = 安装完全成功。**

---

## 第六步：设置每天自动运行

### Windows（推荐）

以**管理员身份**打开 PowerShell，执行（替换路径）：

```powershell
schtasks /create /tn "DailyBriefing" /tr "C:\你的路径\begin-ing\run_briefing.bat" /sc daily /st 19:00
```

验证是否创建成功：

```powershell
schtasks /query /tn "DailyBriefing"
```

> 晚上 7 点电脑需**开机**且 QQ 需**已登录**，否则当天不会推送。

### 修改推送时间

```powershell
schtasks /change /tn "DailyBriefing" /st 21:00    # 改为晚上9点
```

### Linux / macOS

```bash
crontab -e
# 添加下面这行（替换为你的实际路径）：
0 19 * * * cd /home/xxx/begin-ing && py daily_briefing.py >> logs/cron.log 2>&1
```

---

## 日常使用

### 手动运行一次

```bash
py daily_briefing.py
```

### 只生成简报不发邮件

```bash
py daily_briefing.py --no-email
```

### 发邮件前预览 HTML

```bash
py daily_briefing.py --no-email --dry-run
# 打开 preview.html 查看效果
```

### 每天开机后启动 NapCat

如果 QQ 没自动启动 NapCat（正常情况每次开机/重启后需要重新启动），以**管理员身份**运行：

```batch
D:\.napcat\shell\<版本>\resources\app\napcat\launcher-win10.bat
```

---

## 修改配置

直接编辑项目目录下的 `config.yaml`：

```yaml
qq:
  groups:
    - group_id: "1053013915"    # 新增群
      name: "新群"
    - group_id: "123456789"     # 删除不用的群，删掉整段即可
      name: "旧群"

email:
  password: "新的16位授权码"     # 换授权码

briefing:
  max_qq_messages: 500          # 抓更多消息（默认200）
```

修改后无需重启任何东西，下次到点自动生效。

---

## 常见问题

### Q: 提示 "Cannot connect to NapCat"

NapCat 没有运行。需要启动 NapCat → 扫码登录 QQ。

### Q: 授权码填了还是发不出邮件

检查 `config.yaml` 中 `password` 是 **16 位授权码**不是 QQ 密码。重新生成授权码再试。

### Q: 电子邮件中文乱码

确认项目是最新版（已修复），或手动在 `run_briefing.bat` 中加入：

```batch
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
```

### Q: macOS / Linux 能用吗

可以。核心 Python 代码跨平台。NapCat 部分需要手动安装（参考 [NapCat 文档](https://doc.napneko.icu)）。

### Q: 能不能用其他邮箱（163/Gmail）

可以。修改 `config.yaml` 中 email 部分：

```yaml
# 163邮箱
email:
  smtp_server: "smtp.163.com"
  smtp_port: 465

# Gmail
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
```

---

## License

MIT
