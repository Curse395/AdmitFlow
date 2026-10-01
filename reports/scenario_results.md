# AdmitFlow - Scenario Simulation

> **Every number in this report is a hypothetical simulation of stated assumptions,**
> computed by arithmetic on the synthetic AdmitFlow funnel. None of it is a forecast, a
> guarantee, or real-world institutional performance. Scenario outputs describe what
> *would* follow *if* an assumption changed - not what *will* happen.

---

## 1. How the engine works

The engine is deliberately simple and fully deterministic. There is no sampling, no
fitted parameter and no randomness, so every result is exactly reproducible and
auditable by hand.

**Anchor.** `CYC-2025`, week index 36, the latest eligible forecast origin
in the most recent cycle. **Scenario frame**: the funnel's tracked endpoint at that
anchor under its observed conversion rates.

**Observed funnel state at the anchor** (from `fact_forecast_panel.csv`, portfolio):

| Stage | Observed cumulative at anchor T |
|---|---|
| `S` applications submitted | 3,001 |
| `V` applications verified | 2,481 |
| `D` decisions issued | 2,441 |
| `A` admitted | 1,118 |
| `E` enrolled | 686 |

**Observed conversion rates at the anchor** (cumulative, portfolio):

| Rate | Definition | Value |
|---|---|---|
| `r_verify` | V / S | 0.8267 |
| `r_decision` | D / V | 0.9839 |
| `r_admit` | A / D | 0.4580 |
| `r_yield` | E / A | 0.6136 |

End-to-end yield, S to E: **0.2286**
(22.9% of submitted applications end up enrolled).

**Why a drain, not a time extrapolation.** The panel's flow is lumpy: for `PGM-01` in
`CYC-2025`, `wk_applications_submitted` is 0 in every week from 30 to 42, while 170
decisions land in week 34 and 0 in the weeks either side. A trailing-4-week mean weekly
flow therefore captures a single decision burst and projects hundreds of phantom
decisions per week. That approach was implemented first, measured, and rejected. The
drain formulation below uses no time extrapolation at all.

**Projection arithmetic.** Applying the observed rates through the chain:

```
S_h = S * volume_mult        submitted volume entering the funnel
V_h = S_h * r_verify         applications verified
D_h = V_h * r_decision       decisions issued
A_h = D_h * r_admit          admitted
E_h = A_h * r_yield          enrolled      <-- reported output
```

This is **horizon-free by construction**. It answers "where is the funnel currently
tracking to, if the remainder converts at the rates observed so far", which is what a
scenario means. It is not a time-phased path to a specific week, and it uses no
post-origin panel value.

| Family | Factor perturbed | Meaning |
|---|---|---|
| **A** Application volume change | `S` | submitted volume entering the funnel |
| **B** Verification conversion change | `r_verify` | share of submitted applications that reach verification |
| **C** Admission conversion change | `r_admit` | share of issued decisions that result in an admission |
| **D** Enrolment yield change | `r_yield` | share of admissions that convert to enrolment |

Scenario A perturbs the submitted volume *entering the funnel* - that is, the total the
funnel is working through at the anchor - not a weekly submission rate. At this anchor
the application window has already closed, so there are no further submissions to
schedule; a volume counterfactual is the only meaningful form of that scenario.

---

## 2. Worked example: +10% submitted applications

This is the required reproducible example, computed from the anchor state above.

| Line | Submitted | Verified | Decisions | Admitted | **Enrolled** |
|---|---|---|---|---|---|
| Baseline projection | 3,001.0 | 2,481.0 | 2,441.0 | 1,118.0 | **686.0** |
| Scenario: submitted +10% | 3,301.1 | 2,729.1 | 2,685.1 | 1,229.8 | **754.6** |
| **Difference** | +300.1 | +248.1 | +244.1 | +111.8 | **+68.6** |

- **Baseline projected enrolment: 686.0**
- **Scenario projected enrolment: 754.6**
- **Absolute change: +68.6 enrolled**
- **Percentage change: +10.0%**

