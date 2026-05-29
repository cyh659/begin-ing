# QQ群每日简报 - 开源化设计

## 目标

将现有项目改造为他人可一键安装使用的开源工具。

## 用户旅程

```
git clone → python setup.py → 扫码登录QQ → 收到测试邮件 ✅
```

## setup.py 三阶段

### 阶段 1: 自动安装
- pip install 依赖
- 检测操作系统
- 检测/提示安装 QQ NT
- 自动下载 NapCatQQ → 解压 → 配置 OneBot HTTP API (端口 3000)
- 启动 NapCat

### 阶段 2: 交互配置
- 输入 QQ 群号
- 输入邮箱 SMTP 授权码
- 默认推送时间 19:00
- 生成 config.yaml

### 阶段 3: 验证激活
- 等待用户扫码登录 QQ
- 验证 API 连通性
- 发送测试邮件

## 不做的
- 不自动创建 OS 定时任务（用户自行配置）
- 不自动化 QQ 扫码登录
- 不自动化 SMTP 授权码获取

## 文件结构

```
begin-ing/
├── setup.py                  # 一键安装 (新增)
├── daily_briefing.py         # 主程序
├── config.example.yaml
├── requirements.txt
├── run_briefing.bat / .sh    # 启动脚本
├── LICENSE                   # MIT (新增)
├── README.md                 # 中文 (新增)
├── README_EN.md              # 英文 (新增)
├── sources/
│   ├── qq_groups.py
│   └── zhihu.py
└── output/
    ├── aggregator.py
    └── email_sender.py
```
