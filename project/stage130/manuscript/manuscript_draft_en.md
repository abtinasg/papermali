# Incremental Information and Its Practical Limits in Point-in-Time Corporate Financial-Distress Prediction: Evidence from the Tehran Stock Exchange

## Structured Abstract

**Problem.** Corporate financial-distress prediction in emerging and frontier markets is usually reported under conditions that make its practical value hard to judge: outcome labels are constructed retrospectively, predictors are drawn from statements that were not yet public at the moment prediction is claimed to occur, and evaluation splits are random rather than temporal. The resulting performance figures answer a question no user of such a model ever faces. This study asks a narrower and more answerable question: in a genuinely point-in-time, leakage-safe design, how much information do successive blocks of data actually add, and what are the practical limits of that information when the outcome is rare?

**Design.** We construct one-year-ahead company-year prediction pairs for firms listed on the Tehran Stock Exchange. The outcome is an audited three-state composite operational indicator of financial distress, in which missing evidence is never coded as healthy. Predictors enter only if they would have been available at the prediction cutoff under a fixed four-month regulatory information-availability assumption. Validation is strictly forward-chaining on the fiscal target year, with no shuffling and no random split. A prespecified nested block architecture (financial, market, macroeconomic, audit and governance) was to be evaluated incrementally on paired predictions. The primary metric, PR-AUC, the full metric set, the model configuration and the operating threshold were all fixed before the held-out years were opened.

**Final Test.** The final evaluation years were temporally held out throughout development and were opened exactly once. The evaluation set contained 346 evaluable company-year rows across 119 unique companies, and **only 12 positive observations** were present in it. The prevalence of the outcome in this set was 0.03468208092485549, which we report separately from the discrimination results.

**Results.** On the held-out Final Test the model achieved a PR-AUC of 0.243879669979 (95% cluster-bootstrap CI 0.053272572767–0.541675572242). This interval is wide and its lower bound lies close to the prevalence, so this single evaluation does not establish a precise effect size. As a secondary metric, ROC-AUC was 0.907684630739 (95% CI 0.787834897749–0.97144045144); under severe class imbalance ROC-AUC is less informative about positive-class retrieval and must be read alongside the primary PR-AUC. The observed Brier score on raw, unrecalibrated predicted probabilities was 0.071625345916 (95% CI 0.053164118058–0.092580775647); calibration was not fully assessed. At the pre-specified operating threshold of 0.426878838687, derived from pooled development out-of-fold predictions only, the confusion counts were TP 8, FP 43, TN 291, FN 4. Screening the top decile of predicted risk yielded Recall@10% of 0.666666666667 and Lift@10% of 6.407407407407, both point estimates for which no confidence interval is available.

**Incremental blocks.** Of the prespecified incremental blocks beyond the financial baseline, the market block showed approximately null observed development evidence and was retained on architectural rather than performance grounds; the confirmatory macroeconomic block was never admitted because point-in-time availability could not be established; and the audit-and-governance block was prespecified but not admitted because the available data did not provide adequate coverage and did not satisfy the frozen feature definitions. The corresponding prespecified comparisons were therefore not executed, no p-values were computed, and no inferential conclusion is drawn for them.

**Conclusion.** In a point-in-time, leakage-safe design on a small, severely imbalanced sample, a parsimonious regularized model built on financial-statement information produced a ranking signal, while the additional data blocks that a richer specification would require could not be shown to add information within the constraints of the available evidence. The width of the primary interval and the small number of positive observations mean these results describe what one locked evaluation observed, not a settled level of performance.

## Keywords

financial distress prediction; point-in-time design; data leakage; temporal validation; class imbalance; precision–recall; Tehran Stock Exchange; emerging markets; regularized logistic regression; reproducible predictive modelling

---

## 1. Introduction

The prediction of corporate financial distress is one of the oldest continuously active empirical problems in accounting and finance. From the univariate ratio comparisons of [@beaver1966] and the multivariate discriminant model of [@altman1968] through the conditional-probability formulations of [@ohlson1980] and [@zmijewski1984] to hazard-based [@shumway2001] and market-augmented [@campbell2008] specifications, the literature has accumulated a large stock of models and an equally large stock of reported performance figures. More recently, flexible machine-learning estimators have been applied to the same problem [@barboza2017; @jones2017], and comprehensive reviews have documented how heterogeneous the field has become in its definitions, sampling schemes and feature construction [@sun2014].

What has accumulated less quickly is comparability. Reported performance in this literature depends on choices that are frequently made after the outcome is known: which firms count as distressed, which fiscal years enter the estimation set, when the predictor information is assumed to have become available, and how the evaluation sample was separated from the estimation sample. Each of these choices can move headline performance substantially, and several of them can move it in ways that cannot be reproduced by anyone who has to make a prediction in real time. The concern is not new, but it is structural: a model that is estimated and evaluated on information that was not yet public when the prediction is nominally made will report a figure that no prospective user can attain [@kaufman2012].

This study is organised around that gap rather than around the search for a better estimator. Our central question is not which algorithm ranks highest on a held-out sample, but how much information successive blocks of data actually contribute once the design is made genuinely point-in-time and leakage-safe, and what the practical limits of that contribution are when the outcome is rare. This reframing matters because the two questions have different answers and different policy implications. An algorithm leaderboard tells a reader which estimator won on one sample; an incremental-information design tells a reader whether an additional and often costly data source is worth acquiring at all.

The empirical setting is the Tehran Stock Exchange, a market in which the question is sharpened by two features. First, corporate disclosure follows a Jalali fiscal calendar and a regulatory filing regime, so the moment at which annual financial-statement information becomes usable for prediction is not the fiscal year-end but a later, regulated date; ignoring that gap is one of the most direct routes to optimistic bias. Second, the market is small enough that severe class imbalance and low absolute event counts are not incidental nuisances but binding constraints on what any study can credibly claim. Existing Iranian evidence has typically identified distressed firms through the legal mechanism of Article 141 of the Iranian Commercial Code, under which accumulated losses exceeding half of capital trigger a statutory decision on continuation or dissolution [@salehi2016; @tarighi2022]. That legal event is informative but it is also late, sparse and administratively mediated, which motivates the separate operational outcome we describe in Section 8.

We make four design commitments and report their consequences honestly, including where they are unfavourable. First, the outcome is a three-state composite in which unknown evidence is recorded as unknown rather than as health. Second, predictors are admitted only if a fixed regulatory availability assumption places them before the prediction cutoff. Third, validation is forward-chaining on the fiscal target year, and the final evaluation years were held out and opened exactly once, after the metric set, the model configuration and the operating threshold were fixed. Fourth, the incremental blocks are reported as they resolved, including the blocks that were never admitted; a prespecified comparison that could not be executed is reported as prespecified and not executed rather than quietly removed.