**Why the percentage change equals the shock exactly.** The projection is a chain of
multiplications, `E = S * r_verify * r_decision * r_admit * r_yield`. A 10% shock to
*any single factor* therefore moves `E` by exactly 10%, with the funnel contributing no
damping of its own. This is a property of the multiplicative form, not a finding about
AdmitFlow. The low absolute yield of this funnel is already inside the baseline; it does
not attenuate a *proportional* change on top of it.

The practical consequence is that this engine cannot rank the funnel stages by leverage.
Improving verification by 10% is worth exactly as much, in percentage terms, as
improving yield by 10%. Choosing between them requires knowing which is cheaper to move,
which is a question about operational cost, not about this funnel. See the leverage note
in section 3 and the limitations in section 6.

**Cross-reference against the trained forecast model.** The RandomForestRegressor from
`reports/forecast_results.md`, applied to the same anchor at H = 6, predicts
**885.1** cumulative enrolled for CYC-2025. The deterministic
projection gives 686.0, which is 199.1 lower (22.5% below the model).

The projection is the **lower** of the two, and the reason is measurable rather than
mysterious: enrolment yield is still maturing at the anchor. Across all 48
programme-cycles, mean `cum_enrolment_yield` rises from 0.0112 at the first eligible origin to 0.2745 at the last, and it
rises in **48/48** of them. A static rate reads that partially matured
yield and holds it flat, so it necessarily lands below a model that has learned the
maturation pattern. The cross-reference is a sanity check, not a validation of either
number.

---

## 3. Scenario grid - portfolio level

All scenarios share the same anchor state. Because the drain projection is
horizon-free, the shock applies to the funnel's tracked endpoint rather than to a
specific future week.

| Family | Shock | Submitted | Admitted | **Enrolled** | Abs change | % change | Clamped |
|---|---|---|---|---|---|---|---|
| A Application volume change | +10% | 3,301 | 1,230 | **755** | +69 | +10.0% | no |
| A Application volume change | -10% | 2,701 | 1,006 | **617** | -69 | -10.0% | no |
| B Verification conversion change | +10% | 3,001 | 1,230 | **755** | +69 | +10.0% | no |
| B Verification conversion change | -10% | 3,001 | 1,006 | **617** | -69 | -10.0% | no |
| C Admission conversion change | +10% | 3,001 | 1,230 | **755** | +69 | +10.0% | no |
| C Admission conversion change | -10% | 3,001 | 1,006 | **617** | -69 | -10.0% | no |
| D Enrolment yield change | +10% | 3,001 | 1,118 | **755** | +69 | +10.0% | no |
| D Enrolment yield change | -10% | 3,001 | 1,118 | **617** | -69 | -10.0% | no |

Baseline for comparison: submitted 3,001, admitted 1,118, **enrolled 686**.

**Reading the grid - an important structural result.** Every un-clamped row shows the
**same** percentage change in enrolled as its shock, and the same absolute change,
because `E = S * r_verify * r_decision * r_admit * r_yield` is a product of five
independent factors. Scaling any one of them by `(1 + delta)` scales `E` by exactly
`(1 + delta)`. This is not a coincidence in the data; it is forced by the arithmetic.

What *does* differ between the rows is **where the change lands**: scenario A moves the
Submitted column, scenario D leaves it untouched and moves only the tail of the chain.

The `Clamped` column is the only mechanism in this engine that could make one family a
weaker lever than another, since a conversion rate above 1.0 is impossible. **At this
anchor, no clamp binds** - not for the portfolio, and not for any of the
12 programmes, in either direction. Every rate sits far enough below
1.0 that a 10% shock stays inside the range. So at these shock sizes the four families
are exactly symmetric, and the grid should be read as *four ways of producing the same
percentage change*, not as a ranking.

**This is a limitation of the engine, not a finding about the funnel.** A real
admissions funnel breaks the symmetry in three ways, none of which is modelled here:

