"""Driver: run plan_groups.py's main() with a forward-checking lead search.

Same objective, same tie-breaks, same outputs. The only change is that the exhaustive
search prunes with forward checking, so it can PROVE infeasibility instead of running out
of budget. plan_groups.py's own doctrine merges a proven-infeasible pinch; without a proof
it refuses. Here the pinch is real: one 6-member cluster conflicts with single-member
clusters on every one of its candidates, and a singleton has no alternative lead.
"""
import sys, itertools
sys.path.insert(0, "/sessions/local_c89gdigca2/mnt/.local-plugins/marketplaces/local-desktop-app-uploads/creative-problem-solving/scripts")
import plan_groups as P

JOINING = P.JOINING


def choose_leads(clusters, rel, rounds=12):
    n = len(clusters)
    J = lambda a, b: rel.get(frozenset((a, b))) in JOINING

    order = sorted(range(n), key=lambda i: (-len(clusters[i]), clusters[i][0]))
    lead = {i: clusters[i][0] for i in range(n)}
    for i in order:
        lead[i] = min(clusters[i], key=lambda m: (
            sum(1 for j, l in lead.items() if j != i and J(m, l)), m))
    viol = []
    for _ in range(rounds):
        viol = [(i, j) for i, j in itertools.combinations(range(n), 2) if J(lead[i], lead[j])]
        if not viol:
            break
        moved = False
        for i in sorted({x for pair in viol for x in pair},
                        key=lambda i: (len(clusters[i]), clusters[i][0])):
            cur = sum(1 for j, l in lead.items() if j != i and J(lead[i], l))
            cand = min(clusters[i], key=lambda m: (
                sum(1 for j, l in lead.items() if j != i and J(m, l)), m))
            new = sum(1 for j, l in lead.items() if j != i and J(cand, l))
            if new < cur:
                lead[i] = cand
                moved = True
        if not moved:
            break

    proven = True
    if viol:
        cand = {i: sorted(clusters[i]) for i in range(n)}
        order2 = sorted(range(n), key=lambda i: (len(cand[i]), clusters[i][0]))
        sol = {}

        def place(k, dom):
            if k == len(order2):
                return True
            i = order2[k]
            for m in dom[i]:
                if any(J(m, sol[j]) for j in sol):
                    continue
                sol[i] = m
                nd = dict(dom)
                dead = False
                for t in order2[k + 1:]:
                    nd[t] = [x for x in dom[t] if not J(x, m)]
                    if not nd[t]:
                        dead = True
                        break
                if not dead and place(k + 1, nd):
                    return True
                del sol[i]
            return False

        if place(0, cand):
            lead = dict(sol)
            viol = [(i, j) for i, j in itertools.combinations(range(n), 2) if J(lead[i], lead[j])]
        else:
            proven = True

    return [lead[i] for i in range(n)], viol, proven


P.choose_leads = choose_leads
P.main(sys.argv[1], 45, 10)
