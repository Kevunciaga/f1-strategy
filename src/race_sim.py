import fastf1
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

import fastf1

# enable caching (important)
fastf1.Cache.enable_cache("cache")

# load session
session = fastf1.get_session(2023, "Monza", "R")
session.load()

# Verstappen laps
laps = session.laps.pick_drivers("VER")

# Convert to seconds
lap_times = laps["LapTime"].dropna()

lap_times_sec = lap_times.dt.total_seconds()
print(lap_times_sec.head())
lap_times_sec.sort_values()

# Average Lap Time
base_lap_time = lap_times_sec[:round(0.1*len(lap_times_sec))].mean()


print("Base lap:", base_lap_time)

def simulate_race(base_lap_time, num_laps, pit_laps, compound):

    total_time = 0
    tyre_age = 0
    pit_num = 1
    current_compound = compound[pit_num]
    for lap in range(1, num_laps + 1):
        
        # defining lap time
        lap_time = base_lap_time

        # pit stop
        if lap in pit_laps:
            lap_time += 20
            tyre_age = 0
            current_compound = compound[pit_num]
            pit_num += 1

        
        # degradation
        if current_compound == 'soft':
            degradation = 0.1 * tyre_age
        elif current_compound == 'medium':
            degradation = 0.06 * tyre_age
        elif current_compound == 'hard':
            degradation = 0.02 * tyre_age
        lap_time += degradation
        tyre_age += 1

        # adding time to total_time
        total_time += lap_time

    return total_time

max_race_time = simulate_race(base_lap_time, 50, (10, 40), ('medium', 'medium', 'medium'))
print(round(max_race_time))
print(f'Total time is {round(max_race_time//3600)}:{round((max_race_time%3600))//60}:{round(max_race_time%60)}')