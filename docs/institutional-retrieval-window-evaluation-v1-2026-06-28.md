# SourceTrace v2 institutional retrieval window evaluation v1 — 2026-06-28

## Goal

Check whether the widened retrieval window for institutional-intent queries helps consistently across a slightly broader live pack without obvious regressions or commentary/vendor crowding.

## Live pack

Queries checked:
- break glass account guidance conditional access official best practice
- data breach notification checklist authority official guidance
- legal hold steps records retention official guidance
- remote work reporting obligations Poland employer official guidance
- records retention policy official guidance public sector
- incident response plan official guidance public sector

## Result by case

### Break glass
- candidate pool remained healthy
- selected shape stayed institutional + practical companion
- no obvious regression

Verdict: good

### Breach notification
- candidate pool remained strongly institutional
- selected pair stayed FTC + ICO
- no regression

Verdict: strong

### Legal hold
- institutional evidence now survives into the pool instead of vendor/vendor lock-in
- selected shape improved materially even though one vendor companion still remains

Verdict: materially better

### Remote work reporting
- result is still unstable
- this run did **not** preserve the earlier `gov.pl` win; the selected shape returned to Deloitte + easyeor-style advisory/commercial material
- source typing for the surviving pool was also weak (`unknown`, `unknown`, `unknown`)

Verdict: still weak / not yet stable

### Records retention policy
- candidate pool was strongly institutional
- selected shape looked healthy

Verdict: good

### Incident response plan
- candidate pool was strongly institutional
- selected shape looked healthy and operationally plausible

Verdict: strong

## Overall verdict

`institutional-retrieval-window-v1` is a **net positive** and should remain in place.

Why:
- it materially improved legal-hold
- it did not obviously regress the cleaner institutional-intent cases
- it helped keep institutional pools healthy in several broader public-sector guidance cases

But:
- Poland remote-work reporting is still not stable enough
- that case likely needs a more specific follow-up than just keeping the wider retrieval window
\n## Main interpretation

The widened retrieval window solved a real generic seam problem, but it did **not** finish the hardest jurisdiction-specific retrieval problem.

That means:
- keep the retrieval-window change
- do not roll it back
- but treat remote-work / Poland-style public-institutional retrieval as the next sharper diagnostic target

## Recommended next bounded slice

`poland-institutional-retrieval-diagnostics-v1`

Goal:
- inspect why the remote-work / Poland case is still unstable even after the widened retrieval window
- determine whether the sharper issue is query phrasing, source typing, host heuristics, or provider ordering volatility
