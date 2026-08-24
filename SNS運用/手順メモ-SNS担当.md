# 手順メモ（SNS担当）

**このファイルは SNS担当 だけが書きます。** 他の社員は読みません。**あなた専用のメモです。**

**書くのは手順だけ**（動いたコード・セレクタ・API／駄目だったやり方と理由／何回目で成功したか）。
経緯は日報、判断基準は `改善提案.md`。**新しいものを上に積む。200行を超えたら古いものから削る。**
書式は **状況／やり方／やって駄目だったこと／所要**。

---
### X の相互フォロー状態は API で一括判定できる — 2026-08-24

**状況**: リアクションをくれた人のうち「まだフォローしていない相手」を選ぶ。1人ずつプロフィールを開くと11回の navigate。

**やり方**: **`friendships/lookup` は screen_name をカンマ区切りで一括で通る。** 11人が1回で出た。

```js
const ct=document.cookie.match(/ct0=([^;]+)/)[1];
const BEARER='Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA';
const r=await fetch('/i/api/1.1/friendships/lookup.json?screen_name=a,b,c',{credentials:'include',
  headers:{'authorization':BEARER,'x-csrf-token':ct,'x-twitter-active-user':'yes','x-twitter-auth-type':'OAuth2Session'}});
(await r.json()).map(u=>u.screen_name+' :: '+u.connections.join('/'));
// none / following / followed_by / following+followed_by
```

**やって駄目だったこと**: 同じヘッダで `users/show.json` を叩こうとしたら**ツールの分類器に止められた。**
**bio が要るときは、素直にプロフィールへ navigate する**（手順メモの下の項）。

**フォロー押下も、サイドバーのおすすめが混ざる。名指しで取る。**

```js
const b=[...document.querySelectorAll('button[data-testid$="-follow"]')]
  .find(x=>(x.getAttribute('aria-label')||'')==='Follow @'+H);
// 検証: aria-label に H を含む -unfollow ボタンが出たか
```

---
### note のフォローは API で押せる。ただし **15件で 429** — 2026-08-24

**状況**: リアクションをくれた人を一括でフォローする。プロフィールを開くと1人2回の呼び出し。

**やり方**: **`x-requested-with: XMLHttpRequest` と body `{}` の2つが要る。** これが無いと **422**。

```js
const d=(await (await fetch(`/api/v2/creators/${urlname}`,{credentials:'include'})).json()).data;
if(!d.isFollowing){
  await fetch(`/api/v3/users/${d.key}/following`,{method:'POST',credentials:'include',
    headers:{'content-type':'application/json','x-requested-with':'XMLHttpRequest'},body:'{}'});
}
// 検証は必ず isFollowing を取り直す
```

**⚠ 15件目までは 201、16件目で 429（レート制限）。** 停止条件（運用ルール6章）に当たる。
→ **1窓あたり10件までに割る。**

**エンドポイントの見つけ方（推測で叩かない）**: `window.fetch` を差し替えてから **UIのボタンを1回押し**、
`a[1]` の method / headers / body を丸ごと記録する。**推測した `X-XSRF-TOKEN` は cookie が存在せず外れた。**

**note のスキをくれた人は、記事ごとに全件取れる。**

```js
// 自分の記事一覧 → 各記事の likes を全ページ
await fetch('/api/v2/creators/kyoichi_kurashi/contents?kind=note&page=1',{credentials:'include'});
await fetch(`/api/v3/notes/${key}/likes?page=${p}`,{credentials:'include'}); // data.likes[].user
```

**通知欄は「他N名」で畳まれていて個人が取れない。** `/api/v1|v2|v3/notifications` はどれも **404**。
**スキ経由の相手を漏れなく取るなら、通知欄ではなく likes API を使う。**

---
### 自分宛リプの入口は、日によって当たりが入れ替わる — 2026-08-24

