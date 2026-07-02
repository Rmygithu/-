# 💔 心愈 AI・分手情绪疗愈系统

> 🤖 基于多智能体协作的 AI 分手疗愈支持系统 | 课程设计项目

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.44-red?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Agno-2.2+-green" alt="Agno">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
</p>

---

## 📖 项目简介

**心愈 AI** 是一个基于多智能体协作的情感支持系统，通过 **5 个专业 AI Agent** 为经历分手的用户提供全方位的情感支持和恢复指导。

### 🎯 核心理念

- 🤝 **多智能体协作**：5 个专业 Agent 各司其职，提供多角度支持
- 🧠 **情感智能**：基于大语言模型的深度情感理解
- 🎯 **实用导向**：提供可执行的恢复计划和行动建议
- 💬 **长记忆对话**：基于 Agno 原生记忆的多轮上下文对话

---

## ✨ 功能特性

### 🌟 核心功能

| 功能 | 描述 | Emoji |
|------|------|-------|
| 🧠 **情绪评估** | 分析情绪状态，输出结构化评估报告 | `Step 0` |
| 🤗 **情绪疗愈** | 共情倾听、正念引导、情绪拆解、认知调整 | `Step 1` |
| ✍️ **告别释怀** | 多版本信件修改、语气调整、断联话术生成 | `Step 2` |
| 📅 **恢复规划** | 7天恢复计划、任务细化、歌单影单定制 | `Step 3` |
| 💪 **清醒真话** | 事件分析、行为动机拆解、观点辩论 | `Step 4` |
| 💝 **一键生成** | 全套恢复方案，一键获取 | `核心功能` |

### 🔥 亮点功能

- 🎵 **治愈歌单**：自动生成并链接网易云音乐搜索
- 📊 **情绪报告**：可视化展示情绪类型、烈度、核心痛点
- 📅 **7天计划表**：结构化展示每日恢复任务
- 💬 **多轮对话**：每个 Agent 独立记忆，页面刷新不丢失
- 🔄 **滑动窗口**：自动保留最近 10 轮对话，避免上下文过长
- 🎉 **完成特效**：生成完毕后触发气球和烟花动画

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    🎨 Streamlit Frontend                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Sidebar  │  │  Input   │  │  Chat    │  │  Common  │    │
│  │  Config  │  │   Area   │  │  Tabs    │  │   UI     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    🎯 Controller Layer                        │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │  BatchController   │  │  ChatController    │             │
│  │  (5步状态机)       │  │  (单Tab对话)       │             │
│  └────────────────────┘  └────────────────────┘             │
├─────────────────────────────────────────────────────────────┤
│                    🤖 Agent Manager                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ EmotionEval │ Therapist │ Closure │ Routine │ Honesty │   │
│  │   Agent     │   Agent   │  Agent  │  Agent  │  Agent  │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    ⚙️ Agno Framework                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            MiMo v2.5-pro (OpenAI Compatible)          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
ai_breakup_recovery_agent/
├── 🚀 app.py                      # 主入口
│
├── 🤖 agents/                     # 智能体模块
│   ├── base.py                    # 基类（Agno 原生记忆）
│   ├── emotion_eval_agent.py      # 🧠 情绪评估
│   ├── therapist_agent.py         # 🤗 共情疗愈
│   ├── closure_agent.py           # ✍️ 告别释怀
│   ├── routine_agent.py           # 📅 恢复规划
│   ├── honesty_agent.py           # 💪 清醒真话
│   └── manager.py                 # 🎯 调度管理
│
├── 🎮 controllers/                # 控制器层
│   ├── batch_controller.py        # 批量生成（5步状态机）
│   ├── chat_controller.py         # 单Tab对话
│   └── music_mapper.py            # 🎵 歌单映射
│
├── ⚙️ config/                     # 配置模块
│   ├── constants.py               # 常量定义
│   └── settings.py                # 环境配置
│
├── 📝 prompts/                    # 提示词模板
│   ├── system_prompts.py          # 系统指令
│   └── user_templates.py          # 用户模板
│
├── 🎨 ui/                         # UI 组件
│   ├── sidebar.py                 # 侧边栏
│   ├── input_area.py              # 输入区域
│   ├── chat_tabs.py               # 聊天窗口
│   └── common.py                  # 通用组件
│
├── 🔧 utils/                      # 工具函数
│   ├── session_store.py           # 会话管理
│   ├── validators.py              # 输入验证
│   ├── logger.py                  # 日志工具
│   ├── stream_helper.py           # 流式输出
│   └── routine_parser.py          # 计划解析
│
├── 🧪 tests/                      # 单元测试
├── 📚 docs/                       # 项目文档
├── 📦 requirements.txt            # 依赖清单
├── 🐳 Dockerfile                  # Docker 配置
└── 🐳 docker-compose.yml          # 编排配置
```

---

## 🚀 快速开始

### 📋 环境要求

- 🐍 Python 3.11+
- 📦 pip 或 conda
- 🔑 MiMo API Key（小米 AI 模型）

### 💻 本地运行

```bash
# 1️⃣ 克隆项目
git clone <repository-url>
cd ai_breakup_recovery_agent

