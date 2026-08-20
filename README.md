# Fishgame Commercial Test

海外商业测试部署包。

## 路径

- `/game/` 游戏端
- `/admin` 商业测试后台
- `/api/health` 健康检查

## 说明

本仓库是轻量自举版：Render 启动时会从公开 GitHub 源下载 H5 捕鱼游戏资源，然后自动补丁：

- 修复画面自适应显示
- 接入后台事件上报
- 启用 SQLite 后台数据

## Render 部署

配置：

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: python server.py
Plan: Free
```

环境变量：

```text
APP_ENV=commercial-test
ADMIN_PASSWORD=你的强密码
ADMIN_TOKEN=同上
DATA_DIR=/tmp/fishgame-data
```

## 合规边界

当前仅做娱乐币商业测试，不接入真钱充值、提现或博彩结算。
