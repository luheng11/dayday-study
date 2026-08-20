"""Prompt 契约测试：验证 Prompt 模板变量完整、可格式化、含 K12 约束"""

from app.prompts.quiz_prompt import (
    QUIZ_HUMAN_PROMPT,
    QUIZ_SYSTEM_PROMPT,
    format_type_ratio_instruction,
)
from app.prompts.report_prompt import REPORT_HUMAN_PROMPT, REPORT_SYSTEM_PROMPT


class TestQuizPrompt:
    def test_system_prompt_requires_pure_json(self):
        assert "JSON" in QUIZ_SYSTEM_PROMPT
        assert "json" in QUIZ_SYSTEM_PROMPT.lower()

    def test_system_prompt_is_k12_oriented(self):
        assert "中小学" in QUIZ_SYSTEM_PROMPT

    def test_human_prompt_has_all_placeholders(self):
        for ph in (
            "{user_input}",
            "{question_count}",
            "{difficulty}",
            "{search_context_section}",
            "{type_ratio_instruction}",
        ):
            assert ph in QUIZ_HUMAN_PROMPT

    def test_human_prompt_formattable(self):
        result = QUIZ_HUMAN_PROMPT.format(
            user_input="光合作用",
            question_count=5,
            difficulty="medium",
            search_context_section="",
            type_ratio_instruction="3:1:1",
        )
        assert "光合作用" in result
        assert "5" in result

    def test_k12_constraints_present(self):
        assert "中小学生" in QUIZ_HUMAN_PROMPT
        assert "口语化" in QUIZ_HUMAN_PROMPT
        assert "积极健康" in QUIZ_HUMAN_PROMPT
        assert "判断题选项固定为 A 正确、B 错误" in QUIZ_HUMAN_PROMPT
        assert "多选题" in QUIZ_HUMAN_PROMPT

    def test_explanation_two_parts_required(self):
        assert "①" in QUIZ_HUMAN_PROMPT and "②" in QUIZ_HUMAN_PROMPT

    def test_type_ratio_3_questions(self):
        text = format_type_ratio_instruction(3)
        assert "各 1 题" in text

    def test_type_ratio_5_questions(self):
        text = format_type_ratio_instruction(5)
        assert "3:1:1" in text or "3 道单选" in text

    def test_type_ratio_other_counts(self):
        text = format_type_ratio_instruction(10)
        assert "3:1:1" in text


class TestReportPrompt:
    def test_system_prompt_requires_pure_json(self):
        assert "JSON" in REPORT_SYSTEM_PROMPT

    def test_system_prompt_k12_encouraging(self):
        assert "中小学" in REPORT_SYSTEM_PROMPT or "鼓励" in REPORT_SYSTEM_PROMPT

    def test_human_prompt_has_all_placeholders(self):
        for ph in ("{topic}", "{quiz_json}", "{answer_records}", "{score_summary}"):
            assert ph in REPORT_HUMAN_PROMPT

    def test_human_prompt_formattable(self):
        result = REPORT_HUMAN_PROMPT.format(
            topic="光合作用",
            quiz_json="[]",
            answer_records="[]",
            score_summary="{}",
        )
        assert "光合作用" in result

    def test_share_quote_requirement_present(self):
        assert "share_quote" in REPORT_HUMAN_PROMPT

    def test_no_fabrication_constraint_present(self):
        assert "不编造" in REPORT_HUMAN_PROMPT
