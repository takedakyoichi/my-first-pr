# 貸金試験対策アプリ — Plan 1: 生成パイプライン Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** スマホで撮影したKindle教材の画像を Claude Vision で読み取り、要点テキストと4択問題を抽出して `app/content.json` に蓄積するローカルバッチCLIを作る。

**Architecture:** `generate/` 配下の小さなPythonモジュール群。`schema.py`（Pydanticデータ契約）→ `vision.py`（画像1枚→抽出、AI境界）→ `merge.py`（ID採番・重複排除・トピック↔問題リンクの純粋関数）→ `generate.py`（import/走査→抽出→マージ→書き出しのCLI）。AIを呼ぶのは`vision.py`のみで、他は決定的でユニットテスト可能。APIキーは`generate/.env`（gitignore）のみに置く。

**Tech Stack:** Python 3.11+, `anthropic` SDK（`client.messages.parse` + `output_format`）, Pydantic v2, `python-dotenv`, pytest。

## Global Constraints

- モデルIDは正確に `claude-opus-4-8` を使う（他モデルへ勝手に変更しない）。
- Vision呼び出しは `client.messages.parse(..., output_format=PageExtraction)` を使い、`response.parsed_output` を受け取る（生JSONの手パースはしない）。
- thinkは `thinking={"type": "adaptive"}`（`budget_tokens` は使わない＝Opus 4.8では400）。
- 出力分野は必ず4値のいずれか: `law` | `civil` | `protection` | `finance`（①法令 ②民法等 ③保護 ④財務会計）。
- `content.json` は `app/content.json` に UTF-8・`ensure_ascii=False`・indent=2 で書き出す。
- APIキーは `generate/.env` のみ。`.env` と `import/` は必ず gitignore。
- コミットはこのワークスペースの他アプリ（埋め込みgitリポジトリ）を巻き込まないよう、**必ずパス指定で `git add`**。`git add -A` / `git add .` は禁止。
- データ契約（`content.json` の形）は仕様書 §8 を正とする。Plan 2/3 がこのJSONを消費する。

---

## File Structure

- `貸金試験対策アプリ/generate/__init__.py` — パッケージ化（空）
- `貸金試験対策アプリ/generate/schema.py` — Pydanticモデル（Raw* = Vision出力、Topic/Question/Content = 保存形）
- `貸金試験対策アプリ/generate/vision.py` — `extract_from_image()`。AI境界
- `貸金試験対策アプリ/generate/merge.py` — `merge_pages()`。ID採番・重複排除・リンク（純粋関数）
- `貸金試験対策アプリ/generate/generate.py` — CLI。`run()` + `main()`
- `貸金試験対策アプリ/generate/requirements.txt`
- `貸金試験対策アプリ/generate/.env.example`
- `貸金試験対策アプリ/.gitignore`
- `貸金試験対策アプリ/generate/tests/__init__.py`
- `貸金試験対策アプリ/generate/tests/test_schema.py`
- `貸金試験対策アプリ/generate/tests/test_vision.py`
- `貸金試験対策アプリ/generate/tests/test_merge.py`
- `貸金試験対策アプリ/generate/tests/test_generate.py`
- `貸金試験対策アプリ/README.md`

すべての `pytest` はリポジトリの `貸金試験対策アプリ/` 直下で実行する（`cd 貸金試験対策アプリ && python -m pytest`）。

---

### Task 1: スキャフォールド + データ契約（schema.py）

**Files:**
- Create: `貸金試験対策アプリ/generate/__init__.py`
- Create: `貸金試験対策アプリ/generate/tests/__init__.py`
- Create: `貸金試験対策アプリ/generate/schema.py`
- Create: `貸金試験対策アプリ/generate/tests/test_schema.py`
- Create: `貸金試験対策アプリ/generate/requirements.txt`
- Create: `貸金試験対策アプリ/generate/.env.example`
- Create: `貸金試験対策アプリ/.gitignore`

