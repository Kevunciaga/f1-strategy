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
2. **Tyre degradation model.** The model includes a tyre degradation model.
   - *Placeholder rule, puncture:* a tyre punctures when its degradation reaches 100%. The puncture is assumed to happen at the start/finish line, adds a fixed time penalty to that lap, and forces a pit stop at the end of that lap. The rule is a simplification and will be revisited once real data is used.
   - *Placeholder rule, forced stop:* the next planned stop is moved earlier to the puncture lap, keeping its planned compound. If no planned stop remains, the compound is chosen from the laps left: 10 or fewer soft, 20 or fewer medium, otherwise hard. A puncture on a planned pit lap is one stop. A puncture on the final lap causes no stop.
3. **Lap time responds to degradation.** Lap time increases as tyre degradation increases.
   - Degradation differs by compound. Softs drop off more sharply than mediums, which drop off more sharply than hards.
   - Fresh-tyre pace differs by compound. Softs are fastest on a fresh tyre, hards slowest.
   - All values are placeholders until real data is used.
4. **Fuel load model.** The model includes a fuel load model. The car gets lighter as fuel burns off, so lap time decreases as the race progresses.
5. **Pit stop and start time loss.** A pit stop costs an in-lap loss on the lap of the stop and an out-lap loss on the lap after it, measured per track. Lap 1 is slower than a normal lap because of the standing start, also measured per track. The values are in `src/track_params.py`. The time spent in the pit lane is already inside these losses, and is stored for information only.
6. **Race time output.** The model outputs a total race time based on the strategy and the resulting lap times, including any forced stops.

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