The contribution is therefore evidential rather than algorithmic. We provide one fully specified, leakage-controlled, single-pass evaluation of a parsimonious model in an emerging-market setting, together with an explicit account of how far the additional information blocks could and could not be taken. We do not claim superiority over any comparator, we do not claim that the observed performance is stable, and we do not claim readiness for deployment. What we do claim is that the design permits the reader to see exactly what was measured and under what constraints.

## 2. Literature Review and Conceptual Motivation

### 2.1 From ratios to conditional probabilities

The classical strand of the distress literature established that accounting ratios carry information about subsequent failure. [@beaver1966] compared failed and non-failed firms on individual ratios; [@altman1968] combined ratios into a discriminant score; [@ohlson1980] and [@zmijewski1984] reframed the problem as the estimation of a conditional probability and drew early attention to the sampling and selection issues that arise when failures are rare and non-randomly observed. [@shumway2001] showed that static single-period models discard information relative to a hazard formulation, and [@campbell2008] extended the predictor set with market-based variables. This line of work is the source of the financial-ratio block we use as the baseline specification.

### 2.2 Machine learning and the leaderboard problem

A second strand applies flexible estimators to the same task. [@barboza2017] and [@jones2017] compare a range of statistical and machine-learning frameworks for bankruptcy prediction, and the review by [@sun2014] documents how definitions, sampling and feature construction vary across this literature. The methodological difficulty is that comparisons across estimators are informative only if everything else is held fixed, which in practice it rarely is. [@breiman2001] framed the underlying tension between model-based and algorithmic cultures, and [@shmueli2010] made explicit the distinction between explanatory and predictive modelling that this literature often blurs. [@rudin2019] argues further that in high-stakes settings interpretable models should be preferred where they are adequate, rather than treated as a fallback.

Our design responds to this by removing the leaderboard from the centre of the paper. The algorithm family and configuration were locked before the held-out years were opened, and the not-selected algorithm families are reported as not selected, not as inferior.

### 2.3 Emerging and frontier markets

Distress prediction in emerging markets faces smaller samples, shorter reliable histories and more variable disclosure. [@altman2005] proposed an emerging-market adaptation of the classical scoring approach, and [@altman2017] provides a broad international assessment of how the classical model performs across countries. For the Iranian market specifically, [@salehi2016] applied several data-mining classifiers to Tehran Stock Exchange firms, identifying distressed firms through Article 141 of the Iranian Commercial Code, and [@tarighi2022] uses financial-distress risk in the same institutional setting. These studies establish both the relevance of the question and the practical difficulty of the data environment.

### 2.4 Class imbalance and the choice of primary metric

When the positive class is rare, the choice of evaluation metric is not cosmetic. [@davis2006] established the formal relationship between precision–recall and ROC space and showed that dominance in one does not imply dominance in the other, and [@saito2015] demonstrated that the precision–recall plot is the more informative of the two when classes are severely imbalanced. This is the basis for our prespecification of PR-AUC as the primary metric with ROC-AUC as a secondary one. Probability quality is a separate question again: the Brier score [@brier1950] is a proper scoring rule [@gneiting2007], but a single score is not a calibration assessment, and [@steyerberg2010] and [@vancalster2019] set out how much more is required before a model's probabilities can be described as calibrated. Rare-event settings additionally distort maximum-likelihood estimation in ways documented by [@king2001], and the sample-size requirements for developing a reliable binary prediction model are considerably more demanding than event counts of the order available here [@riley2019].

### 2.5 Leakage, temporal validation and reproducibility

[@kaufman2012] provides the general taxonomy of leakage in data mining and the practical point that leakage is usually introduced by the construction of the analysis table rather than by the estimator. [@bergmeir2012] examines cross-validation for temporally ordered data and the conditions under which random splitting is inappropriate. Reporting standards for prediction models [@collins2015] and the broader reproducibility literature [@peng2011] motivate the artifact-level provenance we describe in Section 18. Where resampling is used to characterise uncertainty, the bootstrap [@efron1979] must respect the dependence structure of the data; with repeated observations on the same firm, clustering is the relevant adjustment [@cameron2015].

### 2.6 Conceptual motivation for an incremental design

Taken together, these strands motivate a design in which the unit of scientific interest is the *block* rather than the *model*. If a financial-statement block is available at low cost and a market, macroeconomic or governance block is available only at high cost or with unresolved availability semantics, the practically relevant question is what the additional block adds on the same sample, the same temporal split and the same paired predictions. This is the question our prespecified nested architecture was built to answer, and Section 12 reports what happened when it met the data.

## 3. Institutional Context of the Tehran Stock Exchange

Three features of the Iranian institutional setting shape the design directly.

**The fiscal calendar.** Iranian companies report on a Jalali fiscal calendar. All fiscal years in this study are therefore stated in Jalali form: development target years 1393–1399 and final-test target years 1400–1402. We report these years as they appear in the frozen design rather than restating them in a converted calendar, because the mapping between the two calendars is a design parameter in this project and not a cosmetic relabelling.

**Regulated disclosure and the availability lag.** Annual financial-statement information does not become usable for prediction at the fiscal year-end. It becomes usable when it is filed and disclosed, which occurs later. Because row-level publication timestamps were not collected for the full panel, this study applies a fixed regulatory-lag assumption of four Jalali months: an annual statement for fiscal year *t* is treated as available only from four Jalali months after the fiscal year-end. This is a methodological assumption about regulatory practice, not an observed publication-time claim for any individual filing, and Section 16 records the limitation this creates.

**The legal distress mechanism.** Iranian empirical work has commonly labelled a firm as distressed by reference to Article 141 of the Iranian Commercial Code; [@salehi2016] operationalises that criterion as accumulated losses exceeding half of equity and selects the study sample on that basis, and financial-distress risk is used in the same institutional setting by [@tarighi2022]. That criterion identifies a legally consequential condition, but it is administratively mediated, sparse and recognised late relative to the deterioration it reflects. As Section 5 explains, our primary outcome deliberately does not equate distress with the legal condition: an accumulated-loss criterion enters only as one component of a broader operational composite, and a stricter accumulated-loss-only definition is retained separately as a robustness target rather than as the primary outcome.

## 4. Data and Sample

The analysis operates on company-year pairs constructed for one-year-ahead prediction: predictor information for fiscal year *t* is aligned to an outcome observed for target year *t+1*. The company universe consists of firms listed on the Tehran Stock Exchange for which researcher-verified annual financial data were frozen before any modelling began; the financial data were verified and frozen, and no re-extraction was performed at any later stage.

