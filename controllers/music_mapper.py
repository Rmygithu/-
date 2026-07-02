"""
音乐解析控制器
负责：从 Agent 回复文本中解析歌单结构化数据

架构说明
--------
Agent 层只输出"歌名 - 歌手"纯文本，完全不涉及链接。
本模块在 Controller 层解析为结构化列表，
UI 层将每首歌渲染为音乐平台搜索跳转链接。

严格遵循 Agent → Controller → UI 的分层原则。
"""

import re
from typing import List, Dict


def build_search_url(title: str, artist: str) -> str:
    """
    构建网易云音乐搜索跳转 URL

    参数:
        title:  歌曲名称
        artist: 歌手名称

    返回:
        可直接在浏览器中打开的搜索页面 URL
    """
    from urllib.parse import quote
    query = f"{title} {artist}".strip()
    encoded = quote(query)
    return f"https://music.163.com/#/search/m/?s={encoded}&type=1"


def parse_song_list(raw_text: str) -> List[Dict[str, str]]:
    """
    从 Agent 回复文本中解析歌单列表

    期望格式（数字列表，「歌名 - 歌手」或「歌名」）：
        1. 城南花已开 - 三亩地
        2. River Flows in You - Yiruma
        3. 夜的钢琴曲五

    参数:
        raw_text: Agent 的完整回复文本

    返回:
        [{"title": str, "artist": str, "search_url": str}, ...]
        每条都带有网易云音乐搜索直链
    """
    songs: List[Dict[str, str]] = []

    # 匹配有序列表条目：1. / 1、/ 1） 等多种前缀格式
    line_pattern = re.compile(
        r'^\s*(?:\d+[\.、。）)]\s*|[①②③④⑤⑥⑦⑧⑨⑩]\s*)'  # 序号前缀
        r'(?:🎵\s*)?'                                           # 可选 emoji
        r'(.+?)$',
        re.MULTILINE | re.UNICODE,
    )

    # 分离「歌名 - 歌手」（支持全半角连字符）
    sep_pattern = re.compile(r'\s*[-–—]\s*')

    for m in line_pattern.finditer(raw_text):
        raw_item = m.group(1).strip()
        if not raw_item:
            continue

        parts = sep_pattern.split(raw_item, maxsplit=1)
        title  = re.sub(r'[*_`]', '', parts[0]).strip()
        artist = parts[1].strip() if len(parts) > 1 else ""

        if not title:
            continue

        songs.append({
            "title":      title,
            "artist":     artist,
            "search_url": build_search_url(title, artist),
        })

    return songs[:8]  # 最多保留8首
