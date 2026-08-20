"""计分服务测试（TDD）"""

import pytest

from app.models.quiz import AnswerRecord
from app.services.scoring_service import compute_score_summary, compute_xp, total_xp


def rec(qid, correct, duration=3000):
    return AnswerRecord(
        question_id=qid,
        selected_answers=["A"],
        is_correct=correct,
        duration_ms=duration,
    )


class TestComputeScoreSummary:
    def test_empty_records(self):
        s = compute_score_summary([])
        assert s == {
            "total": 0,
            "correct": 0,
            "wrong": 0,
            "accuracy": 0,
            "avg_duration_ms": 0,
        }

    def test_all_correct(self):
        s = compute_score_summary([rec("q1", True), rec("q2", True)])
        assert s["total"] == 2
        assert s["correct"] == 2
        assert s["wrong"] == 0
        assert s["accuracy"] == 100

    def test_mixed(self):
        s = compute_score_summary(
            [rec("q1", True), rec("q2", True), rec("q3", False), rec("q4", True)]
        )
        assert s["total"] == 4
        assert s["correct"] == 3
        assert s["wrong"] == 1
        assert s["accuracy"] == 75

    def test_accuracy_rounds_up(self):
        # 2/3 = 66.67 → 67
        s = compute_score_summary([rec("q1", True), rec("q2", True), rec("q3", False)])
        assert s["accuracy"] == 67

    def test_avg_duration(self):
        s = compute_score_summary(
            [rec("q1", True, 1000), rec("q2", False, 3000), rec("q3", True, 5000)]
        )
        assert s["avg_duration_ms"] == 3000


class TestComputeXp:
    @pytest.mark.parametrize(
        "qtype, expected",
        [("single", 10), ("multiple", 15), ("judge", 10)],
    )
    def test_correct_xp_by_type(self, qtype, expected):
        assert compute_xp(qtype, True) == expected

    @pytest.mark.parametrize("qtype", ["single", "multiple", "judge"])
    def test_wrong_gets_zero(self, qtype):
        assert compute_xp(qtype, False) == 0


class TestTotalXp:
    def test_sum_across_types(self):
        # 单选对 +10、多选对 +15、判断对 +10、单选错 +0 = 35
        records = [
            rec("q1", True),
            rec("q2", True),
            rec("q3", True),
            rec("q4", False),
        ]
        types = {"q1": "single", "q2": "multiple", "q3": "judge", "q4": "single"}
        assert total_xp(records, types) == 35

    def test_unknown_question_ignored(self):
        records = [rec("q1", True)]
        assert total_xp(records, {"q2": "single"}) == 0
