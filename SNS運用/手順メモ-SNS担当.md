# 手順メモ（SNS担当）

## 2026-08-25 23:00窓

### ⚠ 時刻は「10ツール呼び出しごと」に `date` を取る（3回目の再発）

**23:16 に、現在時刻を「23:43」だと思い込んでいた。27分のズレ。**
**「作業の切り替え時に取る」では足りない。ツール呼び出しの体感は当てにならない。**
→ **`date "+%H:%M:%S"` を、10呼び出しごとに機械的に。** 19:00窓・21:00窓に続き3件目。

### note のフォロバ走査（動く。283名を約20秒）

```js
// note.com の自分のプロフィールページ上で実行する（他ドメインでは credentials が乗らない）
const miss=[];let total=0;
for(let p=1;p<40;p++){
 const r=await fetch(`/api/v2/creators/kyoichi_kurashi/followers?page=${p}`,{credentials:'include'});
 const d=(await r.json()).data||{};
 (d.follows||[]).forEach(u=>{total++; if(u.isFollowed && !u.isFollowing) miss.push(u.urlname);});
 if(d.isLastPage)break;
}
({total,miss})
```

### ⚠ note のフォローボタンは「フォローバック」と出ることがある

**相手が既にこちらをフォローしている場合、ボタンの文言は「フォロー」ではなく「フォローバック」。**
`/^フォロー$/` の**完全一致では拾えない**。→ `/^フォロー(バック)?$/` で探すこと。
押した後の確認は `(await (await fetch('/api/v2/creators/{urlname}',{credentials:'include'})).json()).data.isFollowing`。

### ⛔ note の通知欄は URL からは開けない（未解決）

`note.com/notifications` → **ユーザー「☆6」のページ**／`note.com/notice` → **ユーザー「ササケン」のページ**。
API は `/api/v1|v2|v3/notifications` と `/api/v3/notifications/list` の**4本とも 404**。
トップページの DOM からも通知リンクが取れない（セレクタ0件）。
→ **次はベルのアイコンを `computer` のスクリーンショットで目視してクリックする。**

### note のタグ新着はAPIで一気に取れる（4タグ48件を1呼び出し）

```js
const tags=['自炊記録','晩ごはん','台所','食費'];const out=[];
for(const t of tags){
 const r=await fetch(`/api/v3/hashtags/${encodeURIComponent(t)}/notes?order=new&page=1`,{credentials:'include'});
 const j=await r.json();
 ((j.data&&(j.data.notes||j.data.contents))||[]).slice(0,12).forEach(n=>out.push({key:n.key,title:n.name,urlname:n.user&&n.user.urlname,liked:n.isLiked,price:n.price}));
}
```
全文スキャンは `/api/v3/notes/{key}` の `data.body`（HTMLタグを剥がしてから NEG/PROMO に通す）。

### note のスキ押下（`ALREADY_LIKED` の判定込み）

`button` を全部見て `aria-label`/`title` に **`スキを取り消す`** があれば既スキ、**`スキ`** だけなら未スキ。
押した後、`スキを取り消す` が現れれば成功。**21:00窓の「描画されず押せない」は誤判定だった実績があるので、必ずこの確認を通す。**

### X のリプ送信ボタンは、本文が折り返すと y 座標が下にずれる

**1回目の Reply クリックが空振りした**（本文2行→3行で、ボタンが 547→608 に移動）。
→ **タイプした後にスクリーンショットを撮り直して、そのときの座標を押す。** 打つ前の座標を使い回さない。

### X の候補取得は `article` から直接読む（`users/lookup.json` は 404）

`/i/api/1.1/users/lookup.json` は **code 34 で死んでいる**。bio確認はプロフィールを1件ずつ開くしかない。
検索結果からは `div[role="link"]`（引用先）も一緒に取っておくこと。


**このファイルは SNS担当 だけが書きます。** 他の社員は読みません。**あなた専用のメモです。**

