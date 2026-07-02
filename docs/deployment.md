# 部署指南

## 本地部署

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd ai_breakup_recovery_agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# MIMO_API_KEY=your_mimo_api_key
```

### 3. 启动应用

```bash
streamlit run app.py
```

应用将在 http://localhost:8501 启动

## Docker 部署

### 1. 使用 Docker Compose（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 2. 使用 Docker

```bash
# 构建镜像
docker build -t breakup-recovery .

# 运行容器
docker run -d \
  -p 8501:8501 \
  -e MIMO_API_KEY=your_key \
  breakup-recovery
```

## 云端部署

### Streamlit Cloud

1. Push 代码到 GitHub
2. 登录 [Streamlit Cloud](https://share.streamlit.io/)
3. 连接仓库，选择 `app.py` 作为入口
4. 在 Secrets 中配置环境变量

### Heroku

```bash
# 安装 Heroku CLI
heroku create breakup-recovery

# 配置环境变量
heroku config:set MIMO_API_KEY=your_key

# 部署
git push heroku main
```

### Railway

1. 连接 GitHub 仓库
2. 配置环境变量
3. 自动部署

## 配置说明

### Streamlit 配置

编辑 `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF6B6B"

[server]
port = 8501
headless = true
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| MIMO_API_KEY | MiMo API Key | - |
| MIMO_BASE_URL | MiMo API 地址 | https://token-plan-cn.xiaomimimo.com/v1 |
| MIMO_MODEL_ID | MiMo 模型 ID | xiaomi/MiMo-7B-RL |

## 常见问题

### 1. 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8501

# 杀死进程
kill -9 <PID>
```

### 2. 依赖安装失败

```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. API Key 无效

- 检查 API Key 是否正确
- 确认 API Key 是否有足够额度
- 检查网络连接
