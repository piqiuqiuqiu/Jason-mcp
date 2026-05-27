"""
DevOps 提示模板
"""

PROMPTS = [
    {
        "name": "debug-container",
        "description": "容器问题诊断：检查日志、进程、网络连接，定位容器异常原因",
        "arguments": [
            {"name": "container_name", "description": "容器名称", "required": True},
            {"name": "symptom", "description": "异常表现描述", "required": False},
        ],
        "template": """你是一名资深 DevOps 工程师，请诊断以下 Docker 容器问题：

## 容器信息
- 容器名称：{container_name}
- 异常表现：{symptom}

## 诊断步骤
请依次执行：
1. `docker logs --tail=50 {container_name}` 查看最近日志
2. `docker inspect {container_name}` 检查容器配置
3. 检查容器内进程状态
4. 检查网络连接和端口监听
5. 检查磁盘和内存使用

## 输出要求
- 列出发现的问题
- 给出根因分析
- 提供修复方案（优先级排序）
"""
    },
    {
        "name": "deploy-checklist",
        "description": "部署前检查清单：确认代码、配置、依赖、备份状态",
        "arguments": [
            {"name": "service_name", "description": "要部署的服务名", "required": True},
        ],
        "template": """部署前检查清单 - {service_name}

请依次确认以下事项：
1. [ ] Git status 干净，所有变更已提交
2. [ ] 代码已 push 到远程仓库
3. [ ] 依赖文件（requirements.txt）已更新
4. [ ] 环境变量配置正确
5. [ ] 数据库迁移已完成（如适用）
6. [ ] 健康检查端点可用
7. [ ] 备份已创建

确认完毕后执行：`docker compose up -d --build {service_name}`
"""
    },
    {
        "name": "performance-analysis",
        "description": "性能分析：检查系统资源瓶颈",
        "arguments": [],
        "template": """请进行系统性能分析：

1. 使用 tool_sys_info 获取 CPU、内存、磁盘概览
2. 使用 tool_process_mgr 的 top 功能查看资源消耗 TOP 10
3. 检查磁盘 I/O 和网络带宽
4. 分析是否存在内存泄漏或 CPU 密集进程

输出格式：
- 当前负载评级（低/中/高/危险）
- 瓶颈分析
- 优化建议
"""
    },
]
