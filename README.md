# gh-proxy

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ZvonimirSun/gh-proxy)

## 简介

GitHub release、archive、项目文件和 Git clone 加速项目，提供 Cloudflare Workers 和 Python/Docker 两种部署方式。

## Python 版本和 Cloudflare Worker 版本差异

- python版本支持进行文件大小限制，超过设定返回原地址 [issue #8](https://github.com/hunshcn/gh-proxy/issues/8)

- python版本支持特定user/repo 封禁/白名单 以及passby [issue #41](https://github.com/hunshcn/gh-proxy/issues/41)

## 使用

以下示例假设服务部署在 `https://example.com/` 根路径。

### 文件下载

将完整的 GitHub 资源地址追加到代理入口后：

```text
https://example.com/https://github.com/owner/repo/releases/download/v1.0.0/file.zip
```

对于 `github.com` 地址，可以省略协议和域名，使用简写格式：

```text
https://example.com/owner/repo/releases/download/v1.0.0/file.zip
```

支持以下 GitHub 资源：

- Release 文件和源码归档
- 分支、标签和提交对应的源码归档
- `blob` 和 `raw` 文件
- `raw.githubusercontent.com` 文件
- `gist.githubusercontent.com` 文件

也可以访问代理首页，在输入框中填写完整 GitHub 文件地址。

### Git Clone

仓库地址支持完整格式和简写格式：

```bash
git clone https://example.com/https://github.com/owner/repo.git
git clone https://example.com/owner/repo
git clone https://example.com/owner/repo.git
```

简写仓库地址带或不带 `.git` 均可。后续的 Git Smart HTTP 和 Git LFS 请求会沿用同一代理路径。

克隆私有仓库时，可以在地址中提供 GitHub 用户名和 Personal Access Token：

```bash
git clone https://user:TOKEN@example.com/owner/private-repo.git
```

详见 [#71](https://github.com/hunshcn/gh-proxy/issues/71)。请避免在日志或 shell 历史中泄露 Token。

高频或大流量使用场景请自行部署，避免依赖公共实例。

## Cloudflare Worker 部署

项目使用 ES Modules Worker，入口由 `wrangler.jsonc` 指向 `index.js`。

1. [Fork 本仓库](https://github.com/ZvonimirSun/gh-proxy/fork) 到自己的 GitHub 账号。
2. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)，进入 **Workers & Pages**，选择从 Git 仓库创建 Worker。
3. 授权并连接刚刚 Fork 的仓库，生产分支选择 `master`。
4. 保持项目根目录不变，将部署命令设置为：

```bash
npx wrangler deploy --keep-vars
```

5. 保存并开始首次部署。部署完成后，可以在 Worker 设置中绑定自定义域名。
6. 如需覆盖默认配置，在 Worker 的运行时变量设置中添加以下变量：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `GH_PROXY_ASSET_URL` | `https://zvonimirsun.github.io/gh-proxy/` | 首页等静态资源地址，需保留结尾 `/` |
| `GH_PROXY_PREFIX` | `/` | 代理入口的路径前缀，需以 `/` 开头和结尾；配置为 `/gh/` 后，代理地址为 `https://example.com/gh/` |
| `GH_PROXY_JSDELIVR` | `0` | `1` 启用 jsDelivr，`0` 禁用 |
| `GH_PROXY_WHITELIST` | 空 | 逗号分隔的白名单规则，支持 `/user/`、`user`、`user/repo` 和 `*/repo` |

环境变量不存在时会使用表中的默认值。`wrangler.jsonc` 中的 `keep_vars` 和部署命令中的 `--keep-vars` 会在后续 Git 自动部署时保留 Dashboard 中设置的运行时变量。

## Python 版本部署

### Docker 部署

先从当前仓库构建镜像：

```bash
docker build -t gh-proxy .
docker run -d --name gh-proxy \
  -p 80:80 \
  --restart always \
  -e GH_PROXY_PREFIX=/ \
  -e GH_PROXY_JSDELIVR=0 \
  -e GH_PROXY_WHITELIST= \
  -e GH_PROXY_ASSET_URL=https://zvonimirsun.github.io/gh-proxy/ \
  gh-proxy
```

Python/Docker 版本使用与 Worker 相同的四个 `GH_PROXY_*` 变量和默认值。还可以通过 `LISTEN_PORT` 调整服务监听端口。

### 直接部署

安装依赖并运行：

```bash
pip install flask requests
python app/main.py
```

运行前可通过环境变量覆盖配置，无需修改 `app/main.py`。

### 注意

Python 版本启动时会获取 `GH_PROXY_ASSET_URL` 的首页和 favicon。如果运行环境无法访问该地址，请将变量改为可访问的静态资源地址。

## Cloudflare Workers 计费

可在 Cloudflare Dashboard 中查看 Worker 使用量。免费额度和付费方案可能调整，请以 [Cloudflare Workers 官方定价](https://developers.cloudflare.com/workers/platform/pricing/) 为准。

## Changelog

* 2020.04.10 增加对`raw.githubusercontent.com`文件的支持
* 2020.04.09 增加Python版本（使用Flask）
* 2020.03.23 新增了clone的支持
* 2020.03.22 初始版本

## 参考

[jsproxy](https://github.com/EtherDream/jsproxy/)
