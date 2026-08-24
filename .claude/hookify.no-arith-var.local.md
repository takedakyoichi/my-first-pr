---
name: block-arith-with-variable
enabled: true
event: bash
action: block
pattern: \$\(\([^)]*[A-Za-z_]
---

🚫 **変数を使った `$(( ))` は実行できません。書き直してください。**

**理由**: Claude Code は、変数を含む算術展開に**必ず手動承認**を要求します。

```
Arithmetic expansion references variable or non-literal: SECONDS
```

`bypassPermissions` でも外せません。**このMacでは毎時7:00〜23:00に無人のスケジュールタスク（SNS運用の窓）が動いており、ここで止まるとオーナーが承認するまで進みません。**

## 書き直し方

**待ち時間のループは、回数で書いてください。**

| ✕ | `END=$((SECONDS+3000)); while [ $SECONDS -lt $END ]; do ...; sleep 20; done` |
|---|---|
| **○** | `for i in $(seq 1 150); do ...; sleep 20; done`（20秒×150回＝50分） |

**カウンタも同じです。**

| ✕ | `n=$((n+1))` |
|---|---|
| **○** | `n=$(expr $n + 1)` ／ そもそも `for` で回して数えない |

**数える・計算する処理は、シェルではなく Python でやってください。**
`python3 -c "..."` や、スクラッチパッドに `.py` を書いて `python3 /絶対パス/x.py` で実行すれば通ります。
**日本語の文字数を数えるときも Python です**（`wc -m` はロケールによってバイト数を返します）。

## 例外が要るとき

このルールは `/Users/kyoichi/Claud用/.claude/hookify.no-arith-var.local.md` にあります。
**AIが自分でこのファイルを書き換えてはいけません。** 変更はオーナーが行います。