**Interfaces:**
- Produces（後続タスクが依存）:
  - `RawQuestion(stem: str, choices: list[str](len 4), answerIndex: int 0-3, explanation: str)`
  - `RawTopic(field: Fieldname, chapter: str, title: str, body: str, questions: list[RawQuestion])`
  - `PageExtraction(topics: list[RawTopic])`
  - `Question(id: str, field: Fieldname, topicId: str, stem: str, choices: list[str], answerIndex: int, explanation: str)`
  - `Topic(id: str, field: Fieldname, chapter: str, title: str, body: str, relatedQuestionIds: list[str])`
  - `Content(version: int, generatedAt: str, topics: list[Topic], questions: list[Question])`
  - `Fieldname = Literal["law", "civil", "protection", "finance"]`

- [ ] **Step 1: requirements.txt / .env.example / .gitignore を作成**

`貸金試験対策アプリ/generate/requirements.txt`:
```
anthropic>=0.40
python-dotenv>=1.0
pytest>=8.0
```

`貸金試験対策アプリ/generate/.env.example`:
```
# コピーして generate/.env を作り、実際のキーを入れる（.env はコミットしない）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

`貸金試験対策アプリ/.gitignore`:
```
generate/.env
import/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: 失敗するテストを書く** — `貸金試験対策アプリ/generate/tests/test_schema.py`

```python
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
```

- [ ] **Step 3: 失敗を確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_schema.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'generate.schema'`）

- [ ] **Step 4: 実装** — `貸金試験対策アプリ/generate/__init__.py`（空ファイル）、`貸金試験対策アプリ/generate/tests/__init__.py`（空ファイル）、`貸金試験対策アプリ/generate/schema.py`:

```python
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
```

- [ ] **Step 5: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_schema.py -v`
Expected: PASS（5件）

- [ ] **Step 6: コミット**

```bash
git add 貸金試験対策アプリ/generate/__init__.py 貸金試験対策アプリ/generate/tests/__init__.py \
        貸金試験対策アプリ/generate/schema.py 貸金試験対策アプリ/generate/tests/test_schema.py \
        貸金試験対策アプリ/generate/requirements.txt 貸金試験対策アプリ/generate/.env.example \
        貸金試験対策アプリ/.gitignore
git commit -m "feat(kashikin/generate): データ契約(Pydanticスキーマ)とスキャフォールド"
```

---

### Task 2: Vision抽出（vision.py）

**Files:**
- Create: `貸金試験対策アプリ/generate/vision.py`
- Create: `貸金試験対策アプリ/generate/tests/test_vision.py`

**Interfaces:**
- Consumes: `PageExtraction`, `RawTopic`, `RawQuestion`（Task 1）
- Produces:
  - `MODEL = "claude-opus-4-8"`
  - `extract_from_image(client, image_bytes: bytes, media_type: str = "image/png") -> PageExtraction`
    - `client` は `anthropic.Anthropic` 互換（テストでは MagicMock）

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/generate/tests/test_vision.py`

```python
from unittest.mock import MagicMock

from generate import vision
from generate.schema import PageExtraction, RawTopic, RawQuestion


def _fake_extraction():
    return PageExtraction(topics=[RawTopic(
        field="law", chapter="総則", title="貸金業の定義", body="要点本文",
        questions=[RawQuestion(stem="s", choices=["a", "b", "c", "d"],
                               answerIndex=0, explanation="e")],
    )])


def test_extract_returns_parsed_output():
    fake = _fake_extraction()
    client = MagicMock()
    client.messages.parse.return_value = MagicMock(parsed_output=fake)

    result = vision.extract_from_image(client, b"\x89PNGdata", "image/png")

    assert result == fake