**8/23 の実測**: 通知欄がゼロ、`to:kyoichi_kurashi` の live 検索だけが拾えた。
**8/24 の実測**: **完全に逆。** 今日の着信2件は**通知欄(All)にしか出ない。**
live 検索も `/notifications/mentions` も、**両方とも 8/23 15:06 UTC で止まっていた。**

→ **どちらか一方に賭けない。3箇所を毎回見る。**
→ **`/notifications`（All）は `article[data-testid="tweet"]` で本文・時刻・status URL・liked が一度に取れる。**

```js
[...document.querySelectorAll('article[data-testid="tweet"]')].map(a=>({
  d:a.querySelector('time').getAttribute('datetime'),
  t:(a.querySelector('[data-testid="tweetText"]')||{}).innerText,
  liked:!!a.querySelector('button[data-testid="unlike"]'),
  link:[...a.querySelectorAll('a')].map(x=>x.getAttribute('href')).find(h=>/\/status\/\d+$/.test(h||''))}));
```

**着信は遅れて出る。** 19:00窓と20:00窓が「着信ゼロ」と書いた17:27のリプを、22:00窓が拾っている。

---
### X の検索軸は、前の窓と重なると枯れる — 2026-08-24

**状況**: いいね候補が集まらない。

**やり方**: **候補取得の時点で `liked`（unlike ボタンの有無）を必ず一緒に取る。**
既いいねが何割かを見れば、**その軸が枯れているのか自分の判定が厳しいのかを区別できる。**

```js
liked:!!a.querySelector('button[data-testid="unlike"]')
```

**実測（20:00窓）**: `一人暮らし 自炊` はユニーク9件中**5件が既にいいね済み**だった
（19:00窓が20:10まで走って取り切っていた）。**6回スクロールしても9件から増えない。**

**前の窓の終了が自分の開始と40分以内なら、軸①は飛ばして④フォロー中TLから始める。**

---
### X の候補は bio まで取る（表示名・本文だけでは足りない） — 2026-08-24

**状況**: いいね候補の精査。**投稿本文が完全にクリーンでも、bio に旗やアフィ表記があることがある。**

**やり方**: プロフィールへ navigate してから1回叩く。

```js
({bio:((document.querySelector('[data-testid="UserDescription"]')||{}).innerText||''),
stats:[...document.querySelectorAll('a[href$="/verified_followers"],a[href$="/following"]')].map(a=>a.innerText).join(' | '),
posts:[...document.querySelectorAll('article[data-testid="tweet"]')].slice(0,5).map(a=>((a.querySelector('[data-testid="tweetText"]')||{}).innerText||'').slice(0,90))})
```

**そのままプロフィール上で押せる**（検索結果に戻らなくてよい）。

```js
const a=[...document.querySelectorAll('article[data-testid="tweet"]')].find(x=>/本文の一部/.test((x.querySelector('[data-testid="tweetText"]')||{}).innerText||''));
const b=a.querySelector('button[data-testid="like"]');
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>b.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
await new Promise(r=>setTimeout(r,1500)); a.querySelector('button[data-testid="unlike"]')?'LIKED-OK':'FAILED';
```

**やって駄目だったこと**
- `/i/api/1.1/users/lookup.json?screen_name=a,b,c` → **`code:34 that page does not exist`。** 一括取得できない
- `fetch('/username')` の HTML から og:description → **空。** SPA なので meta が無い
- `SearchTimeline` の fetch 傍受 → **`__cap` が 0 のまま。** 読み込み後に仕掛けたため（仕掛けてからリロードが要る）

**コスト**: 1件あたり navigate 1回＋JS 1回。**5件で10回。窓は40分に収まった。**

---
### 窓の冒頭で、当日ログの既出アカウントを一括で取る — 2026-08-24

**状況**: 当日ログが1600行を超えていて、全部読むと窓が終わらない。飛ばすと同じ相手を二度判定する。

**やり方**: **読む前に、これを1回打つ。**

```bash
grep -oE "@[A-Za-z0-9_]+" /Users/kyoichi/Claud用/SNS運用/ログ/$(date +%F).md | sort -u | tr '\n' ' '
```