The temporal design partitions company-year pairs on the target year. Development uses target years 1393–1399; the final evaluation uses target years 1400–1402 and was untouched throughout development. Within development, validation is forward-chaining across two locked folds: the first trains on target years 1393–1395 and validates on 1396–1397; the second trains on target years 1393–1397 and validates on 1398–1399. Neither random splitting nor shuffling was authorised at any point.

The development fit set used for the final model comprises 666 company-year rows, of which 68 are positive and 598 are negative. The held-out evaluation set comprises 346 evaluable company-year rows across 119 unique companies, of which 12 are positive and 334 are negative. The prevalence of the outcome in the evaluation set is 0.03468208092485549. These counts are the operative constraint on everything reported below: they are small in absolute terms and severely imbalanced, and no analysis in this paper is capable of overcoming that.

Table 1 records the cohort and temporal design in full.

## 5. Financial-Distress Target Construction

The outcome is `FD_target_main`, a composite operational indicator of financial distress evaluated for the target year. It is deliberately distinguished from legal insolvency. It is built from criteria that are each evaluated in three states — positive, negative, or unknown — and then aggregated.

The component criteria are:

1. **Accumulated loss relative to registered capital.** Positive if the ratio of accumulated loss to registered capital reaches or exceeds one half; negative if it is below one half; unknown if registered capital is missing or non-positive, or if accumulated loss is missing. This is the accounting condition that corresponds most closely to the legal criterion discussed in Section 3.
2. **Negative equity.** Positive if equity is below zero; negative if equity is at or above zero; unknown if equity is missing.
3. **Negative operating cash flow combined with high leverage.** Positive if operating cash flow is negative *and* the ratio of total liabilities to total assets exceeds 0.70; definitely negative if operating cash flow is known to be non-negative *or* leverage is known not to exceed 0.70; unknown otherwise.
4. **Direct Article-141 evidence.** Defined in the target contract but unobserved for every row in the panel, because no verified controlled source for it existed in the frozen data.

Aggregation follows a modified three-valued disjunction: the composite is positive if any evaluable criterion is definitely positive; negative if all evaluable criteria are definitely negative; and unknown otherwise. Criteria that are entirely unobserved across the panel — in practice, the direct Article-141 criterion — are excluded from the aggregation so that a wholly unavailable source cannot block an otherwise definite negative conclusion.

Two properties of this construction matter for interpretation. First, **missingness is never silently coded as health.** A company-year whose evidence does not permit a determination is recorded as unknown and is excluded from target-specific analyses, rather than being counted as a non-distressed observation. This is a conservative choice: it reduces the sample but prevents an unknown from inflating the negative class. Second, **the composite is not an Article-141 target.** A stricter Article-141-only definition, and a persistent-loss variant, are retained as separate robustness targets. Conflating the operational composite with the legal event would misstate what is being predicted.

## 6. Point-in-Time Predictor Architecture

The predictor architecture is designed so that every feature value used to predict target year *t+1* would have been available to a user at the prediction cutoff.

The final model uses nine financial-statement features, in a locked order: `log_total_assets`, `leverage_ratio`, `current_ratio`, `roa_period_adjusted`, `ocf_to_assets_period_adjusted`, `asset_turnover_period_adjusted`, `operating_margin_period_adjusted`, `financial_expense_to_assets_period_adjusted` and `accumulated_loss_to_capital_ratio`. These cover size, capital structure, short-term liquidity, accrual and cash-flow profitability, asset productivity, operating margin, financing burden and accumulated losses. A tenth candidate, revenue growth, was excluded before modelling because its coverage in the first fold's training window fell below the prespecified minimum; it was retained in the coverage audit rather than deleted, and no denominator exception was granted to rescue it.

Availability is enforced by the four-month rule described in Section 3. A predictor row is admitted to the leakage-safe analysis table only where the assumed regulatory availability date for fiscal year *t* falls strictly before the fiscal year-end of the target year *t+1*. Company-years that fail this condition remain on the audited-pairs surface for transparency but do not enter the analysis-ready table.

Missing predictor values are handled with a pre-imputation missingness mask: for each of the nine features, a binary indicator records whether that feature was missing for that row before imputation, and the indicator is constructed from the row's own pre-imputation missing positions rather than inferred after imputation. The design matrix therefore carries eighteen columns — nine imputed continuous features and nine binary missingness indicators — in a fixed order. Continuous features are standardised; missingness indicators are left unstandardised and binary. All preprocessing parameters — clipping bounds, imputation medians and standardisation means and standard deviations — were estimated on the development fit set only and were applied verbatim to the held-out rows; nothing was re-estimated on the evaluation set.

## 7. Leakage-Safe Temporal Validation and Empirical Design

Random splitting was not used, and shuffling was not authorised. The reason is specific rather than stylistic. Company-year observations in this panel are ordered in time and correlated within firms, and the prediction task is prospective: information from later target years must not inform a model that is evaluated on earlier ones, and information from any target year must not inform the model that is evaluated on the held-out years. A random split violates both conditions simultaneously, and in a panel with repeated observations on the same firm it additionally allows the same company to appear on both sides of the split. Under these conditions the standard concerns about cross-validation for temporally dependent data apply directly [@bergmeir2012], and the general mechanism by which analysis-table construction introduces optimistic bias is well documented [@kaufman2012].

The empirical design therefore proceeds in three separated stages.

**Development.** Model families and configurations were compared under the locked forward-chaining folds, on the primary sample and target, with all preprocessing fitted inside the training fold only. Class weighting was the primary imbalance strategy; synthetic minority oversampling [@chawla2002] was admitted only as an in-training-fold robustness check and never as part of the primary specification.

**Locking.** The metric set, the model family and configuration, the feature order and the operating threshold were fixed and committed before the held-out years were opened. The operating threshold was derived from pooled development out-of-fold predictions under an F2-maximising rule with a higher-threshold tie-break; it was not derived from, and was never re-derived on, the held-out data.

**Final Test.** The held-out target years were opened exactly once. The locked model was applied, not fitted: no estimator was trained on the held-out rows, no hyperparameter search or feature search was executed, no threshold search was performed, no recalibration or isotonic fitting was applied, and no model, block, algorithm or configuration was re-selected on any quantity computed from the held-out data.

Uncertainty for the aggregate metrics is characterised by a paired bootstrap clustered on the company identifier, with percentile-based 95% intervals. Clustering is necessary because the same firm contributes multiple company-year rows, and treating those rows as independent would understate uncertainty [@cameron2015; @efron1979].

Figure 1 presents the study timeline and the leakage-safe design; Figure 2 presents the model-development workflow.

## 8. Development and Robustness Evidence

Development compared regularized logistic regression, random forest and gradient-boosted trees under the locked folds. The observed primary development ordering placed regularized logistic regression ahead of random forest, and random forest ahead of gradient boosting. We state this ordering as an observation on development out-of-fold predictions. It is not a significance test, and it was not used to make an inferential claim about relative model quality.