**書くのは手順だけ**（動いたコード・セレクタ・API／駄目だったやり方と理由／何回目で成功したか）。
経緯は日報、判断基準は `改善提案.md`。**新しいものを上に積む。200行を超えたら古いものから削る。**
書式は **状況／やり方／やって駄目だったこと／所要**。

> **⚠ 2026-08-25 19:3x 時点で 200行の上限を超えたまま。** `改善提案.md` に
> 「安定した手順を `運用ルール.md` 8章へ昇格させる」提案を出してある（未採否）。
> **19:00窓は 3項目（21行）足し、重複していた拡張切断の項を 22行 → 6行に畳んで相殺した。**
> **⚠ それでも上限は超えている。8章への昇格が決まるまで、削るだけでは追いつかない。**
> **→ 次に足す窓は、先に昇格の採否を確認すること。決まっていなければ、足す行数と同じだけ畳んでから足す。**

---
### note入稿: `file_upload` は ref 必須。捕捉した file input は**そのままでは読めない** — 2026-08-25（須崎公開）

**`input.click` パッチで捕捉した input は、accessibility tree に出ず ref が取れない**（read_page 2回とも0件）。
→ **DOMに append ＋ `aria-label` を付与 → `find` で「(付けたラベル) file input」を検索**すると ref が返る。1回で通る。
**画像キャプションは figcaption を実クリック → `type` で直接打てる。目次は空段落で＋メニュー→「目次」（1回目で成功）。**
**目次・写真の位置指定は、pasteの本文に `【ここに目次】` `【ここに写真】` の目印段落を入れておき、triple_click＋Delete で空にしてから挿入すると外れない。**

---
### フォロバのボタンは `Follow @H` ではなく **`Follow back @H`** — 2026-08-25（22:00窓）

**相手が先にフォローしてきている場合、`aria-label` が `Follow back @<handle>` になる。**
**既存のスニペット（`==='Follow @'+H`）は一致せず `NO_BUTTON` を返す。** 両方を見ること。

```js
const b=[...document.querySelectorAll('button[data-testid$="-follow"]')]
  .find(x=>/^Follow (back )?@/.test(x.getAttribute('aria-label')||'')&&(x.getAttribute('aria-label')||'').endsWith('@'+H));
```

---
### note で「描画されない」＝「押せていない」ではない — 2026-08-25（22:00窓）

**21:00窓が「ページが描画されず押せなかった」と記録した記事を開いたら `ALREADY_LIKED` だった。**
**押下は通っていた。** → **失敗と決める前に `スキを取り消す` ボタンの有無をもう一度読む。** 累計がずれる。

---
### リプが送れないのは、相手が返信範囲を制限しているせいのことがある — 2026-08-25（21:00窓）

**症状**: Reply を押すと `The post you are trying to reply to has been deleted or is not visible to you.`
**投稿は生きている**（views は増え続ける・ページは 200・こちらのいいねも残る）。**2回押しても同じ。**

**見分け方（これで確定できる）**: **入力欄をクリアして、その status ページを navigate で開き直す。**
→ **`Post your reply` の入力欄そのものが描画されなければ、相手の設定。うちの制限ではない。**
**同じ窓で別の投稿・いいね・フォローが通っているかも一緒に見る**（通っていればアカウントは無事）。

**3回目は押さない。候補から外す。** 停止条件ではない。

---
### `date` は、取った瞬間だけでなく「優先順位を切り替える直前」に取る — 2026-08-25（21:00窓）

**21:19 の時点で「21:37」だと思っていた（18分のずれ）。`date` は5回取っていたが、その間は見積もりで進めていた。**
**取り直さなければ、スキ4件・いいね2件・フォロー3件を落として閉じていた。**
**19:00窓と同じ失敗で2件目。** → **「もう時間がないから切り上げよう」と思った瞬間が、いちばん `date` を取るべきとき。**

---
### 拡張の切断は「10〜15秒あけて2回」で判定する — 2026-08-25（18:00窓）

