FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl cron procps net-tools iputils-ping dnsutils \
    && curl -fsSL https://get.docker.com | sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 源代码
COPY . .

# 创建必要目录
RUN mkdir -p downloads logs store && chmod -R 777 downloads logs store

# entrypoint
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]