def test_extract_sends_image_and_schema():
    client = MagicMock()
    client.messages.parse.return_value = MagicMock(parsed_output=_fake_extraction())

    vision.extract_from_image(client, b"\x89PNGdata", "image/jpeg")

    kwargs = client.messages.parse.call_args.kwargs
    assert kwargs["model"] == "claude-opus-4-8"
    assert kwargs["output_format"] is PageExtraction
    content = kwargs["messages"][0]["content"]
    assert content[0]["type"] == "image"
    assert content[0]["source"]["type"] == "base64"
    assert content[0]["source"]["media_type"] == "image/jpeg"
    assert content[1]["type"] == "text"
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_vision.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'generate.vision'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/generate/vision.py`

```python
from __future__ import annotations

import base64

from .schema import PageExtraction

MODEL = "claude-opus-4-8"

INSTRUCTION = """あなたは「貸金業務取扱主任者」試験の教材編集者です。
添付画像は市販テキストの1ページです。画像から日本語の本文を読み取り
（画面の映り込み・傾き・改行の乱れは文脈で補正）、次を行ってください。

1. 内容を意味のまとまり（要点）に分け、それぞれに chapter（章・節）と
   title（要点の見出し）を付ける。
2. 各要点の body に、試験に出る定義・数字・要件・条文キーワードを
   簡潔にまとめる（原文の丸写しではなく要点化）。
3. 各要点について、本試験と同じ形式の4択問題を1〜3問作る。
   choices はちょうど4つ、answerIndex は正解の位置(0〜3)、
   explanation になぜ正解かを1〜2文で書く。
4. 各要点の field を必ず次のいずれかに分類する:
   - law        : 貸金業法および関係法令
   - civil      : 貸付け・取引に関する法令（民法等）
   - protection : 資金需要者等の保護
   - finance    : 財務および会計

画像に試験内容が写っていない場合は topics を空配列にしてください。"""


def extract_from_image(client, image_bytes: bytes, media_type: str = "image/png") -> PageExtraction:
    """画像1枚を Claude Vision に渡し、要点＋問題の構造化データを返す。"""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {"type": "text", "text": INSTRUCTION},
            ],
        }],
        output_format=PageExtraction,
    )
    return response.parsed_output
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_vision.py -v`
Expected: PASS（2件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/generate/vision.py 貸金試験対策アプリ/generate/tests/test_vision.py
git commit -m "feat(kashikin/generate): Claude Visionで画像→要点＋4択問題を抽出"
```

---

### Task 3: マージ・ID採番・重複排除（merge.py）

**Files:**
- Create: `貸金試験対策アプリ/generate/merge.py`
- Create: `貸金試験対策アプリ/generate/tests/test_merge.py`

**Interfaces:**
- Consumes: `Content`, `Topic`, `Question`, `PageExtraction`, `RawTopic`, `RawQuestion`（Task 1）
- Produces:
  - `merge_pages(existing: Content, pages: list[PageExtraction]) -> Content`
    - トピックは `(field, chapter, title)` が同一なら既存に問題を追記、なければ新規 `t-NNN`
    - 問題は stem を空白除去・小文字化した正規化キーで重複排除、新規は `q-NNN`
    - 追加した問題IDは対応トピックの `relatedQuestionIds` に追記
    - ID採番は既存の最大番号+1から連番。`generatedAt` は現在UTC(ISO8601)

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/generate/tests/test_merge.py`

```python
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
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_merge.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'generate.merge'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/generate/merge.py`

```python
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
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_merge.py -v`
Expected: PASS（3件）

- [ ] **Step 5: コミット**

```bash
git add 貸金試験対策アプリ/generate/merge.py 貸金試験対策アプリ/generate/tests/test_merge.py
git commit -m "feat(kashikin/generate): ID採番・重複排除・トピックリンクのマージ処理"
```

---

### Task 4: CLIオーケストレーション（generate.py）+ README

**Files:**
- Create: `貸金試験対策アプリ/generate/generate.py`
- Create: `貸金試験対策アプリ/generate/tests/test_generate.py`
- Create: `貸金試験対策アプリ/README.md`

**Interfaces:**
- Consumes: `Content`, `PageExtraction`（Task 1）, `merge_pages`（Task 3）, `extract_from_image`（Task 2）
- Produces:
  - `load_content(path: Path) -> Content`（無ければ空Content）
  - `run(import_dir: Path, content_path: Path, extractor=extract_from_image, client=None) -> Content`
    - `import_dir` 内の画像（.png/.jpg/.jpeg/.webp、名前順）を各1回 `extractor(client, bytes, media_type)` に渡す
    - マージ結果を `content_path` に UTF-8/`ensure_ascii=False`/indent=2 で書き出す
  - `main()`（CLIエントリ。`--import-dir`（既定 `import`）, `--out`（既定 `app/content.json`）。`load_dotenv()` を呼ぶ）

- [ ] **Step 1: 失敗するテストを書く** — `貸金試験対策アプリ/generate/tests/test_generate.py`

```python
import json
from pathlib import Path

