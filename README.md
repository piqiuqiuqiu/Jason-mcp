# JasonMCP

本地操作专用 MCP Server，与 NotionMCP (V1) 同网络运行，聚焦 DevOps 和系统管理能力。

## 架构

```
JasonMCP/
├── server/                 # MCP 服务器核心
│   ├── main.py            # FastMCP 主实例（13 个 Tools）
│   ├── config.py          # 配置管理
│   ├── tools/             # 工具实现
│   │   ├── shell_exec.py      # Shell 命令执行
│   │   ├── file_ops.py        # 文件读写
│   │   ├── git_ops.py         # Git 版本控制
│   │   ├── docker_ops.py      # Docker Compose 管理
│   │   ├── process_mgr.py     # 进程管理
│   │   ├── sys_info.py        # 系统信息
│   │   ├── env_mgr.py         # 环境变量管理
│   │   ├── log_viewer.py      # 日志查看器
│   │   ├── cron_mgr.py        # 定时任务管理
│   │   ├── network_utils.py   # 网络工具
│   │   ├── dir_tree.py        # 目录树可视化
│   │   └── text_search.py     # 递归文件搜索
│   ├── resources/         # MCP Resources
│   │   ├── docker_config.py   # Docker 容器/镜像/配置
│   │   └── server_config.py   # 服务器信息/磁盘/网络
│   ├── prompts/           # MCP Prompts
│   │   └── devops.py          # 容器诊断/部署清单/性能分析
│   └── routes/            # REST API
│       ├── health.py          # /health 端点
│       └── monitor.py         # /monitor 监控面板
├── run.py                 # 启动入口
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 部署

```bash
# 构建并启动
docker compose up -d --build

# 验证
curl http://localhost:8809/health
curl http://localhost:8809/tools
```

## 网络

与 NotionMCP V1 共享 Docker 网络 `notion-mcp_default`，可通过 `http://notion-mcp:8000` 互通。

## 端口

- **8809** (宿主) → **8000** (容器)
