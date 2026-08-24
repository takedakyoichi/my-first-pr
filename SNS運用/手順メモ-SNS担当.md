# 手順メモ（SNS担当）

**このファイルは SNS担当 だけが書きます。** 他の社員は読みません。**あなた専用のメモです。**

**書くのは手順だけ**（動いたコード・セレクタ・API／駄目だったやり方と理由／何回目で成功したか）。
経緯は日報、判断基準は `改善提案.md`。**新しいものを上に積む。200行を超えたら古いものから削る。**
書式は **状況／やり方／やって駄目だったこと／所要**。

---
### note のフォローバックは「フォローバック」を名指しで押す — 2026-08-24

**状況**: 未フォロバの解消。**プロフィールには `フォロー` ボタンが10個以上ある**（サイドバーのおすすめユーザー）。

**やり方**: **本人のボタンは「フォローバック」。名指しで取り、API で検証する。**

```js
const f=[...document.querySelectorAll('button')].find(b=>/^フォローバック$/.test(b.innerText.trim()));
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>f.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
await new Promise(r=>setTimeout(r,2500));
const d=(await (await fetch(`/api/v2/creators/${URLNAME}`,{credentials:'include'})).json()).data;
d.isFollowing ? 'FOLLOWED-OK' : 'FAILED';
```

**やって駄目だったこと**: `^フォロー$` の最初の1件を押した → **サイドバーのおすすめユーザーだった。**
しかも検証を **「ページのどこかに『フォロー中』の文字があるか」** で書いていたため **`OK` と誤表示。**
**サイドバーに既フォローの人が並んでいれば、何もしなくても真になる。**

**結論: 押下の検証は、押した対象そのものの状態で見る。** note は API に `isFollowing` があるのでそこで見る。
**総数でも二重チェックできる**（`/api/v2/creators/kyoichi_kurashi/followings?page=1` の `totalCount`）。

**所要**: 1件あたり navigate 1回＋JS 1回。

---
### note の未フォロバは毎日出る（16:50に解消した4時間後に2件） — 2026-08-24

**状況**: フォロバ漏れの走査。**「今日やった」は理由にならない。**

**やり方**: **タグ新着の取得と同じJSの中に混ぜて1回で流す。** 22ページで数十秒。

```js
let fb=[],page=1;
for(;;){
  const r=await fetch(`/api/v2/creators/kyoichi_kurashi/followers?page=${page}`,{credentials:'include'});
  const d=(await r.json()).data||{};
  (d.follows||[]).forEach(u=>{ if(u.isFollowed && !u.isFollowing) fb.push(u.urlname); });
  if(d.isLastPage||page>30) break; page++;
}
fb;
```

**溜まる相手には規則性がある: こちらがスキを押した相手が、あとからフォローしてくる。**
→ **スキを押した窓の次の窓で走査すると当たりやすい。**

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
### X の検索は `from:` をまとめても、1人が連投していると埋まる — 2026-08-24

**やって駄目だったこと**: 関係が続く8名を `(from:a OR from:b ...)` で1回に引いた
→ **1人が10連投していて、10件すべてがその人。他7名は1件も出ない。**

**結論: `from:` のまとめ引きは「誰が動いているか」の確認には使えるが、候補集めには使えない。**
**人数ぶん個別に開くか、フォロー中TLを使う。**


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

**半角数字は入力時に脱落する。**「約10万円」→「約万円」、「5分」→「分」の実例が2回。
→ **数字を含むなら送信前に残存を確認。**

**【2026-08-24 訂正】「漢数字に切り替える」は誤りだった。**
この回避策が既定になり、**最初から漢数字で書く**ようになっていた。
相手が「一人暮らし**3年目**」と書いたリプに「同じ**三年目**です」と返した実例あり。
**同じ言葉を違う表記で返していて不自然。** オーナーから指摘を受けた。

**脱落したときは、この順で対処する。**
1. **もう一度入力し直す**（二度目で入ることがある）
2. **入力欄をクリアして最初から打ち直す**
3. **その数字を含む表現を変える**
4. **漢数字は最後の手段。** 使ったら日報に理由を書く

**数字は算用数字で書く。**「3年目」「100回」「900円」。
**漢数字が自然な語はそのまま**（一人暮らし／一汁一菜／一番）。**これは数量ではなく語の一部。**
**迷ったら相手の書き方に合わせる。**

**本文そのものが入っていないことがある。** 中身が改行1文字だけだった実例あり。
→ **文字数と本文の完全一致を、送信直前に確認する。**

---

**（削除した手順: note の一覧API取得／note の解除・フォロバ／X の購読アカウントの解除／X の入力欄クリア／公開済み記事の差分の扱い／公開済みnote記事の機械照合 → すべて `運用ルール.md` 5章・8章・8.5章にある。
`status` のIDを推測しない／X の改行は innerText で判定できない → `改善提案.md` に昇格を提案済み）**
