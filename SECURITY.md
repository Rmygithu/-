# 🔒 安全配置说明

## 📋 概述

为了保护你的 API Key 和敏感信息不被泄露，本项目采用环境变量管理所有敏感配置。

## ⚠️ 重要提醒

**绝对不要将以下文件提交到 Git：**
- `.env` - 包含你的真实 API Key
- `.env.local` - 本地开发配置
- `.env.production` - 生产环境配置

这些文件已在 `.gitignore` 中排除，不会被 Git 追踪。

## 🚀 快速配置

### 1️⃣ 创建 .env 文件

```bash
# 复制模板文件
cp .env.example .env
```

### 2️⃣ 编辑 .env 文件

用文本编辑器打开 `.env` 文件，填入你的真实配置：

```env
# MiMo 模型配置（必填）
MIMO_API_KEY=你的真实API Key
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL_ID=mimo-v2.5-pro
```

### 3️⃣ 验证配置

```bash
python check_config.py
```

如果看到 "✅ 配置检查通过！" 说明配置正确。

## 🔐 API Key 获取方式

### 小米 MiMo API Key

1. 访问 [小米 AI 平台](https://mimo.xiaomi.com/)
2. 注册并登录账号
3. 在控制台中创建 API Key
4. 复制 API Key 到 `.env` 文件

## 🛡️ 安全最佳实践

### ✅ 推荐做法

- ✅ 使用 `.env` 文件管理本地开发配置
- ✅ 使用环境变量管理生产环境配置
- ✅ 定期更换 API Key
- ✅ 为不同环境使用不同的 API Key
- ✅ 在团队中使用 `.env.example` 分享配置模板

### ❌ 避免做法

- ❌ 在代码中硬编码 API Key
- ❌ 将 `.env` 文件提交到 Git
- ❌ 在公开场合分享 API Key
- ❌ 使用同一个 API Key 用于开发和生产
- ❌ 在日志中打印完整的 API Key

## 🔧 配置优先级

系统按以下优先级读取配置：

1. **UI 输入**：用户在侧边栏输入的 API Key（最高优先级）
2. **环境变量**：通过 `.env` 文件或系统环境变量设置
3. **默认值**：非敏感配置的默认值（如 API 地址、模型名称）

## 📝 配置项说明

| 配置项 | 必填 | 说明 | 默认值 |
|--------|------|------|--------|
| `MIMO_API_KEY` | ✅ | 小米 MiMo API Key | 无（必须配置） |
| `MIMO_BASE_URL` | ❌ | API 端点地址 | `https://token-plan-cn.xiaomimimo.com/v1` |
| `MIMO_MODEL_ID` | ❌ | 模型标识符 | `mimo-v2.5-pro` |

## 🐳 Docker 部署

### 使用环境变量

```bash
docker run -e MIMO_API_KEY=your_key -p 8501:8501 breakup-recovery
```

### 使用 .env 文件

```bash
docker run --env-file .env -p 8501:8501 breakup-recovery
```

### 使用 docker-compose

```bash
# 确保 .env 文件存在
docker-compose up -d
```

## 🚨 泄露应急处理

如果你的 API Key 不慎泄露：

1. **立即更换**：在小米 AI 平台重新生成 API Key
2. **检查使用**：查看 API Key 的使用记录，确认是否有异常调用
3. **更新配置**：在所有使用该 Key 的环境中更新为新 Key
4. **清理 Git**：如果 Key 被提交到 Git，需要清理 Git 历史

### 清理 Git 历史

```bash
# 使用 BFG Repo-Cleaner
bfg --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

## 📚 相关文档

- [README.md](README.md) - 项目说明
- [.env.example](.env.example) - 配置模板
- [check_config.py](check_config.py) - 配置检查脚本

## 🤝 贡献指南

如果你发现安全问题或有改进建议，欢迎：

1. 提交 Issue 报告安全漏洞
2. 提交 Pull Request 修复问题
3. 完善安全文档

---

<p align="center">
  🔒 安全第一，保护你的 API Key
</p>