- **Capacity.** If a programme is near its seat limit, extra admitted volume cannot be
  absorbed. Here it cannot be used, because the dataset itself shows admissions running
  well past declared `base_seat_capacity`; the audit in `docs/ADMITFLOW_DATASET_HANDOFF.md`
  found admits at roughly 4.7x declared seats, so capacity is a planning attribute here,
  not a binding constraint. Imposing one would contradict the data.
- **Volume-quality interaction.** Marginal applicants typically convert worse than the
  early, self-selecting ones, so extra volume would not convert at the average rate.
  The engine assumes it does. Quantifying this would need an estimate of the
  marginal-applicant conversion rate that this dataset does not provide.
- **Rate maturation.** Yield climbs steeply through the cycle (section 2), so a shock
  applied to a mid-cycle rate does not persist the way a shock to a mature rate would.

The honest summary: **this engine quantifies where a change lands, not which stage is
worth attacking.** Ranking the stages needs cost and capacity information that is not
in this dataset.

---

## 4. Programme-level scenarios

Same engine, evaluated separately for each of the 12 programmes with a
fully defined conversion chain at the anchor. A +10% and a -10% shock are shown for
each family; the portfolio column repeats the aggregate for reference.

| Programme | Tier | Baseline enrolled | A +10% | A -10% | D (yield) +10% | D (yield) -10% |
|---|---|---|---|---|---|---|
| `PGM-01` | high | 48 | 53 (+10%) | 43 (-10%) | 53 (+10%) | 43 (-10%) |
| `PGM-02` | high | 59 | 65 (+10%) | 53 (-10%) | 65 (+10%) | 53 (-10%) |
| `PGM-03` | medium | 66 | 73 (+10%) | 59 (-10%) | 73 (+10%) | 59 (-10%) |
| `PGM-04` | medium | 53 | 58 (+10%) | 48 (-10%) | 58 (+10%) | 48 (-10%) |
| `PGM-05` | high | 28 | 31 (+10%) | 25 (-10%) | 31 (+10%) | 25 (-10%) |
| `PGM-06` | medium | 30 | 33 (+10%) | 27 (-10%) | 33 (+10%) | 27 (-10%) |
| `PGM-07` | emerging | 122 | 134 (+10%) | 110 (-10%) | 134 (+10%) | 110 (-10%) |
| `PGM-08` | medium | 65 | 72 (+10%) | 59 (-10%) | 72 (+10%) | 59 (-10%) |
| `PGM-09` | emerging | 93 | 102 (+10%) | 84 (-10%) | 102 (+10%) | 84 (-10%) |
| `PGM-10` | emerging | 48 | 53 (+10%) | 43 (-10%) | 53 (+10%) | 43 (-10%) |
| `PGM-11` | emerging | 27 | 30 (+10%) | 24 (-10%) | 30 (+10%) | 24 (-10%) |
| `PGM-12` | emerging | 47 | 52 (+10%) | 42 (-10%) | 52 (+10%) | 42 (-10%) |
| **PORTFOLIO** | - | 686 | 755 (+10%) | 617 (-10%) | 755 (+10%) | 617 (-10%) |

---

## 5. Acquisition channel and source

> ### ASSOCIATIONAL ONLY
> Everything in this section describes **association on a self-selected, first-touch
> population in synthetic data**. It is **not** a causal effect, not an uplift estimate,
> and not evidence that changing a channel would change enrolment. Applicants who
> arrive through a given channel differ systematically from those who do not, and this
> design cannot separate the channel from the applicant mix. **Do not use these
> numbers to justify reallocating marketing budget.**

### By acquisition channel, CYC-2025 (all applications at any stage)

