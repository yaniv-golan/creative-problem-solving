"""Cross-judge reliability from naturally duplicated option texts.

Padded controls duplicate their base answer's blocks; where a base and its padded twin were
judged by DIFFERENT batches, the same option text carries two independent label sets. That is a
free cross-judge replicate — no extra spend, and no judge knew any item was a repeat.
"""
import json,glob,hashlib,sys,collections,itertools
W=sys.argv[1] if len(sys.argv)>1 else "."
def alpha(pairs):
    pairs=[(a,b) for a,b in pairs if a and b]
    n=len(pairs)
    if n<2: return None,n
    Do=sum(1 for a,b in pairs if a!=b)/n
    vals=[v for p in pairs for v in p]; c=collections.Counter(vals); N=len(vals)
    De=1-sum(k*(k-1) for k in c.values())/(N*(N-1))
    return (round(1-Do/De,3) if De else None), n
batch={}
for b in (1,2,3,4):
    try:
        for i in open(f"{W}/batch-{b}.txt").read().split(): batch[i]=b
    except FileNotFoundError: pass
labels={}
for f in glob.glob(f"{W}/labels/*.json"):
    for it in json.load(open(f))['items']:
        for o in it['options']: labels[(it['item_id'],o['n'])]=o
texts=collections.defaultdict(list)
for f in glob.glob(f"{W}/items/*.json"):
    d=json.load(open(f))
    for o in d['options']:
        texts[hashlib.sha256(o['text'].encode()).hexdigest()].append((d['item_id'],o['n']))
P=collections.defaultdict(list)
used=0
for h,inst in texts.items():
    inst=[x for x in inst if x in labels]
    for a,b in itertools.combinations(inst,2):
        if batch.get(a[0])==batch.get(b[0]): continue          # same judge: not a replicate
        used+=1
        A,B=labels[a],labels[b]
        for k in ('causal_relevance','actor_named','first_test','breaches_hard_constraint'):
            P[k].append((A.get(k),B.get(k)))
        sa={s['id']:s for s in A.get('scenarios',[])}; sb={s['id']:s for s in B.get('scenarios',[])}
        for sid in set(sa)&set(sb):
            P['admissible'].append((sa[sid].get('admissible'),sb[sid].get('admissible')))
            P['milestone'].append((sa[sid].get('milestone'),sb[sid].get('milestone')))
print(f"cross-judge replicate option-pairs available: {used}\n")
print(f"{'predicate':26s} {'alpha':>7s} {'n':>5s}  gate >= 0.67")
allv=[]
for k in ('admissible','milestone','causal_relevance','actor_named','first_test','breaches_hard_constraint'):
    a,n=alpha(P[k]); allv+=P[k]
    mark='' if a is None else ('PASS' if a>=0.67 else 'FAIL')
    print(f"{k:26s} {str(a):>7s} {n:>5d}  {mark}")
a,n=alpha(allv)
print(f"{'ALL atomic labels pooled':26s} {str(a):>7s} {n:>5d}  {'PASS' if a and a>=0.67 else 'FAIL'}")