from generate.generate import run, load_content
from generate.schema import Content, PageExtraction, RawTopic, RawQuestion


def _stub_extractor(client, image_bytes, media_type):
    # 呼ばれるたびに1トピック1問を返す（stem を bytes で変えて重複回避）
    tag = image_bytes.decode("utf-8")
    return PageExtraction(topics=[RawTopic(
        field="law", chapter="総則", title=f"要点{tag}", body="本文",
        questions=[RawQuestion(stem=f"問題{tag}", choices=["a", "b", "c", "d"],
                               answerIndex=0, explanation="e")],
    )])


def test_load_content_missing_returns_empty(tmp_path):
    content = load_content(tmp_path / "none.json")
    assert content.topics == []
    assert content.questions == []


def test_run_writes_content_for_each_image(tmp_path):
    import_dir = tmp_path / "import"
    import_dir.mkdir()
    (import_dir / "01.png").write_bytes(b"1")
    (import_dir / "02.png").write_bytes(b"2")
    out = tmp_path / "content.json"

    result = run(import_dir, out, extractor=_stub_extractor, client=object())

    assert len(result.questions) == 2
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["topics"]) == 2
    assert len(data["questions"]) == 2
    # 日本語がエスケープされずに書けている
    assert "要点" in out.read_text(encoding="utf-8")


def test_run_merges_into_existing(tmp_path):
    import_dir = tmp_path / "import"
    import_dir.mkdir()
    (import_dir / "01.png").write_bytes(b"1")
    out = tmp_path / "content.json"

    run(import_dir, out, extractor=_stub_extractor, client=object())
    # 別画像を足して再実行 → 追記される
    (import_dir / "02.png").write_bytes(b"2")
    result = run(import_dir, out, extractor=_stub_extractor, client=object())

    # 01.png は同じ内容なので重複排除され、02.png の1問だけ増える
    assert len(result.questions) == 2
```

- [ ] **Step 2: 失敗を確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/test_generate.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'generate.generate'`）

- [ ] **Step 3: 実装** — `貸金試験対策アプリ/generate/generate.py`

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from .merge import merge_pages
from .schema import Content
from .vision import extract_from_image

IMAGE_EXTS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def load_content(path: Path) -> Content:
    if path.exists():
        return Content.model_validate_json(path.read_text(encoding="utf-8"))
    return Content(version=1, generatedAt="", topics=[], questions=[])


