# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "numpy",
#     "pandas",
#     "pathlib",
#     "re",
#     "scipy",
# ]
# ///

import math
from typing import Optional, List
import pandas as pd

# Define epsilon for floating point comparison
epsilon = 1e-9
ACCELERATION_RATE = 291.0
TARGET_SPEED = 50000.0
RUNTIME = 36000

# Helper function for fuzzy comparison (similar to qFuzzyCompare)
def fuzzy_compare(a, b):
    return abs(a - b) < epsilon * max(abs(a), abs(b), 1.0)

def calc_omega2t(start_omega2t, start_speed, start_time, target_speed, t, accel_rate: Optional[float] = None):
    """
    Calculate omega2t (omega^2 * t integral) for a given time point.

    Args:
        start_omega2t: Omega2t from the previous speed step
        start_speed: Speed in rpm from the previous speed step
        start_time: Time the previous speed step ended and the new speed step started
        target_speed: Speed to reach in this speed step
        t: Time to calculate omega2t for
        accel_rate: Acceleration rate in rpm/s for this speed step

    Returns:
        omega2t at time t, or -1.0 on error
    """


    # If t is equal to start_time return the start omega2t
    if fuzzy_compare(start_time, t):
        return start_omega2t

    # If t is smaller than start_time, return -1.0
    if t < start_time:
        return -1.0

    # Convert rpm to rad/s
    RPM2RadPS = math.pi / 30.0

    # Relative time in the speed step [s]
    relative_time = t - start_time
    accel_duration = None
    # If acceleration is needed, check that accel_rate is not zero
    if accel_rate is None and fuzzy_compare(target_speed, start_speed):
        accel_rate = 0.0
        accel_duration = relative_time
    elif accel_rate is None:
        accel_duration = t - start_time
        accel_rate = (target_speed - start_speed) / accel_duration


    # Duration of the acceleration [s]
    if accel_duration is None and accel_rate and not fuzzy_compare(accel_rate, 0.0):
        accel_duration = (target_speed - start_speed) / accel_rate

    if accel_duration is None or accel_duration < 0.0:
        return -1.0

    omega2t = start_omega2t

    # For the time T = min(accel_duration, relative_time) the omega2t can be calculated
    # Integral from 0 to T (start_speed + accel_rate * t)^2 dt
    # = Integral from 0 to T (start_speed)^2 dt <- Contribution of the previous speed
    # + Integral from 0 to T (2 * start_speed * accel_rate * t) dt <- Contribution of the previous speed changing
    # + Integral from 0 to T (accel_rate * t)^2 dt <- Contribution of the acceleration

    T = min(accel_duration, relative_time)

    # Add the contribution of the previous speed
    omega2t += (start_speed * RPM2RadPS) ** 2 * T

    # Add the contribution of the previous speed changing
    omega2t += start_speed * RPM2RadPS * accel_rate * RPM2RadPS * (T ** 2)

    # Add the contribution of the acceleration
    omega2t += (accel_rate * RPM2RadPS) ** 2 * (T ** 3) / 3.0

    # If the relative time extends beyond the acceleration duration, the omega2t can be calculated
    # Integral from accel_duration to relative_time (target_speed)^2 dt
    omega2t += (target_speed * RPM2RadPS) ** 2 * max(0.0, relative_time - accel_duration)

    return omega2t

def calc_acceleration(
        scan_speed: float,
        scan_time: float,
        scan_omega2t: float
) -> List[float]:

    # Constants
    K_RPM_TO_RAD_PER_SEC = math.pi / 30.0  # convert rpm to rad/s
    K_T1_FACTOR = 3.0 / 2.0  # (3.0 / 2.0)


    # Convert to angular speed and compute omega^2
    omega_at_target = scan_speed * K_RPM_TO_RAD_PER_SEC  # rad/s
    omega_squared = omega_at_target ** 2

    # =====================================================================
    # For the first speed step, we compute "t1", the end of the initial
    # acceleration zone, using
    #   "t2"   , the time in seconds for the first scan;
    #   "w2t"  , the omega^2_t integral for the first scan time;
    #   "w2"   , the omega^2 value for the constant zone speed;
    #   "tfac" , a factor (==(3/2)==1.5) derived from the following.
    #   "acc"  , the acceleration rate in radians/s^2
    #   "rpm"  , the target/set speed in rpm
    # The acceleration zone begins at t0=0.0.
    # It ends at time "t1".
    # The time between t1 and t2 is at constant speed.
    # The time between 0 and t1 is at changing speeds averaging (rpm/2).
    # For I1 and I2, the omega^2t integrals at t1 and t2,
    #                    ( I2 - I1 ) = ( t2 - t1 ) * w2       (equ.1)
    #                             I1 = acc^2 * t1^3 / 3       (equ.2)
    #                            rpm = acc * t1 * 30 / PI
    #                             I1 = ( rpm * PI / 30 )^2 * t1 / 3
    #                             w2 = ( rpm * PI / 30 )^2
    #                             I1 = ( w2 / 3 ) * t1
    #                             I2 = w2t
    # Substituting into equ.1, we get:
    #  ( w2t - ( ( w2 / 3 ) * t1 ) ) = ( t2 - t1 ) * w2
    #  t1 * ( w2 - ( w2 / 3 ) )      = t2 * w2 - w2t
    #  t1 * ( 2 / 3 ) * w2           = t2 * w2 - w2t
    #                            t1  = ( 3 / 2 ) * ( t2 - ( w2t / w2 ) )
    # =====================================================================
    if scan_speed == 0.0:
        return [0.0, 0.0]
        
    t1w = scan_omega2t / omega_squared
    accel_end = K_T1_FACTOR * (scan_time - t1w)  # seconds
    if accel_end == 0.0:
        return [0.0, 0.0]
    accel_rate = scan_speed / accel_end  # rpm/s

    return [accel_rate, accel_end]


