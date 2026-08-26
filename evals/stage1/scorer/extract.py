"""Stage 1 option extraction — rule (a), pre-registered: presented order, fixed token
budget per option, cap at six, NO semantic merging. Deterministic and auditable."""
import re,sys,json
CAP=6; TOKEN_BUDGET=220           # words retained per option
HEAD=re.compile(r'^(#{2,4}\s+\S|\*\*[^*]{3,80}\*\*\s*$|\d+[\.\)]\s+\S)')
def extract(text):
    lines=text.split('\n'); blocks=[];cur=[]
    for ln in lines:
        if HEAD.match(ln.strip()) and cur and len(' '.join(cur).split())>25:
            blocks.append('\n'.join(cur)); cur=[ln]
        else: cur.append(ln)
    if cur: blocks.append('\n'.join(cur))
    opts=[b.strip() for b in blocks if len(b.split())>25]
    if len(opts)<2:                       # no headings: fall back to paragraph groups
        opts=[p.strip() for p in re.split(r'\n\s*\n', text) if len(p.split())>40]
    trimmed=[' '.join(o.split()[:TOKEN_BUDGET]) for o in opts]
    return trimmed[:CAP], len(trimmed)
if __name__=='__main__':
    out={}
    for f in sys.argv[1:]:
        o,total=extract(open(f).read())
        out[f.split('/')[-1]]={'kept':len(o),'found':total,'displaced':max(0,total-CAP)}
    print(json.dumps(out,indent=1))