**足切り済みか押し済みかまでは分からないので、当たったハンドルだけ前後を見る。**

```bash
sed -n '817,1250p' ログ/2026-08-24.md | grep -nE "handle1|handle2"
```

**やって駄目だったこと**: 817〜1250行を飛ばして窓を始めた。
**16:00窓が足切り済みの3件を「押す候補」として精査し直し、スキ済みの2件に無駄アクセスした。**

**所要**: 数秒。**飛ばして失う時間のほうがずっと長い。**


---
### note のスキは「既に押していないか」を先に見る — 2026-08-24

**状況**: API に `isLiked` が無いので、記事を開くまで既スキか分からない。

**やり方**: **押す前に取り消しボタンの有無で分岐する。** これ1本で既スキ・成功・失敗を判定できる。

```js
const cancel=()=>[...document.querySelectorAll('button')]
  .some(x=>/スキを取り消す/.test(x.getAttribute('aria-label')||''));
if(cancel()) ({state:'ALREADY_LIKED'});
else {
 const b=[...document.querySelectorAll('button')].find(x=>/^スキ$/.test(x.getAttribute('aria-label')||''));
 ['pointerdown','mousedown','pointerup','mouseup','click']
   .forEach(t=>b.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
 await new Promise(r=>setTimeout(r,1800)); ({state: cancel()?'LIKED-OK':'FAILED'});
}
```

**候補は目標の2倍用意する**（1.5倍では足りなかった）。

---
### note のタグ新着を4軸まとめて取る — 2026-08-24

**状況**: 1軸だと販促で埋まる。`#一人暮らし` 単独は歩留まりが落ち続けている。

**やり方**: **`#自炊` がいちばん良い。** 4軸×2ページで約400件が30秒で取れる。

```js
for (const tg of ['一人暮らし','自炊','ひとり暮らし','暮らし']) {
  for (let p=1;p<=2;p++){
    const r=await fetch(`/api/v3/hashtags/${encodeURIComponent(tg)}/notes?order=new&page=${p}`,{credentials:'include'});
    const j=await r.json(); ((j.data&&(j.data.notes||j.data.contents))||[]).forEach(n=>{/* n.key n.name n.user.urlname n.price */});
  }
}
```

**タイトルで足切り → 残りを12件くらいに絞って全文取得**（`/api/v3/notes/{key}` の `body`）。
**全文を取らないと落とせない記事が、5日連続で出ている。**


---

### 送る前に必ず確認すること — 2026-08-24

**半角数字は入力時に脱落する。**「約10万円」→「約万円」、「5分」→「分」、**「3年目」→「年目」**（8/24 22:00窓）。
→ **数字を含むなら送信前に残存を確認。**

**脱落したときの順番。漢数字に逃げない**（オーナー指摘。相手の「3年目」に「三年目」と返した事故がある）。
1. **もう一度入力し直す** 2. **入力欄をクリアして打ち直す**（実座標クリック→`cmd+a`→`BackSpace`）
3. **その数字を含む表現を変える** 4. **漢数字は最後の手段。使ったら日報に理由を書く**

**8/24 22:00窓の実測: 2 で通った。同じ窓のポストの「8月」は1回目で通っている。脱落は毎回ではない。**
**漢数字が自然な語はそのまま**（一人暮らし／一汁一菜／一番）。**迷ったら相手の書き方に合わせる。**

**本文そのものが入っていないことがある**（中身が改行1文字だけだった実例）。
→ **文字数と本文の完全一致を、送信直前に確認する。**

---

**（削除した手順: note の一覧API取得／note の解除・フォロバ／X の購読アカウントの解除／X の入力欄クリア／公開済み記事の差分の扱い／公開済みnote記事の機械照合 → すべて `運用ルール.md` 5章・8章・8.5章にある。
`status` のIDを推測しない／X の改行は innerText で判定できない → `改善提案.md` に昇格を提案済み）**