**`[]` や `not connected` を1回見ても閉じない。** 実測: 18:03 に1件 → 18:04 に `[]` → 18:04:37 に1件（`connectedAt` 更新＝再接続）。
**`sleep 15` をはさんで、もう一度 `list_connected_browsers`。2回目も `[]` なら閉じる**（15:00窓は6回以上戻らず＝本物の切断）。
**`navigate` が `not connected` を返した直後も同じ。**

---
### X の検索結果の href は、ツール側で伏せられることがある — 2026-08-25

**`link` が `[BLOCKED: Base64 encoded data]` になって status URL が取れない。**
→ **`k.match(/^\/([^\/]+)\/status\/(\d+)/)` で分解し、id を2つに割って返すと通る。**

```js
const m=k.match(/^\/([^\/]+)\/status\/(\d+)/);
({user:m[1], id1:m[2].slice(0,10), id2:m[2].slice(10)})   // 連結して単独ページへ navigate
```

**プロフィールから押そうとして `NOT_FOUND` になることがある**（候補の投稿が上位に出ない）。
**単独ページへ行くほうが速い。引用の確認も同じ画面でできる。**

---
### X の送信ボタンは、JSの座標でも実座標でも「打つ前」を返す — 2026-08-25（4回目）

**打ち終わったらスクショを撮り直す。これが唯一の正解。** `getBoundingClientRect` の値をそのまま押さない。
compose の Post: 空 y=435 → 5行で y=574。**リプ欄の Reply: JSは y=431 を返すが実際は y=487。**

**⚠ リプ欄は、打ったあとツールバーが描画されないことがある**（8/25 21:00窓で再現）。
→ **打った文字の末尾を1回クリック → スクショを撮り直す → 実座標で押す。** これで出る。

**⛔ `/compose/post` でモーダルが開かず home のインライン欄にフォールバックすることがある。**
**このとき `tweetTextarea_0` が2つ存在する。** 掴み間違えると別の欄に打つ。

```js
const el=[...document.querySelectorAll('[data-testid="tweetTextarea_0"]')].find(e=>e.closest('[role="dialog"]'));
```

**復帰手順**: プレースホルダ（x=400,y=101 付近の文字の上）をクリック → モーダル内の文字の上を再クリック → focused を確認して打つ。
**投稿の成否は `location.href`（`/compose/post` → `/home`）。**

---
### X の `(A)(B OR C)` は丸括弧で機能する — 2026-08-25

**`一人暮らし 晩ごはん OR 夜ごはん` は前置きが OR に飲まれて無関係になる。丸括弧で囲むと全件が文脈一致。**
**⚠ 丸括弧が "Something went wrong" になるのは `lang:ja` と併用したときだけ。** 単独なら通る。

---
### ⛔ `tweetText` は引用ツイートの中身を返さない — 2026-08-25（誤爆1件の原因）

**状況**: いいね候補の精査。**本文が完全にクリーンでも、引用先が足切り対象のことがある。**
実例 @ozioreun: 本文は `自炊をすると満たされた気持ちになります` の19字。
**引用先は英語の Polymarket の賭け金の話（NEG `仮想通貨`）。**
**単独ページで「全文を取った」つもりでも、引用ボックスは最初から視界に入っていない。**

**やり方（候補取得のコードに1行足す。押す前に必ず通す）**

```js
const a=document.querySelector('article[data-testid="tweet"]');
({quote:((a.querySelector('div[role="link"]')||{}).innerText||'').slice(0,300)})  // 空でなければ引用あり
```

**押す前にスクリーンショットを1枚撮れば目視でも分かる**（引用は枠付きで描画される）。
**やって駄目だったこと**: 押してからスクショを撮った。**順番が逆。押す前に撮る。**

**⚠ 検索結果の `liked` は当てにならない。** 検索で `liked:false`、単独ページで `1 Like. Liked` の実例あり。
**既いいねの判定は、単独ページの `aria-label`（`N Likes. Like` / `N Like. Liked`）で行う。**

