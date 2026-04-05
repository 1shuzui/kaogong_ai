"""Interview workflow orchestration service."""
import logging
from pathlib import Path

from app.core.config import settings
from app.models.schemas import EvaluationResult, MediaExtractionResult
from app.services.llm.client import LLMClient
from app.services.media.video_processor import process_audio, process_video
from app.services.question_bank import QuestionBank
from app.services.scoring.calculator import apply_post_processing
from app.services.scoring.prompts import build_evaluation_prompt
# 第一轮新增：导入证据抽取和评分模块
from app.services.scoring.evidence_extractor import extract_evidence
from app.services.scoring.evidence_scorer import score_evidence

logger = logging.getLogger(__name__)

class InterviewFlowService:
    """Coordinate media extraction, LLM scoring, and deterministic validation."""

    def __init__(self, llm_client: LLMClient, question_bank: QuestionBank):
        self.llm_client = llm_client
        self.question_bank = question_bank

    def validate_media_suffix(self, filename: str) -> None:
        """Ensure the uploaded media extension is supported."""

        suffix = Path(filename).suffix.lower()
        supported_extensions = (
            set(settings.SUPPORTED_VIDEO_EXTENSIONS)
            | set(settings.SUPPORTED_AUDIO_EXTENSIONS)
        )
        if suffix not in supported_extensions:
            supported = ", ".join(sorted(supported_extensions))
            raise ValueError(f"不支持的媒体格式: {suffix or '无后缀'}。支持格式: {supported}")

    def _extract_from_media(self, file_path: str) -> MediaExtractionResult:
        suffix = Path(file_path).suffix.lower()
        if suffix in settings.SUPPORTED_VIDEO_EXTENSIONS:
            return process_video(file_path)
        if suffix in settings.SUPPORTED_AUDIO_EXTENSIONS:
            return process_audio(file_path)
        raise ValueError(f"不支持的媒体格式: {suffix or '无后缀'}")

    def _execute_evaluation_core(
        self,
        question_id: str,
        extraction_result: MediaExtractionResult,
    ) -> EvaluationResult:
        question = self.question_bank.get_question(question_id)

        # ===== 第一轮新增：证据抽取 → 证据评分 链路 =====
        # 1. 抽取证据
        evidence_list = extract_evidence(extraction_result.transcript, question)
        logger.info("抽取到证据片段 %s 条: %s", len(evidence_list), evidence_list)
        
        # 2. 证据评分
        evidence_score_result = score_evidence(
            evidence_list=evidence_list,
            text=extraction_result.transcript,
            question=question
        )
        logger.info("证据评分结果: %s", evidence_score_result)
        # ==========================================

        # ===== 第一轮新增：将证据信息传入prompt（修改build_evaluation_prompt调用） =====
        prompt = build_evaluation_prompt(
            question=question,
            answer_text=extraction_result.transcript,
            visual_observation=extraction_result.visual_observation,
            # 新增参数：证据列表和证据评分
            evidence_list=evidence_list,
            evidence_score_result=evidence_score_result
        )
        raw_llm_result = self.llm_client.generate(prompt)
        if raw_llm_result is None:
            raise RuntimeError("大模型评估引擎响应失败或返回结果无法解析。")

        # ===== 第一轮新增：将证据评分结果传入后处理（修改apply_post_processing调用） =====
        evaluation_result = apply_post_processing(
            raw_llm_result=raw_llm_result,
            transcript=extraction_result.transcript,
            question=question,
            visual_observation=extraction_result.visual_observation,
            # 新增参数：证据信息
            evidence_list=evidence_list,
            evidence_score_result=evidence_score_result
        )
        
        # ===== 第一轮新增：将证据信息添加到最终结果中 =====
        evaluation_result.evidence_extracted = evidence_list  # 抽取的证据
        evaluation_result.evidence_score = evidence_score_result  # 证据评分
        
        return evaluation_result
    def process_and_evaluate(self, question_id: str, file_path: str) -> EvaluationResult:
        """Evaluate an uploaded audio/video submission."""

        extraction_result = self._extract_from_media(file_path)
        if not extraction_result.transcript.strip():
            raise ValueError("未能从媒体文件中提取到有效语音内容。")
        return self._execute_evaluation_core(question_id, extraction_result)

    def evaluate_text_only(self, question_id: str, text_content: str) -> EvaluationResult:
        """Evaluate a plain-text answer without the media preprocessing stage."""

        logger.info("启动纯文本测评旁路, question_id=%s, 文本长度=%s", question_id, len(text_content))
        if not text_content.strip():
            raise ValueError("文本内容为空，无法进行评估。")

        return self._execute_evaluation_core(
            question_id=question_id,
            extraction_result=MediaExtractionResult(
                transcript=text_content.strip(),
                source="text",
                visual_observation=None,
            ),
        )
