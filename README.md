# Fishgame Commercial Test - Vercel Edition

海外免费商业测试部署包，适配 Vercel Hobby。

## 路径

- `/game/` 游戏端
- `/admin/` 商业测试后台
- `/api/health` 健康检查

## 架构

- `public/game/`：完整 H5 捕鱼游戏静态文件
- `api/index.js`：Vercel Serverless API
- `admin/index.html`：商业测试后台

## Vercel 部署

导入本仓库后使用默认设置即可。

环境变量：

```text
ADMIN_TOKEN=至少16位的强密码/随机字符串
APP_ENV=commercial-test
```

部署完成后访问：

- 游戏端：`https://你的域名/game/`
- 后台：`https://你的域名/admin/`

后台登录填写 `ADMIN_TOKEN`。

## 注意

Vercel Serverless 的临时数据不保证长期保存。本版本只用于商业测试和演示，不用于正式运营。

## 合规边界

当前仅做娱乐币测试，不接入真钱充值、提现或博彩结算。