**⚠ 通知欄は1回目が `Something went wrong` で0セルになることがある。** navigate で再読み込みすると出る。
**空振りを「新規ゼロ」と書かない。**

---
### 窓が本当に閉じたかは、ログの記述では分からない — 2026-08-25

**前の窓が「閉じ 15:53」と書いていても生きていることがある**（15:00窓が 16:11 に X へリプ送信。16:00窓と重なった）。

```bash
ls -lt /Users/kyoichi/.claude/projects/-Users-kyoichi-Claud-/*.jsonl | head -5
grep -o "\"timestamp\":\"[^\"]*\"" "<該当jsonl>" | tail -3        # 最終書き込み時刻（UTC）
grep -l "<送られた文の一部>" /Users/kyoichi/.claude/projects/-Users-kyoichi-Claud-/*.jsonl  # 出所の特定
```

**⚠ サブエージェントの書き込みは親の jsonl に出ないことがある。** 親の最終時刻だけで「死んだ」と決めない。
**`switch_browser` が "No other browsers available" なら切替先も無い。`pgrep -x "Google Chrome"` は無意味**（切れているのは拡張の接続）。
**⚠ `tabs_context_mcp` が1回だけ成功して直後から失敗し続けることがある。1回通っても「繋がった」と判断しない。**

---
### note の「フォローしている人の新着」は API で取れない — 2026-08-25（19:00窓）

`/api/v*/timelines/following` `/api/v1/timeline` の**3本とも HTML を返す。推測で叩かない。3回でやめる。**
**候補はタグ軸から。`#自炊記録` `#晩ごはん` `#食費` `#台所` は 8/25 22時でも母集団が重なっていない。**

---
### X の「フォロー中のタイムライン」は候補取得に使えない — 2026-08-25（22:00窓）

**9回スクロールして3件。うち2件がフォロバ宣言、1件が AI副業セミナー。`#ブルバ100` の互助フォローで埋まっている。**

---
### リプ欄の Reply の位置は親ポストの行数で動く — 2026-08-25

**復帰は上の「送信ボタン」の項と同じ**（末尾クリック→スクショ→実座標）。**毎回スクショで取り直す。**
**送信の確認は入力欄が空になったか＋`from:kyoichi_kurashi&f=live` の重複確認。**

---
### ブラウザ無しでも、note記事の裏取りはできる — 2026-08-25

**WebFetch でログアウト状態の公開ページを取る。有料ラインの検証（8.5章）と同じ手。⚠ 15分キャッシュ。**

---
### note のスキ一覧の日付は `created_at`（`createdAt` ではない） — 2026-08-25

**状況**: リアクションフォローの対象（今日スキをくれた人）を抜く。
**`l.createdAt` で書いて空配列が返り、1回空振りした。** エラーにならないので気づけない。

```js
// 全記事ぶん引いて当日分だけ抜く。通知欄は使えない（/api/*/notifications は404）
const c=await (await fetch('/api/v2/creators/kyoichi_kurashi/contents?kind=note&page=1',{credentials:'include'})).json();
for(const n of c.data.contents){
 const j=await (await fetch(`/api/v3/notes/${n.key}/likes?page=1`,{credentials:'include'})).json();
 (j.data.likes||[]).forEach(l=>{ if((l.created_at||'')>='2026-08-25') /* l.user.urlname */ ; });
}
// 未フォロー判定は /api/v2/creators/{urlname} の data.isFollowing
```

**1記事50件まで1ページで返る。6記事で3秒。**

---
### X のレンダラが固まることがある — 2026-08-25

**`scrollBy` 中に `scrollY` が動かなくなり `Runtime.evaluate` が45秒タイムアウト×2。**
→ **`window.__seen` に貯めれば戻り値を失っても残る。復帰は navigate。**
→ **`scrollY` を毎回返し、前回と同じなら「固まり」。** 件数だけ見ると「枯れた」と誤読する。

