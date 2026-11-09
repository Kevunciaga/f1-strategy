# f1-strategy

A Formula 1 race strategy project, built from scratch as a way to learn machine learning from the basics. It is treated as a tool for a real Formula 1 team, so it has to work on the current rules, not only on past seasons.

## Goals

1. **Predict race time from a strategy.** Given a strategy (pit laps and tyre compounds), accurately predict the time to complete the race. This includes races from 2026 onwards, run under the new regulations, not only the historical seasons the model is built from.
2. **Optimise the strategy.** Attach an optimiser that searches for the best strategy.
3. **Adapt strategy during a race.** Eventually allow dynamic adjustment of the strategy in response to race events such as Safety Car, Virtual Safety Car and Red Flags.

## Initial Numbered Targets

> **INITIAL.** This is the first time numbered targets are set. They are a starting point and will evolve as the project progresses.

Targets are tied to the goals above.

- **Goal 1 (INITIAL target):** Predict race time within 30 seconds of the real race data.
- **Goal 1, 2026 onwards (INITIAL target):** The same 30 second target on 2026 races, which the model never sees when it is fitted. Reported separately from the older seasons.
- **Goal 2:** No numbered target yet. See open questions below.

## Data Decisions

**2026-11-09: the per-track numbers use 2021 to 2025 only.**

- **Which numbers.** Lap 1 time loss, in-lap loss and out-lap loss per track (`src/track_params.py`). Each is the average over the dry races of that track from 2021 to 2025 where the number could be measured. That is often fewer than five races: wet races are excluded, and a red flag or Safety Car on lap 1 removes the lap 1 measurement. Monza has two usable races, and Silverstone only one for lap 1.
- **2026 is kept out of the averages.** 2026 races are measured separately. Adding them moved a stop by up to 1.8 s and a two-stop race total by up to 4.5 s (Monaco), with no common direction across tracks: Zandvoort went down, Monaco, Monza and Silverstone went up. With one 2026 race per track so far, that cannot yet be told apart from ordinary race-to-race variation. The 2026 regulation change may be part of the cause, but it is not proven.
- **2026 is a test set.** The 2026 races are used to check whether the numbers from 2021 to 2025 carry over to the new regulations. If they do not, the numbers are refitted on 2026 races once enough exist.
- **Not available.** No 2026 data loads for Jeddah. Wet races are excluded everywhere (see Other Factors).

## Functional Requirements

Requirements for the race time model (Goal 1). The optimiser (Goal 2) and in-race adaptation (Goal 3) will get their own requirements later.

1. **Strategy input.** The model takes a strategy as input: the starting tyre, and for each pit stop the lap number to pit on and the tyre compound to change to.
2. **Tyre degradation model.** The model includes a tyre degradation model. Each compound loses a fixed number of seconds per lap of tyre age, fitted from real lap data (see Fitted Values).
   - *Placeholder rule, puncture:* a tyre punctures at a set tyre age per compound (`puncture_age` in `src/params.py`). The puncture is assumed to happen at the start/finish line, adds a fixed time penalty to that lap, and forces a pit stop at the end of that lap. The puncture ages and the penalty are not fitted, because the data has too few punctures. The rule will be revisited later.
   - *Placeholder rule, forced stop:* the next planned stop is moved earlier to the puncture lap, keeping its planned compound. If no planned stop remains, the compound is chosen from the laps left: 10 or fewer soft, 20 or fewer medium, otherwise hard. A puncture on a planned pit lap is one stop. A puncture on the final lap causes no stop.
3. **Lap time responds to degradation.** Lap time increases with tyre age.
   - Degradation differs by compound. The data does not always show softs dropping off more sharply than mediums and hards: the order changes from race to race (see Fitted Values).
   - Fresh-tyre pace differs by compound, measured as an offset against the soft.
   - Degradation, compound offsets and the fuel effect are fitted from real data. The defaults in `src/params.py` are placeholders, used only by the tests and as a template for values that are not fitted.
4. **Fuel load model.** The model includes a fuel load model. The car gets lighter as fuel burns off, so lap time decreases as the race progresses. The fuel load and burn rate are fixed assumptions (110 kg at the start, 1.8 kg per lap). The time cost per kg is fitted from real data.
5. **Pit stop and start time loss.** A pit stop costs an in-lap loss on the lap of the stop and an out-lap loss on the lap after it, measured per track. Lap 1 is slower than a normal lap because of the standing start, also measured per track. The values are in `src/track_params.py`. The time spent in the pit lane is already inside these losses, and is stored for information only.
6. **Race time output.** The model outputs a total race time based on the strategy and the resulting lap times, including any forced stops.

