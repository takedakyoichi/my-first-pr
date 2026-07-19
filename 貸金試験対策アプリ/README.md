# 貸金試験対策アプリ

貸金業務取扱主任者 試験対策の**画像教材リーダー**。手持ちのKindle教材の
スクリーンショットをそのまま読み、既読/要復習/SRS復習/メモ/学習記録で
反復学習する。**AI・API・OCRを一切使わない＝完全無料・オフライン動作**。

設計: `docs/superpowers/specs/2026-07-19-貸金試験対策アプリ-design.md`

## 構成
- `build_manifest.py` … `app/pages/` の画像から目次 `app/manifest.json` を生成（標準ライブラリのみ）
- `app/`      … 静的PWA本体（画像リーダー＋学習補助）
- `app/pages/`… スクショ画像の置き場（実データはコミットしない。サンプルのみ同梱）
- `tools/`    … dev用（サンプル画像生成）
- `functions/`… Cloudflare同期API（Plan B で実装）

## 使い方（ローカル）
1. Kindle画面のスクショを `app/pages/` に置く（.png/.jpg/.jpeg/.webp、ファイル名＝読む順）。
2. 目次を生成:
   ```
   cd 貸金試験対策アプリ
   python3 build_manifest.py
   ```
   → `app/manifest.json` が生成される（初回は全ページ1章「未分類」）。
3. `app/manifest.json` を開き、章の区切り・章名を編集（任意。未編集でも動く）。
4. ローカル配信して開く（`fetch(manifest.json)` のため file:// 不可・HTTP必須）:
   ```
   cd 貸金試験対策アプリ/app
   python3 -m http.server 8123
   ```
   ブラウザで `http://localhost:8123/` を開く。スマホからも同じWi-Fiの
   `http://<PCのIP>:8123/` でアクセス可（本格的なPC⇄スマホ同期は Plan B）。

## 動作確認用サンプル
実画像が無い状態で試すには:
```
cd 貸金試験対策アプリ
python3 tools/make_samples.py   # app/pages/ にサンプル画像を生成
python3 build_manifest.py
```

## テスト
```
cd 貸金試験対策アプリ
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/ -v          # build_manifest のテスト
node --test app/js/tests/*.test.js            # 学習ロジック(SRS/進捗/永続化)のテスト
```
（テスト実行にAPIキー・課金・ネットワークは不要）
