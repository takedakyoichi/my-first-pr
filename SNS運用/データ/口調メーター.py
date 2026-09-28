# -*- coding: utf-8 -*-
"""口調メーター（2026-09-29）: 直近N日に送ったポストとリプを数え、AI口調チェック⑦の目標と並べる。
使い方: python3 口調メーター.py [日数=3]
分析担当が統合回で毎日実行し、結果を分析ブリーフの口調カルテに貼る。"""
import re, glob, os, sys, datetime, collections

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
LOGDIR = '/Users/kyoichi/Claud用/SNS運用/ログ'
today = datetime.date.today()
since = (today - datetime.timedelta(days=DAYS)).isoformat()

posts, replies = [], []
for f in sorted(glob.glob(f'{LOGDIR}/2026-*.md')):
    d = os.path.basename(f)[:-3]
    if d < since or d >= today.isoformat():
        continue
    lines = open(f, encoding='utf-8').read().split('\n')
    inrep = False
    for i, line in enumerate(lines):
        if line.startswith('### '):
            inrep = line.startswith('### リプ')
        m = re.match(r'^### ポスト（([0-9:]+) 送信', line)
        if m and i + 1 < len(lines) and lines[i + 1].startswith('```'):
            body = []
            for l in lines[i + 2:]:
                if l.startswith('```'):
                    break
                if not l.startswith('http'):
                    body.append(l)
            posts.append('\n'.join(body).strip())
        if inrep and line.startswith('| @'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 3:
                mm = re.search(r'`([^`]+)`', cells[2])
                if mm:
                    replies.append((cells[1], mm.group(1)))

EMO = r'[\U0001F300-\U0001FAFF☀-➿]'
REACT = re.compile(r'[！!？?…笑]|' + EMO + r'|最高|めっちゃ|本当に|ほんと|すぎ|結局|気づいたら|いまだに|正直')
SPOKEN = re.compile(r'んだけど|んだよ|じゃん|ちゃう|ちゃっ|てる|けど|よね|なぁ|なあ|のよ|わ[。\n]|わ$|っぽ|かも|みたい|だよ|れる$')
REASON = re.compile(r'ので、|から、|のに、')

def pct(k, n): return f'{k}/{n}' + (f' ({100*k//n}%)' if n else '')

def judge(val, n, lo=None, hi=None):
    if n == 0: return '—'
    r = val / n
    if lo is not None and r < lo: return '⛔ 下回り'
    if hi is not None and r > hi: return '⛔ 上回り'
    return '⭕'

print(f'## 口調メーター（{since} 〜 {(today - datetime.timedelta(days=1)).isoformat()}・{DAYS}日）\n')
n = len(posts)
rows = []
allmaru = sum(1 for t in posts if t and all(l.strip().endswith('。') for l in t.split('\n') if l.strip()))
react = sum(1 for t in posts if REACT.search(t))
spoken = sum(1 for t in posts if SPOKEN.search(t))
reason = sum(1 for t in posts if REASON.search(t))
twoblk = sum(1 for t in posts if len([b for b in re.split(r'\n\s*\n', t) if b.strip()]) == 2)
print(f'### ポスト n={n}（目標は他人88本の実測）\n')
print('| 項目 | うち | 目標 | 判定 |\n|---|---|---|---|')
print(f'| 全行が「。」 | {pct(allmaru,n)} | 4割以下 | {judge(allmaru,n,hi=0.4)} |')
print(f'| 反応あり | {pct(react,n)} | 4割以上 | {judge(react,n,lo=0.4)} |')
print(f'| 話し言葉あり | {pct(spoken,n)} | 4割以上 | {judge(spoken,n,lo=0.4)} |')
print(f'| 「〜ので、」等あり | {pct(reason,n)} | 2割以下 | {judge(reason,n,hi=0.2)} |')
print(f'| 1行＋空行＋1行 | {pct(twoblk,n)} | 4割以下 | {judge(twoblk,n,hi=0.4)} |')

m = len(replies)
txt = [r[1] for r in replies]
def words(s): return set(re.findall(r'[一-龥ァ-ヶー]{2,}', s))
sym = sum(1 for t in txt if re.search(r'[！!？?〜…]|' + EMO, t))
echo2 = sum(1 for (p, t) in replies if len(words(p) & words(t)) >= 2)
sou = sum(1 for t in txt if re.search(r'そう(です|ですね)?。?$', t))
hook = sum(1 for t in txt if re.search(r'[？?]|ますか|ですか|自分|うち|私も|私は', t))
print(f'\n### リプ n={m}（目標は⑦-R）\n')
print('| 項目 | うち | 目標 | 判定 |\n|---|---|---|---|')
print(f'| 記号・絵文字あり | {pct(sym,m)} | 3割以上 | {judge(sym,m,lo=0.3)} |')
print(f'| 相手の語を2語以上言い直し | {pct(echo2,m)} | 3割以下 | {judge(echo2,m,hi=0.3)} |')
print(f'| 「〜そうです」締め | {pct(sou,m)} | 3割以下 | {judge(sou,m,hi=0.34)} |')
print(f'| 質問か自分の話 | {pct(hook,m)} | 3割以上 | {judge(hook,m,lo=0.3)} |')

# 新しい型への固まり（直しすぎの検知）: 同じ書き出し・同じ絵文字・同じ締めが3割を超えたら赤
print('\n### 新しい型に固まっていないか（同じものが3割を超えたら ⛔）\n')
for label, items, k in [
    ('ポストの書き出し2字', [t[:2] for t in posts if t], len(posts)),
    ('リプの書き出し2字', [t[:2] for t in txt], m),
    ('リプの最後3字', [re.sub(r'[。\s]+$', '', t)[-3:] for t in txt], m),
    ('リプの絵文字', [e for t in txt for e in re.findall(EMO, t)], m),
]:
    c = collections.Counter(items).most_common(3)
    worst = c[0][1] / k if c and k else 0
    mark = '⛔ 固まっている' if worst > 0.3 and k >= 5 else '⭕'
    print(f'- {label}: ' + '、'.join(f'「{a}」{b}' for a, b in c) + f' → {mark}')
