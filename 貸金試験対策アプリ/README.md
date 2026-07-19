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
   python3 -m venv .venv
   .venv/bin/pip install -r generate/requirements.txt
   ```
2. APIキー設定: `generate/.env.example` をコピーして `generate/.env` を作り、
   `ANTHROPIC_API_KEY` を記入。
3. Kindle画面を撮影した画像を `import/` に置く（.png/.jpg/.jpeg/.webp）。
4. 生成実行:
   ```
   .venv/bin/python -m generate.generate --import-dir import --out app/content.json
   ```
5. `app/content.json` に要点＋問題が追記される（再実行で重複排除して追記）。

## テスト
```
cd 貸金試験対策アプリ
.venv/bin/python -m pytest generate/tests/ -v
```
（API呼び出しは全てモック。テスト実行にAPIキー・撮影画像・課金は不要）