def run(import_dir: Path, content_path: Path, extractor=extract_from_image, client=None) -> Content:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()

    images = sorted(
        p for p in import_dir.iterdir()
        if p.suffix.lower() in IMAGE_EXTS
    )
    pages = []
    for img in images:
        media_type = IMAGE_EXTS[img.suffix.lower()]
        pages.append(extractor(client, img.read_bytes(), media_type))
        print(f"processed {img.name}")

    content = merge_pages(load_content(content_path), pages)
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(
        json.dumps(content.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return content


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Kindle撮影画像→content.json 生成バッチ")
    parser.add_argument("--import-dir", default="import")
    parser.add_argument("--out", default="app/content.json")
    args = parser.parse_args()

    content = run(Path(args.import_dir), Path(args.out))
    print(f"done: topics={len(content.topics)} questions={len(content.questions)} -> {args.out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd 貸金試験対策アプリ && python -m pytest generate/tests/ -v`
Expected: PASS（全タスク合計12件）

- [ ] **Step 5: README を作成** — `貸金試験対策アプリ/README.md`

```markdown
# 貸金試験対策アプリ

貸金業務取扱主任者 試験対策アプリ。撮影したKindle教材を Claude Vision で
要点＋4択問題に変換し、静的PWAで反復学習する。

## 構成
- `generate/` … PC上の生成バッチ（撮影時だけ動く。APIキーはここの .env のみ）
- `import/`   … 撮影画像の置き場（gitignore）
- `app/`      … 静的PWA（Plan 2 で実装）
- `functions/`… Cloudflare同期API（Plan 3 で実装）

設計: `docs/superpowers/specs/2026-07-19-貸金試験対策アプリ-design.md`

## 生成バッチの使い方
1. 依存インストール:
   ```
   cd 貸金試験対策アプリ
   pip install -r generate/requirements.txt
   ```
2. APIキー設定: `generate/.env.example` をコピーして `generate/.env` を作り、
   `ANTHROPIC_API_KEY` を記入。
3. Kindle画面を撮影した画像を `import/` に置く（.png/.jpg/.jpeg/.webp）。
4. 生成実行:
   ```
   python -m generate.generate --import-dir import --out app/content.json
   ```
5. `app/content.json` に要点＋問題が追記される（再実行で重複排除して追記）。

## テスト
```
cd 貸金試験対策アプリ
python -m pytest generate/tests/ -v
```
```

- [ ] **Step 6: コミット**

```bash
git add 貸金試験対策アプリ/generate/generate.py 貸金試験対策アプリ/generate/tests/test_generate.py \
        貸金試験対策アプリ/README.md
git commit -m "feat(kashikin/generate): CLIオーケストレーションとREADME"
```

---

## Self-Review

**1. Spec coverage（Plan 1 の範囲 = 仕様書 §3〜§4, §7 生成側, §8）:**
- §4 取り込みパイプライン（OCR＋要点抽出＋問題生成＋分野分類）→ Task 2 の `vision.py`（INSTRUCTION で4項目指示）。✓
- §4 既存 content.json にマージ（重複検出・追記）→ Task 3 `merge_pages`。✓
- §8 データモデル（topics/questions の各フィールド）→ Task 1 `schema.py` が §8 と一致。✓
- §7 生成側スタック（Python + anthropic SDK、.env にキー）→ Task 1/2/4。✓
- Plan 2（app/）・Plan 3（functions/）は本プラン対象外（別プランで実装）。✓

**2. Placeholder scan:** TODO/TBD/「適切に処理」等なし。全コードブロックは実物。✓

**3. Type consistency:**
- `PageExtraction.topics: list[RawTopic]` を vision が返し、merge が消費 — 一致。✓
- `extract_from_image(client, image_bytes, media_type)` の引数順を Task 2 定義・Task 4 呼び出し（`extractor(client, img.read_bytes(), media_type)`）・テストのstubで統一。✓
- ID書式 `t-NNN` / `q-NNN`（`_next_num` は `prefix + "-"` で分割）— merge実装とテスト期待値（`t-001`等）が一致。✓
- `Content(version, generatedAt, topics, questions)` を load/merge/run 全てで同一フィールド名で使用。✓

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-19-kashikin-plan1-generation.md`.**

これは全3プランのうち **Plan 1（生成パイプライン）** です。完了後に Plan 2（静的PWA学習アプリ）、Plan 3（Cloudflare同期＋デプロイ）を同じ流れで作成・実装します。
