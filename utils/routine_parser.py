"""
恢复规划解析工具
将 routine agent 输出的 7 天计划文本解析为结构化数据，供 UI 表格渲染和任务打卡使用
"""

import re
from typing import Optional, List, Dict


def parse_7day_plan(response: str) -> Optional[List[Dict]]:
    """
    解析 routine agent 输出的 7 天恢复计划

    期望格式（每天一组，依次出现）：
        **第1天 · 主题名称**
        - 任务1：具体描述
        - 任务2：具体描述
        - 任务3：具体描述

    支持全角/半角冒号，支持「·」「·」「—」等分隔符，兼容前后空白。

    参数:
        response: routine agent 的完整输出文本

    返回:
        成功返回 [{"day": int, "theme": str, "tasks": [str, str, str]}, ...] 共7项；
        解析结果不足7天则返回 None
    """
    results: List[Dict] = []

    # 匹配每天的标题行：**第N天 · 主题** 或 **第N天—主题** 等
    # 然后紧跟3行 `- 任务N：内容`
    day_header_pattern = re.compile(
        r'\*\*第\s*(\d+)\s*天\s*[··—\-\s]+\s*(.+?)\*\*',
        re.UNICODE,
    )
    task_line_pattern = re.compile(
        r'-\s*任务\s*[1-3一二三]\s*[：:]\s*(.+)',
        re.UNICODE,
    )

    lines = response.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        header_match = day_header_pattern.search(line)
        if header_match:
            day_num = int(header_match.group(1))
            theme = header_match.group(2).strip()

            # 向后扫描，收集3个任务行（允许中间有空行）
            tasks: List[str] = []
            j = i + 1
            while j < len(lines) and len(tasks) < 3:
                t_line = lines[j].strip()
                if t_line:
                    task_match = task_line_pattern.search(t_line)
                    if task_match:
                        tasks.append(task_match.group(1).strip())
                    elif tasks:
                        # 遇到非任务行且已有任务，停止收集（进入下一天）
                        break
                j += 1

            if len(tasks) == 3:
                results.append({
                    "day": day_num,
                    "theme": theme,
                    "tasks": tasks,
                })
                i = j
                continue
        i += 1

    if len(results) < 7:
        return None

    # 按天数排序，取前7天
    results.sort(key=lambda x: x["day"])
    return results[:7]
