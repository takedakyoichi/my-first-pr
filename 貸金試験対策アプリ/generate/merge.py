from __future__ import annotations

import re
from datetime import datetime, timezone

from .schema import Content, PageExtraction, Question, Topic


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _next_num(prefix: str, items) -> int:
    nums = [int(i.id.split("-")[1]) for i in items if i.id.startswith(prefix + "-")]
    return max(nums, default=0) + 1


def merge_pages(existing: Content, pages: list[PageExtraction]) -> Content:
    """既存 content に新しい抽出ページ群をマージして新しい Content を返す。"""
    topics = list(existing.topics)
    questions = list(existing.questions)

    topic_by_key = {(t.field, t.chapter, t.title): t for t in topics}
    seen_stems = {_normalize(q.stem) for q in questions}
    tnum = _next_num("t", topics)
    qnum = _next_num("q", questions)

    for page in pages:
        for rt in page.topics:
            key = (rt.field, rt.chapter, rt.title)
            topic = topic_by_key.get(key)
            if topic is None:
                topic = Topic(id=f"t-{tnum:03d}", field=rt.field, chapter=rt.chapter,
                              title=rt.title, body=rt.body, relatedQuestionIds=[])
                tnum += 1
                topics.append(topic)
                topic_by_key[key] = topic
            for rq in rt.questions:
                norm = _normalize(rq.stem)
                if norm in seen_stems:
                    continue
                seen_stems.add(norm)
                question = Question(id=f"q-{qnum:03d}", field=rt.field, topicId=topic.id,
                                    stem=rq.stem, choices=list(rq.choices),
                                    answerIndex=rq.answerIndex, explanation=rq.explanation)
                qnum += 1
                questions.append(question)
                topic.relatedQuestionIds.append(question.id)

    return Content(
        version=1,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        topics=topics,
        questions=questions,
    )
