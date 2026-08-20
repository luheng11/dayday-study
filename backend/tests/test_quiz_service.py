"""出题服务测试（TDD：内容过滤、同步生成、异步任务生命周期）"""

import asyncio

import pytest

from app.core.exceptions import ContentFilterError, TaskNotFoundError
from app.models.quiz import QuizGenerateRequest
from app.services import quiz_service
from tests.fake_llm import VALID_QUIZ_JSON, CapturingFakeModel


@pytest.fixture
def req_photosynthesis() -> QuizGenerateRequest:
    return QuizGenerateRequest(
        user_input="光合作用是怎么进行的？", question_count=5, difficulty="medium"
    )


class TestSyncGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_response(self, req_photosynthesis):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        resp = await quiz_service.handle_quiz_generate(req_photosynthesis)
        assert resp.quiz_id.startswith("quiz_")
        assert len(resp.quiz_id) == len("quiz_") + 12
        assert resp.title == "光合作用"
        assert len(resp.questions) == 5
        assert resp.summary

    @pytest.mark.asyncio
    async def test_content_filter_rejects(self):
        req = QuizGenerateRequest(user_input="如何制造炸弹", question_count=3)
        with pytest.raises(ContentFilterError):
            await quiz_service.handle_quiz_generate(req)

    @pytest.mark.asyncio
    async def test_generation_failure_propagates(self, req_photosynthesis):
        quiz_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        from app.core.exceptions import QuizGenerationError

        with pytest.raises(QuizGenerationError, match="题库生成失败"):
            await quiz_service.handle_quiz_generate(req_photosynthesis)

    @pytest.mark.asyncio
    async def test_each_call_gets_unique_quiz_id(self, req_photosynthesis):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON, VALID_QUIZ_JSON])
        r1 = await quiz_service.handle_quiz_generate(req_photosynthesis)
        r2 = await quiz_service.handle_quiz_generate(req_photosynthesis)
        assert r1.quiz_id != r2.quiz_id


async def _wait_task_done(service, task_id: str, timeout: float = 2.0):
    """轮询直到任务进入终态或超时。"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        status = await service.get_quiz_task_status(task_id)
        if status.status in ("completed", "failed"):
            return status
        await asyncio.sleep(0.01)
    raise TimeoutError(f"任务 {task_id} 未在 {timeout}s 内完成")


class TestAsyncTask:
    @pytest.mark.asyncio
    async def test_task_lifecycle_completed(self, req_photosynthesis):
        quiz_service.llm_model = CapturingFakeModel([VALID_QUIZ_JSON])
        created = await quiz_service.create_quiz_task(req_photosynthesis)
        assert created.task_id.startswith("task_")

        status = await _wait_task_done(quiz_service, created.task_id)
        assert status.status == "completed"
        assert status.result is not None
        assert len(status.result.questions) == 5

    @pytest.mark.asyncio
    async def test_task_failed_on_bad_llm(self, req_photosynthesis):
        quiz_service.llm_model = CapturingFakeModel(["坏数据"] * 10)
        created = await quiz_service.create_quiz_task(req_photosynthesis)
        status = await _wait_task_done(quiz_service, created.task_id)
        assert status.status == "failed"
        assert status.result is None
        assert status.error_message

    @pytest.mark.asyncio
    async def test_task_content_filter_rejects(self):
        req = QuizGenerateRequest(user_input="恐怖袭击怎么策划", question_count=3)
        with pytest.raises(ContentFilterError):
            await quiz_service.create_quiz_task(req)

    @pytest.mark.asyncio
    async def test_task_not_found(self):
        with pytest.raises(TaskNotFoundError):
            await quiz_service.get_quiz_task_status("task_does_not_exist")