Six prespecified robustness categories were then executed, each changing exactly one dimension of the design while holding the rest fixed:

1. an alternative target-proximity feature set (feature-set dimension);
2. an alternative listing-rule sample (sample dimension);
3. an expanded company-scope sample (sample dimension);
4. a combined expanded sample (sample dimension);
5. a persistent-loss variant of the outcome (target dimension);
6. synthetic minority oversampling applied inside training folds only (imbalance-strategy dimension).

The observed development ordering was preserved in categories 2 through 6. Category 1, the target-proximity six-feature set, is the sole exception: under that reduced feature set the observed ordering reversed.

Three interpretive constraints apply to this evidence and are maintained throughout the paper. First, these six analyses are **sensitivity evidence only**. They characterise how the observed development picture responds to specified perturbations; they do not demonstrate generalisation. Second, they are **not a model-selection exercise**: no winner was selected on this evidence, and no retained design was frozen on the basis of it. Third, the fact that one category reverses the ordering is reported as it stands rather than set aside; it indicates that the observed ordering is contingent on the feature set, which is precisely the kind of contingency a robustness analysis exists to reveal.

The final model family and configuration — regularized logistic regression with an L2 penalty at C = 0.1, on the financial block — were fixed by an explicit decision taken on the pre-locked development evidence, before the held-out years were opened. That decision was a governance act, not an inferential result: no superiority test supported it, and the algorithm families that were not selected retain their standing and are not described here as rejected or inferior.

Table 5 records the robustness categories and the block dispositions discussed in the next section.

## 9. Incremental Information Blocks M2–M4 and Their Dispositions

The prespecified architecture nested four blocks: a financial baseline (M1), a market block (M2), a macroeconomic block (M3) and an audit-and-governance block (M4). Each block was to be admitted only after passing a data gate, and each increment was to be evaluated on the same common sample, the same temporal split and paired predictions. The prespecified confirmatory family of comparisons was {M2 − M1, M3 − M2, M4 − M3}, with Holm multiplicity control. We report what happened to each block, including where the answer is negative or unresolved.

**M2 — market block.** The market block was defined on returns, realised volatility and an illiquidity measure over a pre-cutoff window. Its data-admission gate initially failed and, following an adjudication of trading-calendar semantics and a design freeze of the return construct, was re-executed once and passed on coverage. A paired, development-only comparison of the market block against the financial baseline was then executed on the common sample under the locked folds. The observed evidence was approximately null: all three paired-bootstrap intervals for the difference in the primary metric included zero, and the signs of the point estimates disagreed across model families. The block was subsequently retained by an explicit decision as the intermediate element of the nested architecture, so that the prespecified chain would remain intact for a later comparison. That retention was made on architectural grounds and explicitly not on the basis of observed predictive superiority: no improvement in prediction is claimed for the market block, and no statistical significance is asserted for it.

**M3 — macroeconomic block (confirmatory).** The confirmatory macroeconomic block was defined on inflation, official exchange-rate change and a policy financing rate. Its data gate was executed and terminated in an unresolved state: point-in-time availability of the required series could not be established from an authoritative source, and a set of blocking evidential questions remained open at the close of the gate. The approved reporting of this disposition is as follows. The macroeconomic block was prespecified, but its executed data gate remained unresolved because point-in-time availability could not be established. The block was therefore not admitted to modelling. Consequently, the corresponding comparison against the market block was not executed, no p-value was computed, and no inferential conclusion is drawn for it.

**A supplementary exploratory macro analysis.** Separately from the confirmatory block, a strictly supplementary and exploratory analysis was carried out using two lagged international macroeconomic indicators. Its coverage gate passed, and a paired incremental evaluation against the retained market block was executed on development data only. The result was null: no detectable incremental contribution to the primary metric was observed, with all paired intervals including zero. This analysis is reported as supplementary exploratory evidence only. It is not confirmatory, it does not enter the prespecified multiplicity family, and it is neither a substitute nor a proxy for the confirmatory macroeconomic block. Two evidential limitations attach to it and are not resolved: the availability of the underlying series at any past moment was never established, so the lag does not convert revised data into point-in-time data; and the exchange-rate feature is degenerate over the most recent constructible years, where the underlying official rate is repeated unchanged and the transformed feature is therefore defined but identically zero.

**M4 — audit and governance block.** The audit-and-governance block was defined on four candidates: audit opinion type, a going-concern flag, audit lag in days and board size. Its contract was locked prospectively but was never complete: the taxonomy for audit opinion type and the calendar-conversion convention for audit lag both remained unresolved as definitional questions, and a cross-cutting identity problem meant that no audited deterministic mapping resolved a filing-system issuer identity to the frozen company key used throughout the study. The formal data gate was therefore never executed. The approved reporting of this disposition is as follows. The audit-and-governance block was prespecified but was not admitted to modelling because the available data did not provide adequate coverage and did not satisfy the frozen feature definitions. Consequently, the corresponding comparison was not executed, no p-value was computed, and no inferential conclusion is drawn for it.

**Consequence for the confirmatory family.** Because two of the three prespecified comparisons were never executed, the confirmatory family is incomplete and its multiplicity adjustment is deferred. No confirmatory inference is reported anywhere in this paper: no p-value was computed, no multiplicity procedure was executed, and no hypothesis in the family was accepted or rejected. The unexecuted comparisons are reported as prespecified and not executed rather than removed from the analysis plan, so that the record of what was planned is preserved alongside the record of what was achievable.

## 10. Locked Final Test Results

The held-out target years 1400–1402 were opened exactly once, after the model, the metric set and the operating threshold had been fixed. The locked model was applied to 346 evaluable company-year rows across 119 unique companies. **Only 12 positive observations were present in the Final Test**, against 334 negative observations. All results in this section are reported as computed.

### 10.1 Primary metric

On the held-out Final Test the model achieved a PR-AUC of 0.243879669979 (95% cluster-bootstrap CI 0.053272572767–0.541675572242). The Final Test prevalence was 0.03468208092485549, which we report as a separate descriptive property of the evaluation set.

The accompanying limitation is integral to the result rather than a caveat appended to it: the interval is wide and its lower bound lies close to the prevalence, so this single evaluation does not establish a precise effect size. A reader should treat the point estimate as the centre of a broad range that this evaluation was not powered to narrow.

### 10.2 Secondary metrics

ROC-AUC was 0.907684630739 (95% CI 0.787834897749–0.97144045144). We report the number only. Under severe class imbalance ROC-AUC is less informative about positive-class retrieval and must be interpreted alongside the pre-specified primary PR-AUC [@davis2006; @saito2015]; the divergence between the two figures in this evaluation is a direct illustration of why the primary metric was prespecified as PR-AUC.