---
### compose を開いた直後の `type` は、テキストエリアに入らないことがある — 2026-08-25

**状況**: タグ投稿。`/compose/post` へ navigate → クリック → `type` を5回。
**`tweetTextarea_0` の中身が `\n` だけだった。** モーダルは開いていて、見た目には気づけない。

**やり方（これで1回目から通る）**

```js
// クリックの直後に、これで焦点を確かめてから打つ
const el=document.querySelector('[data-testid="tweetTextarea_0"]');
({focused: document.activeElement===el||el.contains(document.activeElement)})
```

**クリック位置はプレースホルダの文字の上**（x=400 付近。右側の余白 x=500 以上だと外れる）。
**リプ欄も同じ**（「Post your reply」の文字の上・8/25 に1回目で通った）。

**`#` を含むポストは、Post の1回目がハッシュタグ補完を閉じるだけで終わる。**
→ **スクショで "posted" を確認し、`from:kyoichi_kurashi&f=live` で重複が無いことも見る。**
→ **宙に浮いたキー入力で背景の投稿にいいねが飛んでいないか、`liked` で確認する。**

---
### スレッドの親が描画されないときは、相手の `/with_replies` を見る — 2026-08-25（20:00窓）

**状況**: 自分宛リプが「どのポストへの返信か」を特定したい。**単独ページを4回開いて全部1件しか描画されず空振り**
（相手の status ページも、自分のポストの status ページも同じ）。
→ **`x.com/{相手}/with_replies` を開くと、親（自分の投稿）と返信が並んで出る。1回で取れる。**
**やって駄目だったこと**: 同じ status ページを navigate で再読み込みして待つ（2回とも同じ1件のまま）。

**⚠ note の記事URLも urlname を推測しない。** `/api/v3/notes/{key}` の **`data.user.urlname`** を取ってから開く
（`data.noteUrl` は返らない）。推測して1回 404 を踏んだ。

### X の検索の母集団は、時間帯で大きく変わる — 2026-08-25

**93件（8/24 23時）／41件（7時）／20件（12時）／13件（20時）。既いいねゼロなら「枯れた」ではない。**
**`lang:ja` ＋丸括弧は "Something went wrong"。`scrollBy(0,900)`×12回・各1.5秒に刻む（2200pxは空振り）。**

---
### note のフォロバ漏れは API で全件走査できる — 2026-08-25

**`/api/v2/creators/{me}/followers?page=N` の中身は `data.follows`（`users` ではない）。**
**`data.isLastPage` と `data.totalCount` があり、`isFollowing` が各要素に入っている。**

```js
let out=[],p=1;
while(p<=30){
 const j=await (await fetch(`/api/v2/creators/kyoichi_kurashi/followers?page=${p}`,{credentials:'include'})).json();
 const arr=(j.data&&j.data.follows)||[];
 arr.forEach(u=>{if(!u.isFollowing) out.push(u.urlname);});
 if(j.data.isLastPage||!arr.length)break; p++;
}
out
```

**1ページ12件・272名で23ページ・30秒。** **`?page=20` までで止めると 240件で打ち切られる。**
**`isLastPage` を必ず見ること。**

---
### X の compose は、JS挿入ではなく実キー入力で打つ — 2026-08-24

**`execCommand('insertText')` は `innerText` に入るのに画面のcomposeは空。JSの戻り値を信じると空投稿になる。**

**やり方**: **実座標クリック → `computer` の `type` → 改行は `key: Return`（空行は `repeat:2`）。**
**送信前に必ずスクショで目視する。** `innerText` は空行1つを `\n\n\n` と返すので文字列比較だけでは判定できない。

```js
const t=document.querySelector('[data-testid="tweetTextarea_0"]').innerText;
const norm=s=>s.replace(/\n{2,}/g,'\n\n').trim();  // これで want と比較する
```