| Channel | Applications | Admitted rate | Enrolled rate |
|---|---|---|---|
| `paid_search` | 1,382 | 0.1418 | 0.0926 |
| `organic_search` | 1,235 | 0.1806 | 0.1336 |
| `social_media` | 954 | 0.1478 | 0.1006 |
| `referral` | 788 | 0.1827 | 0.1371 |
| `email_campaign` | 758 | 0.1544 | 0.1135 |
| `direct` | 661 | 0.1861 | 0.1271 |
| `education_fair` | 572 | 0.1626 | 0.1101 |
| `partner_agency` | 569 | 0.1424 | 0.1037 |

### By acquisition source, CYC-2025 (top 8 by volume)

| Source | Applications | Admitted rate | Enrolled rate |
|---|---|---|---|
| `meta_ads_prospect` | 489 | 0.1493 | 0.0961 |
| `google_ads_brand` | 470 | 0.1468 | 0.1043 |
| `google_ads_generic` | 423 | 0.1277 | 0.0757 |
| `programme_page` | 319 | 0.1912 | 0.1317 |
| `content_blog` | 313 | 0.1917 | 0.1534 |
| `google_organic` | 308 | 0.1558 | 0.1136 |
| `bing_organic` | 295 | 0.1831 | 0.1356 |
| `newsletter_prospectus` | 262 | 0.1603 | 0.1298 |

These rates are computed over **all** applications in the cycle, including those that
never reached submission, so they are not comparable to the panel's
r_admit / r_yield figures. The gap between a channel's enrolled rate and the portfolio
average is a description of who applied through that channel, not an effect of the
channel itself.

---

## 6. Limitations

1. **These are simulations, not predictions.** Each row answers "what would follow if".
   Nothing here is a statement about what will happen, and no output should be quoted
   without that qualifier.
2. **No uncertainty.** The engine produces point arithmetic. It has no intervals, no
   residual error term and no stochastic component, so it understates real-world
   variation by construction. The forecast model in `reports/forecast_results.md` has
   a real MAE of several enrolments per horizon; the scenario engine has no equivalent.
3. **The engine cannot rank stages by leverage.** Because the projection is a product of
   five independent factors, a proportional shock to any one of them produces the same
   proportional change in enrolled. Capacity, volume-quality interaction and rate
   maturation all break this symmetry in a real funnel; none is modelled here, and
   section 3 explains why capacity could not honestly be used in this dataset. Do not
   read the scenario grid as advice about which stage to invest in.
4. **Rates are frozen at a mid-maturity value.** This is the engine's largest known
   bias, and it is one-directional: `cum_enrolment_yield` rises from 0.0112
   to 0.2745 across the eligible window, in 48 of 48
   programme-cycles. Holding the anchor value flat therefore **understates** the
   endpoint, and the gap against the model cross-reference in section 2 is the visible
   symptom. A version that extrapolates the yield trajectory would be more accurate but
   would be a forecast, not a scenario engine, and would need its own validation.
5. **One factor at a time.** Family A does not also change verification, and combined
   shocks are not modelled. The scenarios are deliberately independent sensitivities, not
   a joint distribution, and they are not additive.
6. **Linear shocks on a clamped quantity.** A +10% shock is linear until a conversion
   ratio would exceed 1.0, at which point it clamps and the reported change is smaller
   than +10% of the base. The grid's `Clamped` column records when this binds. It does
   not bind anywhere at the anchor or shock sizes used here, so the symmetry in
   limitation 3 is exact rather than approximate.
7. **Horizon-free.** The drain projection is not a time-phased path to any particular
   week. It answers where the funnel is currently tracking to. It therefore cannot be
   compared directly against a per-horizon forecast metric, and `H` appears in this
   report only to place the model cross-reference.
8. **Single anchor, single cycle.** Everything is anchored on one week of one cycle
   (the latest eligible origin of the most recent cycle). There is no distribution of
   outcomes across anchors, and an earlier anchor would give a very different - and
   much less mature - conversion state.
9. **Channel results are associational**, for the reasons given in section 5.
10. **Synthetic data.** The conversion rates being flexed are themselves generated by
    `scripts/generate_dataset.py`, so the engine demonstrates the *mechanics* of
    scenario analysis rather than producing decision-grade planning figures.
