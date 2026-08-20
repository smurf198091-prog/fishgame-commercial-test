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
- 游戏源码固定到指定 commit，减少供应链漂移风险
- 后台必须使用 `ADMIN_TOKEN`，没有默认密码

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
ADMIN_TOKEN=至少16位的强密码/随机字符串
DATA_DIR=/tmp/fishgame-data
```

部署完成后访问：

- `https://你的-render域名/game/` 游戏端
- `https://你的-render域名/admin` 后台

后台登录时填写你在 Render 设置的 `ADMIN_TOKEN`。

## 合规边界

当前仅做娱乐币商业测试，不接入真钱充值、提现或博彩结算。Render Free 的 `/tmp` 数据会随实例重启丢失，只适合测试，不适合正式生产。
