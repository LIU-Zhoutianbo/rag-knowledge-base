# Docker 部署指南

本文档详细说明如何使用 Docker 部署 RAG 知识库问答系统。

## 📋 前置要求

- Docker 20.10+
- Docker Compose 1.29+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 🚀 快速开始

### 方法 1：使用 Docker Compose（推荐）

#### 1. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入您的 API Keys（如果使用在线模型）
nano .env
```

#### 2. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 3. 访问应用

打开浏览器访问：http://localhost:8501

#### 4. 停止服务

```bash
# 停止服务
docker-compose down

# 停止并删除数据卷（注意：会删除知识库数据）
docker-compose down -v
```

### 方法 2：使用 Docker 命令

#### 1. 构建镜像

```bash
docker build -t rag-knowledge-base:latest .
```

#### 2. 运行容器

```bash
docker run -d \
  --name rag-app \
  -p 8501:8501 \
  -v $(pwd)/vector_store:/app/vector_store \
  -v $(pwd)/logs:/app/logs \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e DEEPSEEK_API_KEY=your_api_key_here \
  rag-knowledge-base:latest
```

#### 3. 查看日志

```bash
docker logs -f rag-app
```

#### 4. 停止容器

```bash
docker stop rag-app
docker rm rag-app
```

## 🔧 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# Ollama（本地模型）
OLLAMA_BASE_URL=http://host.docker.internal:11434

# DeepSeek（在线模型）
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 通义千问（在线模型）
QWEN_API_KEY=your_qwen_api_key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 数据持久化

默认情况下，以下目录会被持久化：

- `./vector_store` - 向量数据库
- `./logs` - 应用日志

### 端口映射

- `8501` - Streamlit Web 界面

## 🐳 与 Ollama 集成

### 选项 1：使用宿主机的 Ollama

如果您的宿主机已安装 Ollama：

```bash
# 确保 Ollama 正在运行
ollama serve

# 在 docker-compose.yml 中使用 host.docker.internal
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### 选项 2：在 Docker 中运行 Ollama

取消 `docker-compose.yml` 中 Ollama 服务的注释：

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

然后修改 RAG 应用的环境变量：

```yaml
environment:
  - OLLAMA_BASE_URL=http://ollama:11434
```

启动服务：

```bash
docker-compose up -d

# 下载模型
docker exec -it ollama ollama pull llama2
```

## 📊 资源配置

### 内存限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  rag-app:
    # ... 其他配置
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### CPU 限制

```yaml
services:
  rag-app:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2.0'
        reservations:
          cpus: '1.0'
```

## 🔍 故障排查

### 1. 容器无法启动

```bash
# 查看详细日志
docker-compose logs rag-app

# 检查容器状态
docker-compose ps
```

### 2. 无法连接到 Ollama

```bash
# 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 在容器内测试连接
docker exec -it rag-app curl http://host.docker.internal:11434/api/tags
```

### 3. 嵌入模型下载慢

使用 Hugging Face 镜像：

```yaml
environment:
  - HF_ENDPOINT=https://hf-mirror.com
```

### 4. 权限问题

```bash
# 修复目录权限
sudo chown -R $USER:$USER vector_store logs
```

## 🚀 生产环境部署

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 使用 HTTPS

```bash
# 安装 Certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 自动重启

```yaml
services:
  rag-app:
    restart: unless-stopped
```

## 📝 维护

### 备份数据

```bash
# 备份向量数据库
tar -czf vector_store_backup_$(date +%Y%m%d).tar.gz vector_store/

# 备份日志
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

### 清理旧镜像

```bash
# 删除未使用的镜像
docker image prune -a

# 删除未使用的容器
docker container prune
```

## 🔐 安全建议

1. **不要在 Git 中提交 .env 文件**
2. **使用强密码和 API Keys**
3. **定期更新 Docker 镜像**
4. **限制容器资源使用**
5. **使用 HTTPS 加密传输**
6. **定期备份数据**

## 📚 更多资源

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Streamlit 部署指南](https://docs.streamlit.io/streamlit-community-cloud/get-started/deploy-an-app)
- [Ollama Docker 文档](https://hub.docker.com/r/ollama/ollama)

## ❓ 常见问题

**Q: 如何更改端口？**

A: 修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8080:8501"  # 将 8501 改为 8080
```

**Q: 如何使用 GPU？**

A: 在 `docker-compose.yml` 中添加：

```yaml
services:
  rag-app:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Q: 如何查看实时日志？**

A: 使用以下命令：

```bash
docker-compose logs -f rag-app
```

---

如有问题，请提交 Issue 或查看项目文档。