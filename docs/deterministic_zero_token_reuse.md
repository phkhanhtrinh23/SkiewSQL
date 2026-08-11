# Deterministic ("zero-token") reuse vs. LLM-voted reuse — implementation & honest analysis

Config A decides, **per sub-goal**, whether to *reuse* a stored view/skill or *generate* a fresh one.
We now support two mechanisms for that decision:

- **LLM-voted** (the original): an LLM votes on whether to reuse a retrieved candidate.
- **Deterministic / zero-token** (new, Zero-Mem–inspired): the decision uses embedding retrieval + a
  structural guard + calibration, with **no LLM call at all**.

Toggle with `SKIEW_DETERMINISTIC_REUSE=1` (read by `sqlview.deterministic_reuse_on()`; all three
runners branch on it). Everything else in the pipeline (schema-free rewrite, N×M decompose-and-align,
generation, compose) is identical — so this isolates the *reuse-selection* mechanism.

---

## 1. How **LLM-voted** reuse works (the baseline)

Per sub-goal `req`:

```
cands = sqlview.retrieve_candidates(graph, req, k=6)     # Stage-1 structural guard already applied
                                                         # (category/grain/outputs/filters), then lexical top-k
if cands:
    picks = [agents.choose_reuse(llm, req, cands) for _ in range(verify)]   # <-- N LLM CALLS
    top, cnt = Counter(names).most_common(1)[0]
    spec = top if cnt*2 > verify else None               # strict majority to REUSE
    if spec is None: vrej += 1                            # candidates existed but the vote rejected -> generate
```

- **Who decides:** an **LLM**, voting `verify` times (we use `verify=3`), needs a **strict majority**
  on the *same* view to reuse. Any split/abstention → reject → generate fresh.
- **Cost:** up to `verify` LLM calls **per sub-goal that has any guard-compatible candidate**.
- **Character:** *conservative* — the vote often rejects, so reuse fires rarely (reject-biased by design).
- (In `bq_method`/`realrun` the analogue is `agents.verify_reuse` gating a `retrieve()` hit; same idea.)

## 2. How **deterministic / zero-token** reuse works (new)

Per sub-goal `req` — `sqlview.select_reuse(graph, req, embedder, tau=0.55, margin=0.05)`:

```
survivors = [(embedder.sim(req.text, c.description), c)          # embedding RETRIEVAL
             for c in graph.candidates(req.category)
             if not _reuse_blocked(c) and compatible(c, req)[0]] # STRUCTURAL GUARD (zero-token):
                                                                 #   category + outputs + grain + filters
if not survivors: return None                                    # nothing compatible -> generate
top_sim, top = max(survivors)
if top_sim < tau: return None                                    # (a) retrieval-confidence calibration
for sim2, c2 in survivors[1:]:                                   # (b) DISCARD CONFLICTING EVIDENCE:
    if top_sim - sim2 < margin and (grain(c2)!=grain(top) or outputs(c2)!=outputs(top)):
        return None                                              #     near-tie but structurally different -> abstain
    break
return top                                                       # reuse, deterministically
```

- **Who decides:** **no LLM** — the mechanical guard (`compatible`: category match, required outputs
  covered, grain exact-or-finer, filters equal/contained) plus embedding similarity ≥ `tau`, plus a
  calibration step that **abstains when two near-tied survivors disagree** on grain/outputs.
- **Cost:** **zero LLM tokens** for the reuse decision (the Zero-Mem point).
- **Character:** *less conservative than the vote* — if a candidate passes the guard and clears `tau`,
  it is reused; there is no LLM second-guessing it.

## 3. The difference, side by side

| | LLM-voted | Deterministic / zero-token |
|---|---|---|
| Decider | LLM, `verify` votes, strict majority | structural guard + embedding + calibration |
| LLM calls for reuse | up to `verify` per candidate sub-goal | **0** |
| Bias | conservative (rejects on any doubt) | reuses whenever guard+`tau` pass; abstains only on structural near-ties |
| Failure mode | may **reject a valid reuse** (wastes a regeneration) | may **accept a reuse the LLM would've vetoed** |

