import re, collections
L=[l.rstrip('\n') for l in open('comments_raw.txt',encoding='utf-8') if l.strip()]
out=[]; per=collections.Counter(); own=0
for l in L:
    vid=l.split(' @@ ')[1].strip() if ' @@ ' in l else ''
    head=l.split(' @@ ')[0]
    m=re.match(r'(@[^ ]+)\s*(?:~\s*)?•\s*([^~]+?)\s*~\s*(.*?)\s*~\s*Reply\b(.*)$',head)
    if not m: continue
    a,age,txt,rest=m.groups()
    lk=re.match(r'\s*~\s*\d+ repl(?:y|ies)\s*~\s*(\d+)\s*~',rest)
    likes=int(lk.group(1)) if lk else 0
    if a=='@TheSatFy': own+=1
    if vid: per[vid]+=1
    out.append((a,age.strip(),txt.replace(' ~ ',' / '),likes,vid))
open('comments_clean.txt','w',encoding='utf-8').write('\n'.join(f"{a} | {age} | {lk}♥ | {v[:45]} | {t}" for a,age,t,lk,v in out))
print(len(out),'parsed; own',own)
for v,n in per.most_common(): print(n,v)