The observed Brier score on raw, unrecalibrated predicted probabilities was 0.071625345916 (95% CI 0.053164118058–0.092580775647). No recalibration and no isotonic fitting were applied at any point, so the reported probabilities are the raw outputs of the locked pipeline. **Calibration was not fully assessed.** A single proper score at a low event rate is not a calibration assessment [@gneiting2007; @vancalster2019]; no calibration curve, slope or intercept was computed, and no statement that the model is well calibrated is made or implied.

### 10.3 Operating point

At the pre-specified operating threshold 0.426878838687, derived from pooled development out-of-fold predictions only, the confusion counts were TP 8, FP 43, TN 291, FN 4. The threshold was fixed before Final Test access and was not re-derived afterwards; it is not described as optimal or tuned, and no alternative threshold was searched on the held-out data. Table 3 records the operating point and its derivation rule.

### 10.4 Top-decile screening

Under a top-decile screening rule applied within each target year, with the number selected in year *y* defined as the ceiling of one tenth of that year's evaluable rows, 36 rows were selected in total and 8 of the 12 positives were captured. Recall@10% was 0.666666666667 and Lift@10% was 6.407407407407. Both are **point estimates, and no confidence interval is available for either**; none was computed, and none should be inferred. Pooled precision among the selected rows was 0.2222222222222222. Per-year capture counts were 3 of a selected 12 in target year 1400, 4 of 12 in 1401 and 1 of 12 in 1402, from year sizes of 112, 116 and 118 evaluable rows respectively. These per-year counts rest on very few events and support no stability claim in either direction; in particular, the variation across the three years is not evidence of a trend. The selection fraction was fixed in advance and was not optimised after the results were seen. Table 4 records the screening design and outcomes.

### 10.5 What this section does not report

No ROC curve, precision–recall curve, calibration curve, decision curve, net-benefit quantity, subgroup analysis or per-year performance curve is presented. Their absence is deliberate: each would require either row-level access to the held-out predictions beyond the single authorised pass or a new scientific computation, and neither was performed. The reader should not interpret their absence as an omission.

## 11. Model Interpretation

The locked model is a regularized logistic regression with an L2 penalty at C = 0.1, estimated on the development fit set only. The L2 penalty shrinks coefficients toward zero in the manner introduced for the linear case by [@hoerl1970], which is why the estimates below are described as regularized rather than as unbiased maximum-likelihood estimates. Table 6 reports the intercept and the eighteen coefficients together with the corresponding odds ratios, in the model's own locked term order.

Interpretation is subject to three constraints that we state before the substance.

First, the coefficients are **regularized conditional associations**. They are penalised, and each is conditional on the remaining terms in the model. They are not causal effects, and nothing in this design licenses a causal reading [@shmueli2010]. Second, the terms appear in the locked model order, which is deliberately **not** an importance ranking; reordering them by magnitude would create the appearance of a ranking that the design does not support. Third, no confidence interval, standard error, p-value or significance marker accompanies any coefficient, because none exists in the locked artifact and none was computed. No coefficient in this paper is described as significant.

On the scale of the reported odds ratios, standardised continuous features are expressed per one-standard-deviation increase, with the standardising mean and standard deviation shown for each row of Table 6; the binary missingness indicators are expressed for indicator = 1 versus 0.

Reading Table 6 in its locked order, the continuous terms whose coefficients are positive — that is, associated with a higher predicted probability of the composite outcome — are the leverage ratio, the current ratio, asset turnover, operating margin and the accumulated-loss-to-capital ratio. The continuous terms whose coefficients are negative are log total assets, return on assets, cash-flow-to-assets and the financial-expense-to-assets term. We describe these as directional groupings only, and deliberately do not rank the terms within either group: the model order is not an importance order, and no quantity in the locked artifact would support ranking them. The direction of the leverage and accumulated-loss terms is consistent with the accounting content of the composite outcome, two of whose three evaluable criteria are defined on accumulated losses and on a joint cash-flow-and-leverage condition; readers should therefore note that part of this association reflects the construction of the outcome rather than an independent empirical discovery.

Two terms deserve explicit comment because they are easy to over-read. The current-ratio and operating-margin coefficients carry the opposite sign to the one a simple univariate intuition would suggest. In a penalised model with correlated accounting ratios, conditional signs need not match marginal ones, and we draw no substantive conclusion from either.

Regarding the missingness indicators: **six of the nine missingness-indicator coefficients are exactly zero in the locked model, and three are non-zero.** The three non-zero indicators are those for cash-flow-to-assets, operating margin and financial-expense-to-assets. This pattern is reported descriptively. It establishes neither statistical significance nor a general claim that missingness is informative; under an L2 penalty an exactly zero coefficient is a property of this fitted artifact and not a test result, and no inference about the informativeness of missing data should be drawn from it.

Figure 3 presents the coefficient plot in locked term order.

## 12. Discussion

The results support a narrow reading and resist a broad one, and the distinction between the two is the substantive contribution of this paper.

**What the evaluation shows.** A parsimonious regularized model built on nine point-in-time financial-statement features produced a ranking of held-out company-years under which the top-decile screening rule captured 8 of the 12 positives, alongside the aggregate figures reported in Section 10. For a practitioner whose problem is to order a list of companies for further scrutiny rather than to assign a calibrated probability to each, this is the relevant kind of evidence.

**What it does not show.** It does not show that the model performs at the level of the point estimate. The primary interval spans a range wide enough that materially different levels of performance are compatible with what was observed, and the lower bound lies close to the prevalence. It does not show that the model is calibrated, because calibration was not fully assessed. It does not show stability, because there is no second evaluation against which stability could be examined, and the per-year capture counts are far too small to speak to it. It does not show superiority over any comparator, because no comparative test was executed on the held-out data and no confirmatory inference was performed anywhere in the study.

**The divergence between the two discrimination metrics.** The gap between the PR-AUC and the ROC-AUC figures in Section 10 is instructive rather than anomalous. At the prevalence reported in Section 10.1, a ranking can separate positives from the bulk of negatives well enough to produce a comparatively high ROC-AUC while still placing enough negatives above positives to keep precision low across much of the recall range. This is exactly the behaviour that motivated the prespecification of PR-AUC as primary [@davis2006; @saito2015], and it is a concrete argument against reporting ROC-AUC alone in imbalanced distress applications — a practice that remains common in this literature.

**The incremental-information result.** The most consequential finding of this study is arguably negative. The market block, which was actually admitted and actually evaluated, produced approximately null development evidence. The confirmatory macroeconomic block could not be admitted at all, because point-in-time availability could not be established from an authoritative source. The audit-and-governance block could not be admitted because coverage was inadequate and because the definitional and identity questions that its features require were never resolved. A supplementary exploratory macro analysis, run on lagged revised international indicators, was likewise null.

