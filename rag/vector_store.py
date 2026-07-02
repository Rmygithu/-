"""
极简 RAG 向量检索层 — 约 100 行
ChromaDB 本地持久化向量库 + 心理学知识库种子文档

公开接口:
    retrieve(query, k=3) -> str   根据用户描述检索最相关心理学知识片段
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# 知识库种子文档（亲密关系 + 创伤心理学，共 12 条）
# ─────────────────────────────────────────────────────────────
SEED_DOCS: List[dict] = [
    {
        "id": "grief_stages",
        "text": (
            "库伯勒-罗斯悲伤五阶段理论：否认→愤怒→协议→抑郁→接受。"
            "分手后的情绪波动是正常的哀悼过程，每个阶段的持续时间因人而异，"
            "也可以反复经历，不必强迫自己按顺序'走完'。"
        ),
        "meta": {"topic": "grief_theory", "source": "Kübler-Ross, 1969"},
    },
    {
        "id": "attachment_theory",
        "text": (
            "鲍尔比依恋理论：安全型依恋者更容易接受分离；焦虑型依恋者在分手后"
            "更容易产生强烈的思念与挽回冲动；回避型依恋者则倾向于压抑情绪、"
            "假装不在乎。识别自己的依恋风格有助于理解情绪反应的根源。"
        ),
        "meta": {"topic": "attachment_theory", "source": "Bowlby, 1969"},
    },
    {
        "id": "cbt_reframing",
        "text": (
            "认知行为疗法（CBT）核心技术——认知重构：识别负面自动思维"
            "（如'我再也找不到更好的人了'），检验其证据，用更平衡的想法替代。"
            "例如：把'他/她是我的一切'重构为'他/她是我生命中重要的一部分，"
            "但不是全部；我本身就是完整的'。"
        ),
        "meta": {"topic": "CBT", "source": "Beck, 1979"},
    },
    {
        "id": "breakup_recovery_timeline",
        "text": (
            "分手恢复的典型阶段：第1-2周急性痛苦期（情绪最强烈）；"
            "第3-8周适应期（开始重建日常）；第2-6个月整合期（意义建构）；"
            "6个月后成长期（重获自我）。平均情感恢复时间约为关系时长的1/4到1/2。"
        ),
        "meta": {"topic": "recovery_timeline", "source": "关系心理学研究综述"},
    },
    {
        "id": "self_compassion",
        "text": (
            "克里斯汀·内夫自我慈悲三要素：自我善待（对自己像对好朋友一样温柔）、"
            "共同人性（痛苦是人类共有体验，我并不孤独）、正念（不夸大也不压抑情绪，"
            "只是观察）。分手后对自己苛责会延长痛苦，自我慈悲能加速恢复。"
        ),
        "meta": {"topic": "self_compassion", "source": "Neff, 2003"},
    },
    {
        "id": "emotion_regulation",
        "text": (
            "情绪调节策略：箱式呼吸（吸气4秒→屏息4秒→呼气4秒→屏息4秒）激活副交感神经；"
            "情绪命名技术——用语言精确描述情绪可降低杏仁核活跃度；"
            "5-4-3-2-1 grounding 技术帮助从反刍思维中抽身。"
        ),
        "meta": {"topic": "emotion_regulation", "source": "DBT / 正念研究"},
    },
    {
        "id": "rumination_vs_reflection",
        "text": (
            "反刍（Rumination）与反思（Reflection）的区别：反刍是重复回放痛苦场景、"
            "停留在'为什么会这样'；反思是带着好奇心分析'我学到了什么'。"
            "将反刍转化为反思的方法：设定30分钟'担忧时间'，其余时间主动转移注意力。"
        ),
        "meta": {"topic": "cognitive_patterns", "source": "Nolen-Hoeksema, 2003"},
    },
    {
        "id": "no_contact_rationale",
        "text": (
            "断联的心理学依据：保持联系会激活大脑的奖励回路（多巴胺期待），"
            "类似物质戒断反应。神经科学研究显示，失恋激活的脑区与戒除成瘾相同。"
            "断联30天能显著降低痛苦程度，帮助神经回路重新连接。"
        ),
        "meta": {"topic": "no_contact", "source": "Fisher et al., 2010"},
    },
    {
        "id": "identity_reconstruction",
        "text": (
            "分手后的自我重构：长期关系中我们的'自我概念'会包含对方，分手即'自我丧失'。"
            "恢复方法：列出独立于这段关系存在的个人兴趣、价值观和目标；"
            "重新拥抱被关系占用前就存在的自我。"
        ),
        "meta": {"topic": "identity", "source": "Slotter et al., 2010"},
    },
    {
        "id": "closure_letter_therapy",
        "text": (
            "写信疗法（未发送的告别信）：心理学研究表明，将未表达的情感写成信件"
            "能显著降低情绪困扰，促进意义建构。重点不在于发送，而在于将混乱的情绪"
            "外化为文字，获得叙事掌控感。"
        ),
        "meta": {"topic": "writing_therapy", "source": "Pennebaker, 1997"},
    },
    {
        "id": "post_traumatic_growth",
        "text": (
            "创伤后成长（PTG）：约50-70%经历失恋创伤的人报告正向改变，包括"
            "人际关系感激度提升、个人力量感增强、人生新可能性的发现、精神/哲学层面的深化。"
            "PTG 不是否定痛苦，而是痛苦与成长并存。"
        ),
        "meta": {"topic": "PTG", "source": "Tedeschi & Calhoun, 2004"},
    },
    {
        "id": "healthy_boundaries",
        "text": (
            "健康边界设置：分手后常见的边界侵犯包括——反复检查对方社交媒体（数字窥探）、"
            "保留大量合照（记忆触发物）、参加共同朋友聚会时期待重逢。"
            "心理健康边界是：为自己创造心理安全空间，而非惩罚对方。"
        ),
        "meta": {"topic": "boundaries", "source": "亲密关系心理学"},
    },
]

# ─────────────────────────────────────────────────────────────
# ChromaDB 集合（单例，延迟初始化）
# ─────────────────────────────────────────────────────────────

_collection = None                                   # 延迟加载，避免启动时阻塞
_RAG_DB_DIR = Path(__file__).resolve().parent / "_chroma_db"


def _get_collection():
    """
    获取（或初始化）ChromaDB 集合（单例）

    首次调用时：
      1. 创建本地持久化客户端（数据存储在 rag/_chroma_db/）
      2. 若集合为空，批量写入 SEED_DOCS 种子文档
    后续调用：直接返回已有集合
    """
    global _collection
    if _collection is not None:
        return _collection

    import chromadb  # 延迟导入，仅在真正使用时触发依赖检查

    client = chromadb.PersistentClient(path=str(_RAG_DB_DIR))
    col = client.get_or_create_collection(
        name="psych_knowledge",
        metadata={"hnsw:space": "cosine"},   # 余弦相似度，更适合语义匹配
    )

    # 种子数据仅在集合为空时写入（避免重复）
    if col.count() == 0:
        col.add(
            ids=[d["id"] for d in SEED_DOCS],
            documents=[d["text"] for d in SEED_DOCS],
            metadatas=[d["meta"] for d in SEED_DOCS],
        )
        logger.info("[RAG] 知识库初始化完成，已写入 %d 条心理学文档", len(SEED_DOCS))

    _collection = col
    return _collection


# ─────────────────────────────────────────────────────────────
# 公开接口
# ─────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = 3) -> str:
    """
    根据用户描述，检索最相关的心理学知识片段

    参数:
        query: 用户的情绪描述或问题（直接使用原始用户消息）
        k:     返回的片段数量，默认 3 条

    返回:
        格式化的参考资料字符串（空字符串表示检索失败，调用方静默跳过即可）

    异常:
        不会抛出任何异常；所有错误静默降级，返回空字符串
    """
    if not query or not query.strip():
        return ""

    try:
        col = _get_collection()
        results = col.query(
            query_texts=[query],
            n_results=min(k, col.count()),
            include=["documents", "distances"],
        )
        docs: List[str] = results.get("documents", [[]])[0]
        dists: List[float] = results.get("distances", [[]])[0]

        if not docs:
            return ""

        # 过滤相似度过低的结果（余弦距离 > 0.85 视为不相关）
        relevant = [
            doc for doc, dist in zip(docs, dists) if dist < 0.85
        ]
        if not relevant:
            return ""

        lines = "\n".join(f"• {doc}" for doc in relevant)
        return f"[心理学参考资料]\n{lines}"

    except ImportError:
        logger.warning("[RAG] chromadb 未安装，跳过向量检索（pip install chromadb）")
        return ""
    except Exception as exc:
        logger.warning("[RAG] 检索失败，静默跳过: %s", exc)
        return ""
