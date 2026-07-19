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