The reading we take from this is not that market, macroeconomic or governance information is uninformative about corporate distress. It is that, in this setting, the *point-in-time availability* of those blocks — not their conceptual relevance — was the binding constraint. A research design that acquires such data retrospectively, without establishing what was knowable at the prediction cutoff, will not encounter this constraint and will therefore not report it. Making the constraint visible is, in our view, more useful to a reader deciding whether to invest in a data source than another performance figure would be.

**Relation to prior work.** The classical financial-ratio strand [@beaver1966; @altman1968; @ohlson1980; @zmijewski1984] supplies the baseline block that carried the signal here. Market-augmented specifications [@shumway2001; @campbell2008] motivated the block that produced a null in this setting. Emerging-market adaptations [@altman2005; @altman2017] and prior Iranian work [@salehi2016; @tarighi2022] establish the relevance of the question in this market; our contribution relative to that work is not a higher headline figure but a design in which the availability of every input is enforced and every prespecified comparison is accounted for, including the ones that could not be run. Where the machine-learning strand [@barboza2017; @jones2017] has tended toward comparative evaluation across estimators, we have deliberately locked the estimator and moved the comparison to the data blocks; readers interested in interpretable models for high-stakes decisions will recognise the trade-off we accepted [@rudin2019].

**Practical implications, stated conservatively.** For a user in this market, the evidence is consistent with using a parsimonious financial-ratio model as a screening aid that orders companies for human review, provided that the ordering is treated as a prioritisation device rather than as a probability statement, and that the user does not rely on the specific level of performance observed here. Nothing in this paper establishes readiness for deployment, and nothing in it supports an investment or credit decision taken on the model's output alone.

## 13. Limitations

The limitations below are material, and several of them bound the interpretation of the headline results directly.

**Only 12 positive observations were present in the Final Test.** This is the single most important constraint in the study. Twelve events cannot support precise estimation of any performance quantity, and every interval reported in Section 10 reflects that. The required sample sizes for developing reliable binary prediction models are far larger than what was available here [@riley2019], and rare-event settings additionally distort estimation in ways that a larger sample would mitigate [@king2001].

**The primary interval is wide.** The 95% cluster-bootstrap interval for PR-AUC spans from 0.053272572767 to 0.541675572242. Its lower bound lies close to the Final Test prevalence of 0.03468208092485549. This single evaluation therefore does not establish a precise effect size, and any use of the point estimate that ignores the interval will overstate what was learned.

**Calibration was not fully assessed.** A single Brier score computed at a low event rate on raw, unrecalibrated probabilities does not constitute a calibration assessment [@vancalster2019]. No calibration curve, slope or intercept was estimated, and no recalibration was performed. The predicted probabilities should not be treated as calibrated risks.

**Recall@10% and Lift@10% are point estimates without intervals.** No uncertainty quantification is available for either, and per-year capture counts rest on very few events. The variation across the three held-out years supports no claim of stability or instability.

**The four-month availability rule is an assumption, not an observation.** Row-level publication timestamps were not collected for the panel, so the fixed four-Jalali-month regulatory lag is a methodological assumption about when annual statements become usable. If actual filing behaviour departs from that assumption for a material subset of companies, the leakage-safe filter will have been either too permissive or too conservative for those rows. The direction of the resulting bias is not established by this study.

**The outcome is an operational composite, not a legal event.** `FD_target_main` is constructed from accounting criteria, only one of which corresponds to the Article-141 legal condition. Results should not be read as predicting legal insolvency proceedings, and comparison with Iranian studies that label distress via Article 141 alone [@salehi2016] is therefore not like-for-like.

**Two of three prespecified confirmatory comparisons were never executed.** The confirmatory family is incomplete and its multiplicity adjustment is deferred. No confirmatory inference of any kind is reported. The unexecuted comparisons are limitations of the evidence base, not null findings.

**The supplementary exploratory macro analysis carries unresolved evidential problems.** The point-in-time availability of the underlying indicators was never established; the source data are current revised values, and a one-year lag does not convert revised data into point-in-time data. In addition, the exchange-rate feature is degenerate over the most recent constructible years, where the official rate is repeated unchanged so the transformed feature is defined but identically zero. Coverage adequacy for that block is therefore not a statement about its information content.

**Sample and market scope.** The study covers one exchange, a limited number of companies and a limited number of fiscal years. Generalisation to other markets, to unlisted firms or to later periods is not supported by this evidence.

**Robustness evidence is sensitivity evidence.** The six robustness categories vary one design dimension at a time on development data. They do not demonstrate generalisation, and one of the six reversed the observed development ordering.

**Single evaluation.** The held-out years were opened exactly once and may not be reopened. This protects the integrity of the reported figures, but it also means there is no second observation of performance in this study, and the reported figures cannot be checked against a further pass.

**Test-suite scope.** The reproducibility apparatus described in Section 18 carries a set of accepted historical failures arising from earlier-stage boundary conditions. We do not claim that the full repository test suite passes.

## 14. Conclusion

This study evaluated a parsimonious regularized model for one-year-ahead corporate financial-distress prediction on the Tehran Stock Exchange, under a design in which the outcome admits an explicit unknown state, every predictor is filtered by an availability rule, validation is strictly forward-chaining, and the held-out years were opened exactly once after the metric set, the model and the operating threshold had been fixed.

On that single locked evaluation the model achieved a PR-AUC of 0.243879669979, with a wide 95% cluster-bootstrap interval whose lower bound lies close to the prevalence; ROC-AUC, reported as a secondary metric, was 0.907684630739. Only 12 positive observations were present in the evaluation set. Top-decile screening captured 8 of those 12 positives. Calibration was not fully assessed.

Of the prespecified information blocks beyond the financial baseline, the one that could be admitted and evaluated produced approximately null development evidence, and the remaining two could not be admitted at all — one because point-in-time availability could not be established, the other because coverage and feature definitions could not be satisfied. The prespecified comparisons for those two were not executed, and no inferential conclusion is drawn for them.

The appropriate conclusion is a restrained one. In this market and under these constraints, financial-statement information admitted on a genuine point-in-time basis supported a usable ranking of companies, while the additional data blocks that a richer specification would require could not be shown to add information within the limits of the evidence available. The precision of the reported performance is low, and the practical limit encountered was the availability of information rather than the choice of estimator. Establishing whether these findings hold more widely would require larger event counts, a second independent evaluation, and data sources whose availability at the prediction cutoff can be verified rather than assumed.

## 15. Reproducibility and Data/Code Availability

The analysis is organised so that every reported value is traceable to a committed artifact that is pinned by a SHA-256 digest.