# 2️⃣ 安装依赖
pip install -r requirements.txt

# 3️⃣ 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 4️⃣ 检查配置（可选）
python check_config.py

# 5️⃣ 启动应用
streamlit run app.py
```

### 🐳 Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 访问应用
# 🌐 http://localhost:8501
```

---

## 📝 使用指南

### 🎯 一键生成模式（推荐）

1. ⚙️ 在左侧边栏配置 API Key
2. ✏️ 在输入区域描述你的感受和情况
3. 💝 点击「获取恢复方案」按钮
4. ⏳ 等待 5 个 Agent 依次生成（约 1-2 分钟）
5. 🎉 生成完毕后切换 Tab 查看各 Agent 的分析结果

### 💬 单独对话模式

1. 📑 切换到对应的 Tab（情绪疗愈/告别释怀/恢复规划/清醒真话）
2. ✍️ 在底部输入框输入消息
3. 🔄 与 Agent 进行多轮深度对话

### 📊 情绪评估报告

- 🧠 系统会自动分析你的情绪状态
- 📊 生成可视化的情绪评估报告
- 🎯 后续 Agent 会根据评估结果动态适配回复风格

---

## 🔧 配置说明

### 🤖 模型配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MIMO_API_KEY` | 小米 MiMo API Key | ⚠️ **必填** |
| `MIMO_BASE_URL` | API 端点地址 | `https://token-plan-cn.xiaomimimo.com/v1` |
| `MIMO_MODEL_ID` | 模型标识符 | `mimo-v2.5-pro` |

### 📁 环境变量

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

`.env` 文件内容：
```env
MIMO_API_KEY=your_api_key_here
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL_ID=mimo-v2.5-pro
```

---

## 📚 文档

- 📐 [系统架构](docs/architecture.md) - 详细架构说明
- 🚀 [部署指南](docs/deployment.md) - 部署和运维
- 📖 [使用手册](docs/usage_guide.md) - 详细使用说明
- 📋 [更新日志](CHANGELOG.md) - 版本更新记录
- 🔒 [安全配置](SECURITY.md) - API Key 安全管理

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest --cov=agents tests/

# 运行特定测试
pytest tests/test_agents.py
```

---

## 📄 许可证

本项目基于 MIT 许可证开源 - 详见 [LICENSE](LICENSE)

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| **Streamlit** | Web 前端渲染引擎 |
| **Agno** | 多智能体协作引擎 |
| **ChromaDB** | 本地向量数据库（RAG 知识检索） |
| **SQLite** | 轻量级关系型数据库（数据持久化） |
| **MiMo v2.5-pro** | 大语言模型（小米 AI） |

---

## ⚠️ 免责声明

> 💡 **重要提示**：本系统仅供学习和参考使用，不能替代专业心理咨询。
> 
> 如果你正在经历严重的心理困扰，请及时寻求专业心理咨询师或心理医生的帮助。
> 
> 🆘 **24小时心理援助热线**：400-161-9995

---

<p align="center">
  Made with ❤️ by 希锐sama<br>
  <sub>💝 心愈 AI - 让每一次伤痛都成为成长的契机</sub>
</p>
