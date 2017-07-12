#!/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017
"""
    Figure 2 from Shaman, 2010 article.
    All the data files obtained from email correspondence with prof Shaman

    "Vasiliy,

    It’s fine to share the P&I data.  Here they are.
    The file ‘WeeklyExcessNew.txt’ has the excess weekly P&I mortality data
    (last column).  The first column gives the NCHS State code, which are
    given in detail in the other file (0 is the entire US).  The second
    column is the data—the first date is January 2-8, 1972.

    Cheers,
    Jeff"
"""

import datetime
import time

import matplotlib
import numpy as np
import pylab as plt

from usa_ah import get_ah, get_ah_mean, get_ah_deviation
from usa_onset import get_state_resolver, \
    get_mortality_excess, get_onsets

AH_CSV_FILE = 'data/stateAHmsk_oldFL.csv'
STATE_CODES_FILE = 'data/NCHS_State_codes.txt'
MORTALITY_EXCESS_FILE = 'data/WeeklyExcessNew.txt'

# Pass Entire US, Alaska, and Hawaii
CONTIGUOUS_STATES = [1] + list(range(3, 12)) + list(range(13, 52))
DATE_SHIFT_RANGE = range(-6 * 7, 4 * 7 + 1)
THRESHOLDS = [0.005, 0.01, 0.015, 0.02]


def get_average_ah_dev(ah_dev, excess_data, thresholds, state_resolver):
    average_ah_dev = dict()

    for threshold in thresholds:
        onsets = get_onsets(excess_data, threshold)

        print('Found %d epidemic for %f threshold' % (
            sum(len(onsets[state]) for state in CONTIGUOUS_STATES), threshold))

        relative_ah_devs = []
        for state in CONTIGUOUS_STATES:
            state_name = state_resolver[state]['name']

            for onset in onsets[state]:
                current_ah_dev = []

                for day_shift in DATE_SHIFT_RANGE:
                    date = onset + datetime.timedelta(days=day_shift)

                    if date.month == 2 and date.day == 29 or date.month == 3:
                        date += datetime.timedelta(days=1)  # TODO figure out how to manage it
                    current_ah_dev.append(
                        ah_dev[date.strftime('%d.%m.%Y')][state_name])
                relative_ah_devs.append(np.array(current_ah_dev))

        relative_ah_devs = np.array(relative_ah_devs)
        average_ah_dev[threshold] = np.average(relative_ah_devs, axis=0)

    return average_ah_dev


def plot_average_ah_dev(average_ah_dev):
    fig = plt.figure(figsize=(10, 6))
    matplotlib.rcParams.update({'font.size': 14})

    ax = fig.add_subplot(111)
    plt.xlabel('Day relative to onset')
    plt.ylabel('Specific humidity anomaly (kg/kg)')
    colors = {0.005: 'b', 0.01: 'g', 0.015: 'r', 0.02: 'c'}

    for threshold, average in average_ah_dev.items():
        plt.plot(DATE_SHIFT_RANGE, average,
                 colors.get(threshold, 'k') + '-', label=str(threshold))

    plt.legend(loc='best', fancybox=True, shadow=True)
    plt.show()


def main():
    state_resolver = get_state_resolver(STATE_CODES_FILE)
    ah = get_ah(AH_CSV_FILE)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    excess_data = get_mortality_excess(MORTALITY_EXCESS_FILE)

    average_ah_dev = get_average_ah_dev(
        ah_dev, excess_data, THRESHOLDS, state_resolver)

    plot_average_ah_dev(average_ah_dev)

if __name__ == '__main__':
    t0 = time.time()
    main()
    print('Time elapsed: %.2f sec' % (time.time() - t0))