**Single-pass discipline.** The held-out evaluation was executed once. The executor script was frozen and hashed before the held-out data were accessed; its digest is `d85234ee4c7e2b14dc21084348a059fceb083cf8bcc0ecbf30ee64eef79c56a4`. Twenty-one fail-closed controls (FT01–FT21) were evaluated during that pass and all passed. They verified, among other things, that the accepted refit artifacts matched their pinned digests, that the runtime and package versions matched the development environment, that the evaluation cohort contained zero development rows, that the design matrix columns matched the locked model exactly and in order, that preprocessing parameters were taken verbatim from the development artifact rather than re-estimated, that missingness indicators were derived from each row's own pre-imputation missing positions, that no estimator was trained during the pass, that the threshold was read from the committed development artifact rather than derived, that exactly one pass occurred, that no recalibration or isotonic fitting was executed, that no model or configuration was re-selected, and that the locked development results were byte-identical before and after.

**Provenance of reported values.** All numeric values in this manuscript are drawn from a frozen manuscript evidence package containing six result tables, a coefficient and odds-ratio table, three schematic figures and a claim freeze that pins each claim to a source artifact and an exact committed value. The accompanying `claim_traceability_matrix.csv` in this directory records, for every quantitative claim in the manuscript, the section in which it appears, the canonical source path, the field or row within that source, the exact committed value and the SHA-256 digest of the source file.

**Model artifacts.** The locked model coefficients and the preprocessing parameters are committed at `project/stage129/full_development_refit_execution/`, with digests `48faab1ef186206508385713fb3b885a88a55bb072fb586d56e63d2777c97690` and `862c65ec37082be1e3e95c29d2bf8873df9105e90cc43ce1ecac4fd8901ba9f6` respectively. The aggregate evaluation metrics are committed at `project/stage129/final_test_execution/stage129_final_test_metrics.json`, digest `0b1ea6c086430d6ecc65432c8001cc3b028422e7c1293a9ea2fb6c44d7ef4392`. The operating threshold is committed at `project/stage129/threshold_derivation_attempt3/stage129_threshold_value_attempt3.json`, digest `9b8a7d799616eb12d6e70a6dcf623ff1a636b4ec4b1bde37c21116252876b534`. The temporal split contract is committed at `project/stage125/part4_temporal_split_contract_stage125.json`, digest `3f6ff8c7adf77295e558045e5bcaa391b5d2c10e7be0a89aeb0c8ac2dd0463b9`.

**Superseded outputs.** An earlier-generation report tree exists in the repository under `project/outputs/09_report/`. It was produced by a pipeline that predates the leakage-safe dataset, the tuning lock, the accepted refit and the single authorised evaluation, and it describes a different sample and a different analysis. It is preserved unmodified for audit history and is explicitly non-citable; no value in this manuscript derives from it.

**Software.** Analyses were implemented in Python using scikit-learn [@pedregosa2011]. The runtime and package versions were pinned and verified during the single evaluation pass.

**Test suite.** The repository test suite carries a set of accepted historical failures that originate in earlier-stage boundary conditions and that predate this manuscript. They were not repaired as part of this work, and we make no claim that the full suite passes.

**Data availability.** The frozen analysis artifacts, contracts, gate decisions, metric records and provenance manifests are committed in the project repository. Raw evidence bundles for the supplementary exploratory macroeconomic retrieval are deposited in a public archival repository under version DOI `10.5281/zenodo.21844636` (concept DOI `10.5281/zenodo.21844635`). Company-level source financial data are researcher-verified and frozen; their redistribution is governed by the terms under which they were obtained.

## 16. References

Machine-readable entries are provided in `references.bib`; per-entry verification status, including DOI resolution, is recorded in `reference_audit.csv`. Every in-text citation resolves to an entry below, and every entry below is cited in the text.

Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. *The Journal of Finance*, 23(4), 589–609. https://doi.org/10.1111/j.1540-6261.1968.tb00843.x

Altman, E. I. (2005). An emerging market credit scoring system for corporate bonds. *Emerging Markets Review*, 6(4), 311–323. https://doi.org/10.1016/j.ememar.2005.09.007

Altman, E. I., Iwanicz-Drozdowska, M., Laitinen, E. K., & Suvas, A. (2017). Financial distress prediction in an international context: A review and empirical analysis of Altman's Z-score model. *Journal of International Financial Management & Accounting*, 28(2), 131–171. https://doi.org/10.1111/jifm.12053

Barboza, F., Kimura, H., & Altman, E. (2017). Machine learning models and bankruptcy prediction. *Expert Systems with Applications*, 83, 405–417. https://doi.org/10.1016/j.eswa.2017.04.006

Beaver, W. H. (1966). Financial ratios as predictors of failure. *Journal of Accounting Research*, 4, 71. https://doi.org/10.2307/2490171

Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. *Information Sciences*, 191, 192–213. https://doi.org/10.1016/j.ins.2011.12.028

Breiman, L. (2001). Statistical modeling: The two cultures (with comments and a rejoinder by the author). *Statistical Science*, 16(3), 199–231. https://doi.org/10.1214/ss/1009213726

Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. *Monthly Weather Review*, 78(1), 1–3. https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2

Cameron, A. C., & Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. *Journal of Human Resources*, 50(2), 317–372. https://doi.org/10.3368/jhr.50.2.317

Campbell, J. Y., Hilscher, J., & Szilagyi, J. (2008). In search of distress risk. *The Journal of Finance*, 63(6), 2899–2939. https://doi.org/10.1111/j.1540-6261.2008.01416.x

Chawla, N. V., Bowyer, K. W., Hall, L. O., & Kegelmeyer, W. P. (2002). SMOTE: Synthetic minority over-sampling technique. *Journal of Artificial Intelligence Research*, 16, 321–357. https://doi.org/10.1613/jair.953

Collins, G. S., Reitsma, J. B., Altman, D. G., & Moons, K. G. M. (2015). Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD): The TRIPOD statement. *BMJ*, 350, g7594. https://doi.org/10.1136/bmj.g7594

Davis, J., & Goadrich, M. (2006). The relationship between precision-recall and ROC curves. In *Proceedings of the 23rd International Conference on Machine Learning — ICML '06* (pp. 233–240). ACM Press. https://doi.org/10.1145/1143844.1143874

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *The Annals of Statistics*, 7(1), 1–26. https://doi.org/10.1214/aos/1176344552

Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. *Journal of the American Statistical Association*, 102(477), 359–378. https://doi.org/10.1198/016214506000001437

Hoerl, A. E., & Kennard, R. W. (1970). Ridge regression: Biased estimation for nonorthogonal problems. *Technometrics*, 12(1), 55–67. https://doi.org/10.1080/00401706.1970.10488634

