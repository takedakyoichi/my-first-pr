from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field, conlist

Fieldname = Literal["law", "civil", "protection", "finance"]


class RawQuestion(BaseModel):
    """Vision が1問分として返す生データ（IDなし）。"""
    stem: str
    choices: conlist(str, min_length=4, max_length=4)
    answerIndex: int = Field(ge=0, le=3)
    explanation: str


class RawTopic(BaseModel):
    """Vision が1要点として返す生データ。配下に関連問題を持つ。"""
    field: Fieldname
    chapter: str
    title: str
    body: str
    questions: List[RawQuestion]


class PageExtraction(BaseModel):
    """画像1枚分の抽出結果。"""
    topics: List[RawTopic]


class Question(BaseModel):
    """content.json に保存する問題（IDとリンク付き）。"""
    id: str
    field: Fieldname
    topicId: str
    stem: str
    choices: List[str]
    answerIndex: int
    explanation: str


class Topic(BaseModel):
    """content.json に保存する要点（テキスト学習の単位）。"""
    id: str
    field: Fieldname
    chapter: str
    title: str
    body: str
    relatedQuestionIds: List[str]


class Content(BaseModel):
    """content.json 全体。"""
    version: int = 1
    generatedAt: str
    topics: List[Topic] = Field(default_factory=list)
    questions: List[Question] = Field(default_factory=list)
