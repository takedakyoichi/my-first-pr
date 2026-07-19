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