Jones, S., Johnstone, D., & Wilson, R. (2017). Predicting corporate bankruptcy: An evaluation of alternative statistical frameworks. *Journal of Business Finance & Accounting*, 44(1–2), 3–34. https://doi.org/10.1111/jbfa.12218

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining. *ACM Transactions on Knowledge Discovery from Data*, 6(4), 1–21. https://doi.org/10.1145/2382577.2382579

King, G., & Zeng, L. (2001). Logistic regression in rare events data. *Political Analysis*, 9(2), 137–163. https://doi.org/10.1093/oxfordjournals.pan.a004868

Ohlson, J. A. (1980). Financial ratios and the probabilistic prediction of bankruptcy. *Journal of Accounting Research*, 18(1), 109. https://doi.org/10.2307/2490395

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research*, 12(85), 2825–2830. https://www.jmlr.org/papers/v12/pedregosa11a.html

Peng, R. D. (2011). Reproducible research in computational science. *Science*, 334(6060), 1226–1227. https://doi.org/10.1126/science.1213847

Riley, R. D., Snell, K. I. E., Ensor, J., Burke, D. L., Harrell, F. E., Jr., Moons, K. G. M., & Collins, G. S. (2019). Minimum sample size for developing a multivariable prediction model: PART II — binary and time-to-event outcomes. *Statistics in Medicine*, 38(7), 1276–1296. https://doi.org/10.1002/sim.7992

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. *Nature Machine Intelligence*, 1(5), 206–215. https://doi.org/10.1038/s42256-019-0048-x

Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLOS ONE*, 10(3), e0118432. https://doi.org/10.1371/journal.pone.0118432

Salehi, M., Mousavi Shiri, M., & Bolandraftar Pasikhani, M. (2016). Predicting corporate financial distress using data mining techniques: An application in Tehran Stock Exchange. *International Journal of Law and Management*, 58(2), 216–230. https://doi.org/10.1108/IJLMA-06-2015-0028

Shmueli, G. (2010). To explain or to predict? *Statistical Science*, 25(3), 289–310. https://doi.org/10.1214/10-STS330

Shumway, T. (2001). Forecasting bankruptcy more accurately: A simple hazard model. *The Journal of Business*, 74(1), 101–124. https://doi.org/10.1086/209665

Steyerberg, E. W., Vickers, A. J., Cook, N. R., Gerds, T., Gonen, M., Obuchowski, N., Pencina, M. J., & Kattan, M. W. (2010). Assessing the performance of prediction models. *Epidemiology*, 21(1), 128–138. https://doi.org/10.1097/EDE.0b013e3181c30fb2

Sun, J., Li, H., Huang, Q.-H., & He, K.-Y. (2014). Predicting financial distress and corporate failure: A review from the state-of-the-art definitions, modeling, sampling, and featuring approaches. *Knowledge-Based Systems*, 57, 41–56. https://doi.org/10.1016/j.knosys.2013.12.006

Tarighi, H., Nourbakhsh Hosseiny, Z., Abbaszadeh, M. R., Zimon, G., & Haghighat, D. (2022). How do financial distress risk and related party transactions affect financial reporting quality? Empirical evidence from Iran. *Risks*, 10(3), 46. https://doi.org/10.3390/risks10030046

Van Calster, B., McLernon, D. J., van Smeden, M., Wynants, L., & Steyerberg, E. W. (2019). Calibration: The Achilles heel of predictive analytics. *BMC Medicine*, 17(1), 230. https://doi.org/10.1186/s12916-019-1466-7

Zmijewski, M. E. (1984). Methodological issues related to the estimation of financial distress prediction models. *Journal of Accounting Research*, 22, 59. https://doi.org/10.2307/2490859

## 17. Table and Figure Callouts

**Table 1 — Cohort and temporal design.** Development and final-test target years, the two locked forward-chaining validation folds, the split variable, the prohibition on random splitting and shuffling, development fit-set counts, and evaluation-set counts including positives, negatives, unique companies and prevalence. Source: `manuscript_results_tables/table_1_cohort_and_temporal_design.csv`. Cited in Sections 4 and 7.

**Table 2 — Final Test aggregate performance.** PR-AUC as the primary metric with its 95% cluster-bootstrap interval, followed by ROC-AUC, Brier score, Recall@10% and Lift@10% as secondary metrics, with interval availability indicated per metric. Source: `manuscript_results_tables/table_2_final_test_aggregate_performance.csv`. Cited in Section 10.

**Table 3 — Operating point and confusion matrix.** The pre-specified threshold, the rule and tie-break used to derive it, the statement that it was derived from pooled development out-of-fold predictions only, and the four confusion counts. Source: `manuscript_results_tables/table_3_operating_point_confusion_matrix.csv`. Cited in Section 10.3.

**Table 4 — Top-decile screening.** The selection definition and fraction, per-target-year evaluable counts, selected counts and captured positives, pooled selected rows, pooled captured and total positives, pooled precision among selected rows, the record that the selection size was not optimised after results were seen, and the two point estimates marked as having no interval. Source: `manuscript_results_tables/table_4_top10_percent_screening.csv`. Cited in Section 10.4.

**Table 5 — Robustness categories and block dispositions.** The observed primary development ordering, the categories in which it was preserved and the single exception, the classification of the robustness evidence as synthesis only, and the records that no retained design and no winner were selected on this evidence. Source: `manuscript_results_tables/table_5_robustness_and_block_dispositions.csv`. Cited in Sections 8 and 9.

**Table 6 — Model coefficients and odds ratios.** The intercept and eighteen coefficients in locked term order, with term type, effect scale, coefficient, odds ratio, standardising mean and standard deviation for continuous terms, and interpretation class. No standard error, confidence interval, p-value or significance marker appears in this table because none exists in the locked artifact. Source: `manuscript_results_tables/table_6_model_coefficients_and_odds_ratios.csv`. Cited in Section 11.

**Figure 1 — Study timeline and leakage-safe design.** Schematic of the fiscal-year timeline, the four-month availability assumption, the prediction cutoff, the forward-chaining development folds and the held-out evaluation years. Source: `manuscript_figures/figure_1_study_timeline_and_leakage_safe_design.svg`. Cited in Section 7.

**Figure 2 — Model development workflow.** Schematic of the development, locking and single-pass evaluation stages, showing the separation between the data used for tuning, the data used for threshold derivation and the held-out data. Source: `manuscript_figures/figure_2_model_development_workflow.svg`. Cited in Section 7.

**Figure 3 — Coefficient plot.** The locked coefficients in model term order, on the log-odds scale, without error bars, since no interval exists for any coefficient in the locked artifact. Source: `manuscript_figures/figure_3_coefficient_plot.svg`. Cited in Section 11.

All tables and figures are reproduced by reference from the frozen manuscript evidence package. Their scientific contents were not regenerated, recomputed or duplicated with newly calculated values for this manuscript.
