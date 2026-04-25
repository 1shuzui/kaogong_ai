"""评分流程与违规前置检测测试。"""

import sys
import types
import unittest

from app.models.schemas import LLMGenerationResult, QuestionDefinition
from app.services.scoring.prompts import build_violation_check_prompt


# 当前测试环境未安装 sqlalchemy，这里在导入 flow 前注入最小桩模块，
# 避免无关的持久化依赖阻塞流程逻辑测试。
stub_evaluation_store_module = types.ModuleType("app.services.evaluation_store")


class _StubImportedEvaluationStore:
    pass


stub_evaluation_store_module.EvaluationStore = _StubImportedEvaluationStore
sys.modules.setdefault("app.services.evaluation_store", stub_evaluation_store_module)

from app.services.flow import InterviewFlowService


class StubQuestionBank:
    """最小题库桩，返回固定题目。"""

    def __init__(self, question: QuestionDefinition):
        self.question = question

    def get_question(self, question_id: str) -> QuestionDefinition:
        return self.question


class StubEvaluationStore:
    """测试里不落库，只保留接口形状。"""

    def save_evaluation(self, **kwargs):
        return kwargs["final_result"]


class StubLLMClient:
    """可编排返回结果的大模型桩。"""

    def __init__(self, responses=None, *, enabled: bool = True):
        self.provider = "TEST"
        self.model_name = "stub-model"
        self.client = object() if enabled else None
        self.responses = list(responses or [])
        self.calls: list[dict[str, str]] = []

    def generate(self, prompt: str, system_message: str | None = None):
        self.calls.append(
            {
                "prompt": prompt,
                "system_message": system_message or "",
            }
        )
        if not self.responses:
            return None
        return self.responses.pop(0)


class ScoringFlowViolationTestCase(unittest.TestCase):
    """锁住违规检测阶段的关键行为。"""

    def setUp(self):
        self.question = QuestionDefinition(
            id="AH-TEST-001",
            type="综合分析",
            province="安徽",
            fullScore=10,
            question="请结合实际谈谈你的理解。",
            dimensions=[
                {"name": "现象解读", "score": 5},
                {"name": "对策建议", "score": 5},
            ],
            scoringCriteria=["现象解读（5分）", "对策建议（5分）"],
        )

    def test_violation_prompt_mentions_core_categories_and_json_contract(self):
        prompt = build_violation_check_prompt(
            self.question,
            "我觉得应该坚持廉洁自律，不能行贿受贿。",
        )

        self.assertIn("政治红线", prompt)
        self.assertIn("廉政", prompt)
        self.assertIn('"is_violation"', prompt)
        self.assertIn('"matched_terms"', prompt)
        self.assertIn("不能行贿受贿", prompt)

    def test_rule_based_violation_blocks_before_any_llm_scoring_stage(self):
        llm_client = StubLLMClient()
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="你就是个傻逼，根本不配坐这里。",
            persist=False,
        )

        self.assertTrue(result.violation_detected)
        self.assertEqual(result.total_score, 0.0)
        self.assertEqual(result.violation_category, "abuse")
        self.assertIn("傻逼", result.violation_terms)
        self.assertTrue(any("阶段 0 本地规则检测命中" in note for note in result.validation_notes))
        self.assertEqual(len(llm_client.calls), 0)

    def test_llm_violation_blocks_before_evidence_and_scoring_prompts(self):
        llm_client = StubLLMClient(
            responses=[
                LLMGenerationResult(
                    raw_content='{"is_violation": true, "category": "integrity_red_line", "matched_terms": ["塞红包", "走后门"], "reason": "存在鼓吹行贿受贿和走后门的不当表达。"}',
                    parsed_payload={
                        "is_violation": True,
                        "category": "integrity_red_line",
                        "matched_terms": ["塞红包", "走后门"],
                        "reason": "存在鼓吹行贿受贿和走后门的不当表达。",
                    },
                )
            ]
        )
        service = InterviewFlowService(
            llm_client=llm_client,
            question_bank=StubQuestionBank(self.question),
            evaluation_store=StubEvaluationStore(),
        )

        result = service.evaluate_text_only(
            question_id=self.question.id,
            text_content="我觉得遇到这种情况，给领导塞红包、走后门会更快。",
            persist=False,
        )

        self.assertTrue(result.violation_detected)
        self.assertEqual(result.total_score, 0.0)
        self.assertEqual(result.violation_category, "integrity_red_line")
        self.assertEqual(result.violation_terms, ["塞红包", "走后门"])
        self.assertIn("已终止评分", result.rationale)
        self.assertTrue(any("阶段 0 模型检测命中" in note for note in result.validation_notes))
        self.assertEqual(len(llm_client.calls), 1)


if __name__ == "__main__":
    unittest.main()
