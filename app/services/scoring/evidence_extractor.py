"""证据抽取模块：从作答文本中提取可核验的关键证据片段"""
import re
from typing import List, Dict, Any

from app.core.config import settings
from app.models.schemas import QuestionDefinition

# 可配置的证据抽取规则（方便修改）
EVIDENCE_EXTRACT_RULES = {
    "min_length": 5,  # 证据片段最小长度
    "max_length": 50,  # 证据片段最大长度
    "keyword_match_weight": 0.8,  # 关键词匹配权重
    "semantic_match_weight": 0.2,  # 语义匹配权重（预留扩展）
}

def extract_evidence(text: str, question: QuestionDefinition) -> List[str]:
    """
    从作答文本中抽取与题目相关的证据片段
    :param text: 考生作答原文
    :param question: 题目定义
    :return: 去重后的证据片段列表
    """
    normalized_text = _normalize_text(text)
    all_keywords = (
        question.coreKeywords + question.strongKeywords + 
        question.bonusKeywords + question.penaltyKeywords
    )
    
    # 1. 基于关键词匹配抽取证据片段
    keyword_evidence = _extract_by_keywords(normalized_text, text, all_keywords)
    # 2. 预留扩展：语义匹配抽取（可自行补充）
    semantic_evidence = _extract_by_semantic(normalized_text, text, question)
    
    # 合并去重
    all_evidence = list({*keyword_evidence, *semantic_evidence})
    # 过滤长度不符合规则的片段
    filtered_evidence = [
        seg.strip() for seg in all_evidence
        if EVIDENCE_EXTRACT_RULES["min_length"] <= len(seg.strip()) <= EVIDENCE_EXTRACT_RULES["max_length"]
    ]
    
    return filtered_evidence[:5]  # 最多返回5条证据

def _normalize_text(text: str) -> str:
    """标准化文本（去空格、小写）"""
    return re.sub(r"\s+", "", text.lower())

def _extract_by_keywords(normalized_text: str, raw_text: str, keywords: List[str]) -> List[str]:
    """基于关键词抽取证据片段"""
    evidence = []
    for keyword in keywords:
        if not keyword:
            continue
        norm_keyword = _normalize_text(keyword)
        if norm_keyword not in normalized_text:
            continue
        
        # 提取关键词前后的上下文作为证据片段
        keyword_pos = normalized_text.find(norm_keyword)
        raw_pos = _find_raw_position(raw_text, norm_keyword, keyword_pos)
        if raw_pos == -1:
            continue
        
        # 截取上下文（可调整截取长度）
        start = max(0, raw_pos - 20)
        end = min(len(raw_text), raw_pos + len(keyword) + 20)
        evidence.append(raw_text[start:end])
    
    return evidence

def _extract_by_semantic(normalized_text: str, raw_text: str, question: QuestionDefinition) -> List[str]:
    """语义匹配抽取（预留扩展，默认返回空）"""
    # 可自行实现：调用LLM/语义模型抽取相关证据
    return []

def _find_raw_position(raw_text: str, norm_keyword: str, norm_pos: int) -> int:
    """从原始文本中找到标准化关键词对应的原始位置"""
    # 简化实现：实际可优化为更精准的匹配
    raw_text_norm = _normalize_text(raw_text)
    if norm_pos >= len(raw_text_norm):
        return -1
    # 反向查找原始文本的位置（简化版）
    char_count = 0
    for idx, char in enumerate(raw_text):
        if _normalize_text(char) == raw_text_norm[norm_pos]:
            char_count += 1
            if char_count == len(norm_keyword):
                return idx - len(norm_keyword) + 1
    return -1

def get_evidence_extract_rules() -> Dict[str, Any]:
    """获取证据抽取规则（方便外部修改/配置）"""
    return EVIDENCE_EXTRACT_RULES.copy()

def update_evidence_extract_rules(new_rules: Dict[str, Any]) -> None:
    """更新证据抽取规则"""
    global EVIDENCE_EXTRACT_RULES
    EVIDENCE_EXTRACT_RULES.update(new_rules)