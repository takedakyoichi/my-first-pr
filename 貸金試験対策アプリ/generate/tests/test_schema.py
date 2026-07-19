import pytest
from pydantic import ValidationError
from generate.schema import (
    RawQuestion, RawTopic, PageExtraction, Question, Topic, Content,
)


def test_raw_question_accepts_four_choices():
    q = RawQuestion(
        stem="貸金業を営むには何が必要か。",
        choices=["登録", "許可", "免許", "認可"],
        answerIndex=0,
        explanation="貸金業法3条により登録が必要。",
    )
    assert q.answerIndex == 0
    assert len(q.choices) == 4


def test_raw_question_rejects_wrong_choice_count():
    with pytest.raises(ValidationError):
        RawQuestion(stem="x", choices=["a", "b", "c"], answerIndex=0, explanation="e")


def test_raw_question_rejects_out_of_range_answer():
    with pytest.raises(ValidationError):
        RawQuestion(stem="x", choices=["a", "b", "c", "d"], answerIndex=4, explanation="e")


def test_topic_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Topic(id="t-001", field="tax", chapter="c", title="t", body="b", relatedQuestionIds=[])


def test_content_roundtrips_json():
    content = Content(
        version=1,
        generatedAt="2026-07-19T00:00:00+00:00",
        topics=[Topic(id="t-001", field="law", chapter="総則", title="定義",
                      body="要点", relatedQuestionIds=["q-001"])],
        questions=[Question(id="q-001", field="law", topicId="t-001", stem="s",
                            choices=["a", "b", "c", "d"], answerIndex=1, explanation="e")],
    )
    restored = Content.model_validate_json(content.model_dump_json())
    assert restored == content