---

## 4. Empirical result on BEAVER (honest)

On the **same 60 questions** both configs completed:

| | correct | reuse fired (total) |
|---|---|---|
| A — LLM-voted (`verify=3`) | **11/60 = 18.3%** | 0 |
| A — deterministic / zero-token | **11/60 = 18.3%** | 2 |

**They are tied on accuracy.** The deterministic guard fired reuse **2×** where the LLM vote fired
**0×** (the vote is more conservative), but on BEAVER reuse is so rare that the mechanism cannot move
the score. **The real benefit here is cost:** the deterministic variant spends **zero LLM tokens** on
reuse decisions.

### 4a. A genuine *mechanism divergence* — `dw_real_6`

> *"What are the subject titles, their material titles, ISBN numbers, and total costs of new materials
> for each subject title?"*

| | reuse decision | outcome |
|---|---|---|
| LLM-voted | candidate existed → **vote REJECTED it** (`reused=0`) → generated fresh | wrong (result mismatch) |
| Deterministic | same candidate → **guard+`tau` ACCEPTED it** (`reused=1`, a `subject_titles` view) | wrong (result mismatch) |

This is exactly where the two mechanisms diverge: the **LLM vote vetoed** a reuse that the
**structural guard admitted**. Here it didn't change correctness (both wrong on an unrelated
join/cost aggregation), but it shows the decision boundary cleanly — deterministic reuses what the
vote is too cautious to accept.

### 4b. The accuracy flip you asked about — `dw_real_5` — analyzed honestly (it's NOT the mechanism)

> *"List the unique term code, subject title, room, floor, building key, street address, city, state,
> postal code, formats, and number of enrolled students for courses with more than 300 attendees."*

| | reuse | outcome |
|---|---|---|
| LLM-voted | **0** | ❌ wrong — `(1054) Unknown column 'ss_term.TERM_DUR…'` (a **hallucinated column**) |
| Deterministic | **0** | ✅ correct |

It is tempting to call this "deterministic beat LLM-voted." **It is not** — **reuse fired 0× in both
configs**, so the reuse mechanism was *not involved*. The only thing that differed is the SQL the LLM
*generated* (one run invented a non-existent column, the other didn't). This is **LLM generation
nondeterminism** (gpt-5-mini varies run-to-run even at temperature 0), not the zero-token reuse. The
symmetric evidence: across the 60 Q there are **2 flips each way** (LLM-wrong/DET-right *and*
DET-wrong/LLM-right), which is the signature of noise, not a systematic win.

---

## 5. Honest conclusion

- **Accuracy:** the zero-token reuse is **accuracy-neutral** vs. LLM-voted on our benchmarks, because
  reuse is too rare (BEAVER/BigQuery, `reuse ≈ 0–2`) to differentiate the configs. Where the decision
  *does* differ (`dw_real_6`), the deterministic guard reuses what the vote rejects — but that didn't
  change correctness here.
- **Cost:** it removes **all** LLM verify/choose calls for reuse — the genuine, provable win, and the
  Zero-Mem thesis ("memory operations should cost zero tokens").
- **Where it would matter for accuracy:** a benchmark where reuse fires *often*. Our LLM-voted runs
  (`verify=3`) only exist on BEAVER/BigQuery (rare reuse); Spider2-lite — where reuse fires much more —
  was run with `verify=0` (already no LLM vote), so it offers no LLM-vote-vs-deterministic contrast.
  Testing on a high-reuse, LLM-voted setting is the experiment that could show a real accuracy gap.

**Do not read the `dw_real_5` flip as a win.** The honest summary is: *same accuracy, zero token cost,
slightly more (guard-admitted) reuse.*