# Calculate omega2t values and store in DataFrame
def calculate_and_store_omega2t():
    # Initialize lists to store values
    times = []
    speeds = []
    omega2ts = []

    current_speed = 0.0
    current_omega2t = 0.0
    current_time = 0.0

    # Calculate values for each second
    for t in range(RUNTIME + 1):
        times.append(t)
        current_omega2t = calc_omega2t(current_omega2t, current_speed, current_time,
                               TARGET_SPEED, float(t), ACCELERATION_RATE)
        omega2ts.append(current_omega2t)

        if t > 0:
            # Update speed based on acceleration
            if current_speed < TARGET_SPEED:
                current_speed = min(current_speed + ACCELERATION_RATE, TARGET_SPEED)
        speeds.append(current_speed)
        current_time = t

    # Create DataFrame
    df = pd.DataFrame({
        'Time': times,
        'Speed': speeds,
        'Omega^2t': omega2ts
    })
    return df


# load dataframe
data = pd.read_csv(r"C:\Users\Lukas\PycharmProjects\us3utils\SystemStatusDataOptima1Run2424.csv")
rows = [row for index, row in data.iterrows()]
calculated_omega2t = []
calculated_accel_rate = []
calculated_accel_end = []
calc_calculated_accel_rate = []
calc_calculated_accel_end = []
calc_omega2t_diff = []
calculated_omegasquaredt = []
# iterate over all rows of the dataframe and perform the calculations
for index, row in enumerate(rows):
    if index == 0:
        calculated_omega2t.append(0.0)
        calc_omega2t_diff.append(0.0)
        calculated_accel_rate.append(0.0)
        calculated_accel_end.append(0.0)
        calc_calculated_accel_rate.append(0.0)
        calc_calculated_accel_end.append(0.0)
        calculated_omegasquaredt.append(0.0)
        continue
    # calculate omega2t
    omega2t = calc_omega2t(calculated_omega2t[index-1], rows[index-1]['RPM'], rows[index-1]['ExperimentTime'], row['RPM'],
                           row['ExperimentTime'])
    calculated_omega2t.append(omega2t)
    calc_omega2t_diff.append(omega2t - row["OmegaSquaredT"])
    calculated_omegasquaredt.append(calc_omega2t(0.0, 0.0, 0.0, TARGET_SPEED, row['ExperimentTime'], ACCELERATION_RATE))
    #if row['ExperimentTime'] < 180:
    #    calculated_accel_rate.append()
    #    calc_calculated_accel_rate.append(0.0)
    #    calculated_accel_end.append(0.0)
    #    calc_calculated_accel_rate.append(0.0)
    #    calc_calculated_accel_end.append(0.0)
    #    continue
    # calculate acceleration rate and end time
    accel_rate, accel_end = calc_acceleration(row['RPM'], row['ExperimentTime'], row['OmegaSquaredT'])
    if accel_end > row['ExperimentTime']:
        accel_rate = (row['RPM'])/(row['ExperimentTime'])
    calculated_accel_rate.append(accel_rate)
    calculated_accel_end.append(accel_end)
    accel_rate, accel_end = calc_acceleration(row['RPM'], row['ExperimentTime'], omega2t)
    calc_calculated_accel_rate.append(accel_rate)
    calc_calculated_accel_end.append(accel_end)

pure_calculations = calculate_and_store_omega2t()

# create a new dataframe with the columns ExperimentTime, RPM, OmegaSquaredT, CalcOmegaSquaredT, AccelRate, AccelEnd, CalcAccelRate, CalcAccelEnd
df = pd.DataFrame({'ExperimentTime': data['ExperimentTime'], 'RPM': data['RPM'], 'OmegaSquaredT': data['OmegaSquaredT'],
                   'CalcOmegaSquaredT': calculated_omega2t, "OmegaSquaredTDiff": calc_omega2t_diff,
                   'AccelRate': calculated_accel_rate, 'AccelEnd': calculated_accel_end,
                   'CalcAccelRate': calc_calculated_accel_rate, 'CalcAccelEnd': calc_calculated_accel_end,
                   'OmegaSquaredTPureSpeed': calculated_omegasquaredt})
df.to_csv(r"C:\Users\Lukas\PycharmProjects\us3utils\SystemStatusDataOptima1Run2424_calc.csv")
print("done")
