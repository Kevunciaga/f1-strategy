# F1 Strategy — Roadmap

Goal: learn ML from scratch, using F1 tyre/race strategy as the vehicle.
Each phase adds one idea. Don't skip ahead.

## Phase 0 — Rule-based baseline (no ML)
- [x] Constant health decay, one compound (`simple_tyre_model.py`)
- [x] Per-compound constant wear rate
- [ ] Hand-written non-linear wear curve (e.g. wear speeds up late in stint) — still no data, no fitting, just a formula you pick by feel

## Phase 1 — Real data, no fitting yet
- [ ] Pull real lap data via FastF1 for one race
- [ ] Clean it: drop out-laps, in-laps, SC/VSC laps, outliers
- [ ] Plot raw lap time vs tyre age — just look at it, no model

## Phase 2 — First ML model: linear regression
- [ ] Fit `lap_time = a + b * age` by hand (least squares, normal equations)
- [ ] Refit same thing with gradient descent — watch loss (MSE) drop
- [ ] Compare hand-rolled result to `numpy.polyfit` / `sklearn.LinearRegression`

## Phase 3 — Evaluating a model properly
- [ ] Train/test split (e.g. train on laps 1-40, test on 41+, or split by stint)
- [ ] RMSE on train vs test — spot overfitting
- [ ] Residual plot — is the line missing a pattern?

## Phase 4 — Non-linear regression
- [ ] Try polynomial features (degree 2, 3) with linear regression
- [ ] Try the physics-informed curve (warm-up + linear + cliff) via `scipy.curve_fit`
  — this is what `tyre_model.py` already does; revisit it now that the basics make sense
- [ ] Compare polynomial vs physics curve: fit quality, extrapolation behavior

## Phase 5 — More features
- [ ] Add compound as a feature (categorical/one-hot)
- [ ] Add track/session as a feature
- [ ] Multivariate regression across compounds/tracks at once

## Phase 6 — Model comparison & regularization
- [ ] Ridge/Lasso — what regularization does and why
- [ ] Cross-validation instead of one train/test split
- [ ] Try a tree-based model (Random Forest or Gradient Boosting) — compare to regression

## Phase 7 — Race simulator upgrades
- [ ] Fuel load effect on pace (car gets faster as fuel burns off)
- [ ] Realistic pit loss (already have a constant — make it track-specific)
- [ ] Safety car / VSC probability model

## Phase 8 — Strategy optimization
- [x] Brute-force search over pit lap + compound (`race_sim.py`)
- [ ] Monte Carlo simulation — run each strategy N times with random SC events, compare distributions not just averages
- [ ] (stretch) Dynamic programming or simple RL for strategy choice

## Phase 9 — Stretch goals
- [ ] Driver-specific pace/degradation models
- [ ] Uncertainty quantification (confidence intervals on predictions)
- [ ] Multi-car race simulation (overtakes, traffic)

---
Current position: **Phase 0, last item** (hand-written non-linear curve) — or skip straight
to Phase 1 if you'd rather get to real data and real ML sooner.
