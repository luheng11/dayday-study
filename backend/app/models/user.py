"""用户系统相关数据模型（与前端 services/types.ts 一一对应）"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    code: str = Field(min_length=1, description="wx.login() 返回的 code")


class UserBrief(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    total_xp: int


class LoginResponse(BaseModel):
    token: str
    user: UserBrief


class LevelInfo(BaseModel):
    level: int
    title: str
    level_start_xp: int
    level_end_xp: Optional[int] = None
    is_max: bool


class UserProfile(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    total_xp: int
    quiz_count: int
    correct_count: int
    average_accuracy: int
    week_quiz_count: int
    streak_days: int
    level: LevelInfo


class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=30)
    avatar_url: Optional[str] = Field(default=None, max_length=500)


class QuizHistoryItem(BaseModel):
    quiz_id: str
    title: str
    user_input: Optional[str] = None
    accuracy: float
    question_count: int
    duration_ms: int
    created_at: str
    has_report: bool
    report_snippet: Optional[str] = None


class QuizHistoryList(BaseModel):
    items: list[QuizHistoryItem]
    total: int
    page: int
    page_size: int


class QuizDetailResponse(BaseModel):
    quiz_id: str
    title: str
    summary: str
    user_input: Optional[str] = None
    questions: list[Any]
    answer_records: Optional[list[Any]] = None
    report: Optional[dict] = None
    created_at: str


class DailyStat(BaseModel):
    date: str
    label: str
    accuracy: Optional[int] = None
    quiz_count: int


class MasteryItem(BaseModel):
    knowledge_point: str
    accuracy: int


class WeakPointItem(BaseModel):
    knowledge_point: str
    accuracy: int
    quiz_title: str


class UserStats(BaseModel):
    days: list[DailyStat]
    average_accuracy_7d: int
    mastery: list[MasteryItem]
    weak_points: list[WeakPointItem]
    streak_days: int
