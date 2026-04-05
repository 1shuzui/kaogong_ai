"""证据评分模块：对抽取的证据片段进行相关性/有效性评分"""
from typing import List, Dict, Any

from app.models.schemas import QuestionDefinition

# 可配置的证据评分维度（方便修改）
EVIDENCE_SCORING_DIMENSIONS = {
    "relevance": {"name": "相关性", "max_score": 5.0, "weight": 0.6},  # 与题目相关度
    "completeness": {"name": "完整性", "max_score": 5.0, "weight": 0.2},  # 证据完整性
    "accuracy": {"name": "准确性", "max_score": 5.0, "weight": 0.2},  # 证据准确性
}

def score_evidence(evidence_list: List[str], text: str, question: QuestionDefinition) -> Dict[str, Any]:
    """
    对抽取的证据进行评分
    :param evidence_list: 证据片段列表
    :param text: 考生作答原文
    :param question: 题目定义
    :return: 证据评分结果
    """
    if not evidence_list:
        return {
            "total_score": 0.0,
            "dimension_scores": {dim["name"]: 0.0 for dim in EVIDENCE_SCORING_DIMENSIONS.values()},
            "evidence_details": []
        }
    
    evidence_scores = []
    dimension_total = {dim["name"]: 0.0 for dim in EVIDENCE_SCORING_DIMENSIONS.values()}
    
    for evidence in evidence_list:
        # 计算单条证据的各维度得分
        relevance = _score_relevance(evidence, question)
        completeness = _score_completeness(evidence, text)
        accuracy = _score_accuracy(evidence, text)
        
        dim_scores = {
            EVIDENCE_SCORING_DIMENSIONS["relevance"]["name"]: relevance,
            EVIDENCE_SCORING_DIMENSIONS["completeness"]["name"]: completeness,
            EVIDENCE_SCORING_DIMENSIONS["accuracy"]["name"]: accuracy,
        }
        
        # 计算单条证据加权总分
        weighted_score = sum(
            dim_scores[dim["name"]] * dim["weight"]
            for dim in EVIDENCE_SCORING_DIMENSIONS.values()
        )
        
        evidence_scores.append({
            "evidence": evidence,
            "dimension_scores": dim_scores,
            "weighted_score": round(weighted_score, 2)
        })
        
        # 累计维度总分
        for dim_name, score in dim_scores.items():
            dimension_total[dim_name] += score
    
    # 计算整体证据评分（平均）
    avg_dim_scores = {
        dim_name: round(total / len(evidence_list), 2)
        for dim_name, total in dimension_total.items()
    }
    total_score = round(
        sum(avg_dim_scores[dim["name"]] * dim["weight"] for dim in EVIDENCE_SCORING_DIMENSIONS.values()),
        2
    )
    
    return {
        "total_score": total_score,
        "dimension_scores": avg_dim_scores,
        "evidence_details": evidence_scores
    }

def _score_relevance(evidence: str, question: QuestionDefinition) -> float:
    """评分：证据与题目的相关度（0-5分）"""
    # 简化实现：基于关键词匹配度计算，可自行优化
    evidence_lower = evidence.lower()
    keywords = question.coreKeywords + question.strongKeywords
    match_count = sum(1 for kw in keywords if kw.lower() in evidence_lower)
    max_match = len(keywords) if keywords else 1
    relevance = (match_count / max_match) * EVIDENCE_SCORING_DIMENSIONS["relevance"]["max_score"]
    return round(relevance, 2)

def _score_completeness(evidence: str, text: str) -> float:
    """评分：证据的完整性（0-5分）"""
    # 简化实现：证据长度占比，可自行优化
    evidence_len = len(evidence.strip())
    text_len = len(text.strip()) if len(text.strip()) > 0 else 1
    completeness = (evidence_len / text_len) * EVIDENCE_SCORING_DIMENSIONS["completeness"]["max_score"]
    return min(round(completeness, 2), EVIDENCE_SCORING_DIMENSIONS["completeness"]["max_score"])

def _score_accuracy(evidence: str, text: str) -> float:
    """评分：证据的准确性（0-5分）"""
    # 简化实现：证据是否完全来自原文，可自行优化
    if evidence.strip() in text:
        return EVIDENCE_SCORING_DIMENSIONS["accuracy"]["max_score"]
    return round(EVIDENCE_SCORING_DIMENSIONS["accuracy"]["max_score"] * 0.5, 2)

def get_evidence_scoring_dimensions() -> Dict[str, Any]:
    """获取证据评分维度配置（方便修改）"""
    return EVIDENCE_SCORING_DIMENSIONS.copy()

def update_evidence_scoring_dimensions(new_dimensions: Dict[str, Any]) -> None:
    """更新证据评分维度配置"""
    global EVIDENCE_SCORING_DIMENSIONS
    EVIDENCE_SCORING_DIMENSIONS.update(new_dimensions)