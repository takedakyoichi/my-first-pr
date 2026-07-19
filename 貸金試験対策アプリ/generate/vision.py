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