**投稿後の `navigate` は「Leave site?」で止まる。** サイドバーの `a[href="/kyoichi_kurashi"]` を合成イベントで押す。

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
### note のフォローは API で押せる。**15件で 429**（8/25 は解除済み） — 2026-08-24

**`x-requested-with: XMLHttpRequest` と body `{}` の2つが要る。** これが無いと **422**。

```js
const d=(await (await fetch(`/api/v2/creators/${urlname}`,{credentials:'include'})).json()).data;
if(!d.isFollowing){
  await fetch(`/api/v3/users/${d.key}/following`,{method:'POST',credentials:'include',
    headers:{'content-type':'application/json','x-requested-with':'XMLHttpRequest'},body:'{}'});
}
// 検証は必ず isFollowing を取り直す。1窓10件までに割る。1件ずつ1.5秒空ける
```

**note のスキをくれた人は、記事ごとに全件取れる。通知欄は「他N名」で畳まれて取れない**
（`/api/v*/notifications` は全部404）。

```js
await fetch('/api/v2/creators/kyoichi_kurashi/contents?kind=note&page=1',{credentials:'include'});
await fetch(`/api/v3/notes/${key}/likes?page=${p}`,{credentials:'include'}); // data.likes[].user
```

**エンドポイントは推測で叩かない。** `window.fetch` を差し替えてから UIのボタンを1回押して記録する。
**ただし note の「スキ」押下だけは fetch ではなく XHR なので、この手では捕まらない**（記事ページで押す）。

---
### 候補取得のコード（X・共通） — 2026-08-24

**`/notifications`（All）も検索結果も、同じ1本で本文・時刻・status URL・`liked` が取れる。**
**`liked` を必ず一緒に取る。** 既いいねの割合で、軸が枯れたのか判定が厳しいのかを区別できる。

```js
[...document.querySelectorAll('article[data-testid="tweet"]')].map(a=>({
  d:(a.querySelector('time')||{}).dateTime,
  t:(a.querySelector('[data-testid="tweetText"]')||{}).innerText,
  liked:!!a.querySelector('button[data-testid="unlike"]'),
  link:[...a.querySelectorAll('a')].map(x=>x.getAttribute('href')).find(h=>/\/status\/\d+$/.test(h||''))}));
```

**軸①`一人暮らし 自炊` は枯れる**（40分差で2回引くと既いいねが半分）。
**軸③`自炊 OR 洗い物 OR 食洗機 OR 献立` は枯れない**（OR で広く取ると母集団が変わる）。
**着信は遅れて出る。** 「ゼロ」は「来ていない」ではなく「まだ見えていない」。

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

**やって駄目だったこと**: `users/lookup.json` の一括は `code:34`／`fetch('/username')` の og:description は空（SPA）。
**コスト**: 1件あたり navigate 1回＋JS 1回。**bio確認は 8/24 に13件、8/25 に4件の実害を止めている。省かない。**

---
### 窓の冒頭で、当日ログの既出アカウントを一括で取る — 2026-08-24

**当日ログは2700行を超える。全部読むと窓が終わらないが、飛ばすと同じ相手を二度判定する。**
**Bashは絶対パスで渡す。`cd` は許可で止まる。**

```bash
grep -oE "@[A-Za-z0-9_]+" "/Users/kyoichi/Claud用/SNS運用/ログ/$(date +%F).md" | sort -u | tr '\n' ' '
```

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
**全文を取らないと落とせない記事が、6日連続で出ている**
（8/25 は @jihanki_lab。タイトルは「一人暮らしの自炊が続かない人へ」でど真ん中、本文1行目がアフィ表記）。

---

**（削除した手順: 送る前の確認（数字の脱落・本文の残存）／note の一覧API取得／note の解除・フォロバ／X の購読アカウントの解除／X の入力欄クリア／公開済み記事の差分の扱い／公開済みnote記事の機械照合 → すべて `運用ルール.md` 5章・8章・8.5章にある。
`status` のIDを推測しない／X の改行は innerText で判定できない → `改善提案.md` に昇格を提案済み）**