## Fitted Values

**Method.** Each race is fitted on its own with least squares over every clean lap of every driver (`src/fit_params.py`). Clean laps exclude lap 1, in-laps and out-laps, deleted or inaccurate laps, and laps under Safety Car, VSC, red flag or yellow flags. The fitted equation is:

    lap time = driver pace + compound offset + degradation[compound] x tyre age + fuel effect x lap number

The fuel effect per lap is converted to seconds per kg with the 1.8 kg per lap burn rate. Tyre wear and fuel burn can only be told apart because pit stops reset tyre age but not fuel load. The fit is solved directly with the normal equation.

**Values.** Median over the 19 dry races from 2021 to 2025 that could be fitted, at Zandvoort, Barcelona, Jeddah, Monaco, Monza and Silverstone:

| | Soft | Medium | Hard |
|---|---|---|---|
| Degradation, seconds per lap of tyre age | 0.059 | 0.030 | 0.038 |
| Fresh-tyre offset against the soft, seconds | 0.00 | 0.28 | 0.13 |

- **Fuel effect:** 0.029 seconds per kg, close to the commonly quoted rule of thumb of 0.03.
- **Lap-to-lap noise:** 0.68 seconds per lap is left unexplained in a typical race.
- **Spread between races is large.** Degradation depends strongly on the track and the year. A few races give unrealistic values (for example Jeddah 2021 and Silverstone 2022, where few drivers ran some compounds). The median is shown, and used when combining races in the evaluation, because these races pull the mean far off: the mean medium degradation is slightly negative.
- **The offsets are not reliable yet.** In single races they are often not clearly different from zero, and the medians do not show the expected order (soft fastest, hard slowest).

## Results So Far

Tested with `src/evaluate.py`. Every race from 2021 to 2025 is predicted with tyre, fuel and per-track numbers from the other races only (leave-one-race-out). 2026 races are predicted with numbers from 2021 to 2025.

- **Races without Safety Car, VSC or red flag:** average error 6.3 seconds per driver, 97% of drivers within the 30 second target, worst miss 58.8 seconds.
- **Races with Safety Car, VSC or red flag laps:** misses of 100 seconds or more, because these events are not modelled yet (Goal 3). All 2026 races so far had such laps, so the 2026 target cannot be tested yet.
- **Known limit:** each driver's base pace is calibrated from their own clean laps in the race being predicted. Because of this, a baseline without any tyre or fuel model scores almost the same. A stricter test is planned that calibrates pace on part of the race and predicts the rest.

## Other Factors Affecting Lap Time (Considered, Deferred)

Brainstormed factors beyond the functional requirements above. None are in scope yet. Likely first candidates: base pace per track, and tyre warm-up. The start lap and the pit in-lap and out-lap losses are already measured per track, see Data Decisions.

- **Tyre:** warm-up phase on fresh tyres, tyre cliff, tyre temperature and pressure, new vs used set.
- **Track and weather:** track layout and length (sets base lap time), track and air temperature, rain and drying line, wind, track evolution (grip rises as rubber builds up).
- **Wet weather (deferred):** wet-weather tyres (intermediate and full wet compounds) and the effect of rain on lap time. Wet races are excluded from the data for now, and only dry compounds (soft, medium, hard) are modelled.
- **Car:** car performance and team strength, setup (downforce vs top speed), engine mode, energy deployment, car damage, component wear.
- **Driver:** skill and consistency, pace management (lifting and coasting to save tyres or fuel), mistakes and track limits.
- **Other cars and race state:** traffic and dirty air, DRS and slipstream, being lapped, track position, defending and attacking.
- **Race events:** Safety Car, VSC, red flag (see Goal 3), yellow flags, start and restart laps, out-lap and in-lap.
- **Rules:** team orders, mandatory tyre compounds, fuel flow limits and fuel saving.

## Open Questions

- **Goal 2, comparing across cars.** Cars differ in speed, so a strategy's predicted time cannot be compared fairly against other finishers' real times. Options: compare using one car/driver's pace, or measure the gain over that driver's real strategy instead of against other cars.
- **Goal 2, what "best" means.** The fastest predicted race time may not always be the objective. Sometimes the aim is damage limitation, such as the best expected finishing position or the least time lost. The objective function needs defining before a target can be set.
- **2026 regulations.** Once enough 2026 races exist, decide whether to refit the per-track numbers and the tyre and fuel parameters on 2026 data only, or on all years with an indicator for the regulation era.
