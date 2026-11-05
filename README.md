# f1-strategy

A Formula 1 race strategy project, built from scratch as a way to learn machine learning from the basics.

## Goals

1. **Predict race time from a strategy.** Given a strategy (pit laps and tyre compounds), accurately predict the time to complete the race.
2. **Optimise the strategy.** Attach an optimiser that searches for the best strategy.
3. **Adapt strategy during a race.** Eventually allow dynamic adjustment of the strategy in response to race events such as Safety Car, Virtual Safety Car and Red Flags.

## Initial Numbered Targets

> **INITIAL.** This is the first time numbered targets are set. They are a starting point and will evolve as the project progresses.

Targets are tied to the goals above.

- **Goal 1 (INITIAL target):** Predict race time within 30 seconds of the real race data.
- **Goal 2:** No numbered target yet. See open questions below.

## Functional Requirements

Requirements for the race time model (Goal 1). The optimiser (Goal 2) and in-race adaptation (Goal 3) will get their own requirements later.

1. **Strategy input.** The model takes a strategy as input: the starting tyre, and for each pit stop the lap number to pit on and the tyre compound to change to.
2. **Tyre degradation model.** The model includes a tyre degradation model.
3. **Lap time responds to degradation.** Lap time increases as tyre degradation increases.
   - *Deferred:* degradation differs by compound. Softs drop off more sharply than mediums, which drop off more sharply than hards.
4. **Fuel load model.** The model includes a fuel load model. The car gets lighter as fuel burns off, so lap time decreases as the race progresses.
5. **Race time output.** The model outputs a total race time based on the strategy and the resulting lap times.

## Other Factors Affecting Lap Time (Considered, Deferred)

Brainstormed factors beyond the functional requirements above. None are in scope yet. Likely first candidates: base pace per track, and out-lap/in-lap effects.

- **Tyre:** compound grip level, warm-up phase on fresh tyres, tyre cliff, tyre temperature and pressure, new vs used set.
- **Track and weather:** track layout and length (sets base lap time), track and air temperature, rain and drying line, wind, track evolution (grip rises as rubber builds up).
- **Car:** car performance and team strength, setup (downforce vs top speed), engine mode, energy deployment, car damage, component wear.
- **Driver:** skill and consistency, pace management (lifting and coasting to save tyres or fuel), mistakes and track limits.
- **Other cars and race state:** traffic and dirty air, DRS and slipstream, being lapped, track position, defending and attacking.
- **Race events:** Safety Car, VSC, red flag (see Goal 3), yellow flags, start and restart laps, out-lap and in-lap.
- **Rules:** team orders, mandatory tyre compounds, fuel flow limits and fuel saving.

## Open Questions

- **Goal 2, comparing across cars.** Cars differ in speed, so a strategy's predicted time cannot be compared fairly against other finishers' real times. Options: compare using one car/driver's pace, or measure the gain over that driver's real strategy instead of against other cars.
- **Goal 2, what "best" means.** The fastest predicted race time may not always be the objective. Sometimes the aim is damage limitation, such as the best expected finishing position or the least time lost. The objective function needs defining before a target can be set.
