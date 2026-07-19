from generate.schema import Content, PageExtraction, RawTopic, RawQuestion
from generate.merge import merge_pages


def _page(title="定義", stem="貸金業を営むには？"):
    return PageExtraction(topics=[RawTopic(
        field="law", chapter="総則", title=title, body="本文",
        questions=[RawQuestion(stem=stem, choices=["登録", "許可", "免許", "認可"],
                               answerIndex=0, explanation="登録が必要")],
    )])


def _empty():
    return Content(version=1, generatedAt="", topics=[], questions=[])


def test_merge_into_empty_assigns_ids_and_links():
    result = merge_pages(_empty(), [_page()])

    assert len(result.topics) == 1
    assert len(result.questions) == 1
    topic = result.topics[0]
    question = result.questions[0]
    assert topic.id == "t-001"
    assert question.id == "q-001"
    assert question.topicId == "t-001"
    assert topic.relatedQuestionIds == ["q-001"]
    assert result.generatedAt != ""


def test_duplicate_question_is_skipped():
    # 同じ stem を空白違いで2回 → 1問だけ残る
    result = merge_pages(_empty(), [
        _page(stem="貸金業を営むには？"),
        _page(stem="貸金業を営むには ？ "),
    ])
    assert len(result.questions) == 1
    assert len(result.topics) == 1  # 同一トピックにまとまる


def test_new_topic_gets_next_id():
    first = merge_pages(_empty(), [_page(title="定義", stem="q1")])
    second = merge_pages(first, [_page(title="登録", stem="q2")])
    assert [t.id for t in second.topics] == ["t-001", "t-002"]
    assert [q.id for q in second.questions] == ["q-001", "q-002"]
    assert second.topics[1].relatedQuestionIds == ["q-002"]
