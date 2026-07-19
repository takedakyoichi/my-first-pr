# デプロイ手順（Cloudflare Pages + KV + Access）

画像・学習進捗は教材由来／個人データ。**必ず Cloudflare Access 保護のプライベート配信**にすること
（無認証の公開URLで配信しない）。**このアプリの運用は無料枠内で完結し課金は発生しない**
（AI/APIは不使用、Cloudflareは個人1人分で無料枠に収まる）。

## 前提
- Cloudflare アカウント（無料）
- GitHub の**プライベート**リポジトリにこのコードを push 済み

## リポジトリ構成の要点
このコードはリポジトリ直下の `貸金試験対策アプリ/` にあり、その中に
`app/`（静的サイト）と `functions/`（Pages Functions）がある。
Cloudflare Pages の設定では **Root directory を `貸金試験対策アプリ` に**し、
**Build output directory を `app`** にする。これで Pages は
`貸金試験対策アプリ/functions/` を API として自動認識し、`app/` を配信する。

## 1. GitHub（プライベート）に push
```
# GitHub でプライベートリポジトリを作成してから
git remote add origin git@github.com:<あなた>/kashikin-app.git
git push -u origin feature/kashikin-exam-app
```
- 実画像は `.gitignore` で除外している。配信に必要な実画像は、**プライベートリポジトリに限り**
  `app/pages/` の除外を外して含める（`.gitignore` の `app/pages/*` 行を消す）。
  **公開リポジトリには絶対に画像を置かない。**

## 2. Cloudflare Pages プロジェクト作成
1. Cloudflare ダッシュボード → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**。
2. 作成したプライベートリポジトリを選択。
3. ビルド設定:
   - Framework preset: **None**
   - Build command: （空のまま）
   - **Root directory: `貸金試験対策アプリ`**
   - **Build output directory: `app`**
4. **Save and Deploy**。初回デプロイが走る。

## 3. KV 名前空間を作成してバインド
1. **Workers & Pages → KV → Create namespace**（例: `kashikin-state`）。
2. Pages プロジェクト → **Settings → Functions → KV namespace bindings → Add binding**:
   - **Variable name: `STATE_KV`**（コードが参照する名前。厳密に一致させる）
   - Namespace: 上で作った `kashikin-state`
3. **Retry deployment**（再デプロイ）して反映。

> これで `/api/state` が KV に読み書きするようになる。バインド名が `STATE_KV` でないと
> 関数が動かない（`functions/api/state.js` が `context.env.STATE_KV` を参照）。

## 4. Cloudflare Access（本人限定）
1. **Zero Trust → Access → Applications → Add an application → Self-hosted**。
2. Application domain: アプリのドメイン（`<プロジェクト名>.pages.dev`）。
3. ポリシー: Action **Allow**、Include 条件 **Emails = 自分のメールアドレス**。
4. 保存。以降このサイトはメールのワンタイムコード認証を通った本人だけがアクセス可能になり、
   関数は `Cf-Access-Authenticated-User-Email` ヘッダで本人を識別して KV をメール単位で分離する。

> Zero Trust の有効化時にカード情報の登録を求められることがあるが、50ユーザーまで $0 で課金されない。
> カード登録を避けたい場合は、Access の代わりに関数側で合言葉チェックする簡易認証に変更もできる
> （その場合は別途実装が必要）。

## 5. スマホで使う
1. 認証後 `https://<プロジェクト名>.pages.dev` を開く。
2. ブラウザメニュー →「ホーム画面に追加」で PWA としてインストール。
3. PC で進めた進捗が起動時同期で反映され、以降 PC⇄スマホで自動同期される
   （閲覧・既読・要復習・メモは 800ms デバウンスでサーバへ送信、起動時にサーバから取得してマージ）。

## 更新フロー（教材ページを足す）
1. `app/pages/` にスクショを追加 → `python3 build_manifest.py` → `app/manifest.json` 更新。
2. 章名・区切りを編集（任意）。
3. `git add`（パス指定）して push → Pages が自動で再デプロイ。

## ローカルでの事前確認（任意）
デプロイ前に同期挙動を手元で確認したい場合、依存ゼロのモックサーバがある:
```
cd 貸金試験対策アプリ
python3 tools/make_samples.py   # サンプル画像（本番では実画像を置く）
python3 build_manifest.py
node tools/mock_sync_server.mjs # http://localhost:8123 で /api/state をエミュレート
```
