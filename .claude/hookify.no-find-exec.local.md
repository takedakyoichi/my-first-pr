---
name: block-find-exec
enabled: true
event: bash
action: block
pattern: (?:^|&&|\|\||;)\s*find\s+[^|;&]*\s-(exec|execdir|ok|okdir|delete)\b
---

🚫 **`find -exec` / `-delete` は実行できません。書き直してください。**

**理由**: `-exec` は任意コマンドを実行でき、`-delete` はファイルを消せるため、
**権限モードに関係なく必ず手動承認になります。** 無人の窓がここで止まります
（2026-08-25 朝、7:00の窓がこれで4時間半止まりました）。

## 書き直し方

| ✕ | `find "/path" -name "*タグ投稿*" -exec cat {} \;` |
|---|---|
| **○** | `find "/path" -name "*タグ投稿*"` で一覧を出し、**次の呼び出しで `cat "見つかったパス"`** |
| **○** | パスの見当がつくなら `ls "/path/"` → `cat "/path/ファイル名"` |

**`-delete` が要る場面は、そもそもオーナーに聞いてください**（破壊的コマンドのルールと同じ）。

## 例外が要るとき

このルールは `/Users/kyoichi/Claud用/.claude/hookify.no-find-exec.local.md` にあります。
**AIが自分でこのファイルを書き換えてはいけません。** 変更はオーナーが行います。
