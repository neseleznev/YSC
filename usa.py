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
import csv
import datetime
import time

from ah import get_ah_mean_for_site, get_ah_mean, get_ah_deviation, draw_ah_mean, plot_average_ah_dev
from onset import Winter, draw_onset_distribution, get_average_ah_vs_onsets

AH_CSV_FILE = 'data/stateAHmsk_oldFL.csv'
STATE_CODES_FILE = 'data/NCHS_State_codes.txt'
MORTALITY_EXCESS_FILE = 'data/WeeklyExcessNew.txt'

# Pass Entire US, Alaska, and Hawaii
CONTIGUOUS_STATES = [1] + list(range(3, 12)) + list(range(13, 52))
# CONTIGUOUS_STATES = [3, 6, 29, 32, 45]  # south-west
# CONTIGUOUS_STATES = [7, 8, 9, 20, 21, 22, 30, 31, 33, 39, 40, 46, 49]  # north-east
# CONTIGUOUS_STATES = [1, 4, 10, 11, 18, 19, 34, 41, 43, 47]  # bottom, Gulf region
# CONTIGUOUS_STATES = [5, 13, 14, 15, 16, 17, 23, 24, 25, 26, 27, 28,
#                      35, 36, 37, 38, 42, 44, 48, 50, 51]  # the rest
DATE_SHIFT_RANGE = range(-6 * 7, 4 * 7 + 1)
THRESHOLDS = [0.005, 0.01, 0.015, 0.02]
THRESHOLD_COLORS = {0.005: 'b', 0.01: 'g', 0.015: 'r', 0.02: 'c'}


def get_ah(ah_csv_file):
    """
    :return: dict, data['dd.mm.year']['State Name'] = absolute humidity
    """
    data = dict()

    with open(ah_csv_file, 'r') as csv_file:
        ah_reader = csv.DictReader(csv_file, delimiter=';')

        for row in ah_reader:
            if row['Date'].startswith('29.02'):
                continue  # omit leap year

            date = row['Date']
            del row['Date']
            data[date] = row

    return data


def get_state_resolver(state_codes_file):
    """
    :return: dict, such as
        dict[42]['acronym'] = 'DC'
        dict[42]['name'] = 'District of Columbia'
    """
    resolver = dict()
    with open(state_codes_file, 'r') as file:
        _ = file.readline()  # Header
        for line in file:
            code, acronym, *rest = line.split(' ')
            resolver[int(code)] = {'acronym': acronym,
                                   'name': ' '.join(rest).strip('\n')}
    resolver[0] = {'acronym': 'US',
                   'name': 'Entire USA'}
    return resolver


def get_date_from_week_index(week: int):
    """
    Resolve "the first date is January 2-8, 1972." to datetime.date
    """
    base_date = datetime.date(1972, 1, 2)
    return base_date + datetime.timedelta(weeks=week - 1)


def get_mortality_excess(mortality_excess_file):
    data = dict()
    for idx in range(52):
        data[idx] = list()

    with open(mortality_excess_file, 'r') as file:
        for line in file:
            values = line.split()
            if not values:
                continue

            state_code, population, date, mortality_excess = \
                int(values[0]), int(values[1]), \
                get_date_from_week_index(int(values[2])), \
                float(values[-1])

            data[state_code].append(
                dict(population=population,
                     date=date,
                     excess=mortality_excess / 7)
            )
    return data


def get_onsets(excess_data, thresholds, winter=Winter()):
    onsets = dict()
    for threshold in thresholds:
        onsets[threshold] = dict()

        for idx in range(52):
            onsets[threshold][idx] = list()

        for state in range(52):
            for idx in range(len(excess_data[state])):
                if idx == 0 or idx == 1:
                    continue
                prev2, prev1, current = excess_data[state][idx - 2], \
                    excess_data[state][idx - 1], excess_data[state][idx]

                if current['date'] <= datetime.date(1972, winter.END.month, winter.END.day) or \
                        current['date'] >= datetime.date(2002, winter.START.month, winter.START.day):
                    continue

                if prev2['excess'] >= threshold and prev1['excess'] >= threshold \
                        and winter.is_winter(current['date']):
                    # Cutoff second epidemic in the same winter-time
                    if onsets[threshold][state] and current['date'] - onsets[threshold][state][-1] < \
                            datetime.timedelta(days=winter.days_count):
                        continue
                    onsets[threshold][state].append(current['date'])
                    continue
    return onsets


def main():
    state_resolver = get_state_resolver(STATE_CODES_FILE)
    ah = get_ah(AH_CSV_FILE)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    excess_data = get_mortality_excess(MORTALITY_EXCESS_FILE)
    onsets = get_onsets(excess_data, THRESHOLDS)

    average_ah_dev = get_average_ah_vs_onsets(
        ah_dev, onsets, CONTIGUOUS_STATES, THRESHOLDS,
        DATE_SHIFT_RANGE, state_resolver)

    plot_average_ah_dev(average_ah_dev, THRESHOLD_COLORS,
                        DATE_SHIFT_RANGE,
                        save_to_file='results/usa/figure.png')


def test_parser():
    """
    Parse humidity data, draw Figure 1D from Shaman, 2010 article
    """
    ah = get_ah('data/stateAHmsk_oldFL.csv')
    ah_mean = get_ah_mean(ah)
    # ah_dev = get_ah_deviation(ah, ah_mean)

    # Graph 1D from Shaman 2010
    draw_ah_mean(
        ah_mean,
        sites=['Arizona', 'Florida', 'Illinois', 'New York', 'Washington'],
        colors={'Arizona': 'b', 'Florida': 'g', 'Illinois': 'r',
                'New York': 'c', 'Washington': 'm'}
    )


def onset_distribution():
    excess_data = get_mortality_excess(MORTALITY_EXCESS_FILE)
    onsets = get_onsets(excess_data, [0.005])
    draw_onset_distribution(onsets[0.005], CONTIGUOUS_STATES)


def winter_range_investigation():
    state_resolver = get_state_resolver(STATE_CODES_FILE)
    ah = get_ah(AH_CSV_FILE)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    excess_data = get_mortality_excess(MORTALITY_EXCESS_FILE)

    for params in ((12, 2),
                   (12, 3), (11, 2),
                   (11, 3),
                   (11, 4), (10, 3),
                   (10, 4),
                   (10, 5), (9, 4),
                   (9, 5),):
        winter = Winter()
        winter.START = datetime.date(winter.START.year, params[0], 1)
        if params[1] in [10, 12, 1, 3, 5]:
            last_day = 31
        elif params[1] in [9, 11, 4]:
            last_day = 30
        else:  # 2 (February 1972)
            last_day = 29
        winter.END = datetime.date(winter.END.year, params[1], last_day)

        onsets = get_onsets(excess_data, THRESHOLDS, winter)

        average_ah_dev = get_average_ah_vs_onsets(
            ah_dev, onsets, CONTIGUOUS_STATES, THRESHOLDS,
            DATE_SHIFT_RANGE, state_resolver)

        filename = 'results/winter_range_usa/figure_winter%d-%d.png' % (
            winter.START.month, winter.END.month
        )
        plot_average_ah_dev(average_ah_dev, THRESHOLD_COLORS,
                            DATE_SHIFT_RANGE, save_to_file=filename)


def distinct_states():
    state_resolver = get_state_resolver(STATE_CODES_FILE)
    ah = get_ah(AH_CSV_FILE)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    excess_data = get_mortality_excess(MORTALITY_EXCESS_FILE)
    onsets = get_onsets(excess_data, THRESHOLDS)

    deeps = dict()  # state_code: ah
    deep_level = -0.0003
    anomaly_peaks = [-19, -18, -17, -11, -10, -9]

    for state in [1] + list(range(3, 12)) + list(range(13, 52)):
        CONTIGUOUS_STATES = [state]

        average_ah_dev = get_average_ah_vs_onsets(
            ah_dev, onsets, CONTIGUOUS_STATES, THRESHOLDS,
            DATE_SHIFT_RANGE, state_resolver)

        for threshold, average in average_ah_dev.items():
            idxs = [day_x - DATE_SHIFT_RANGE[0]
                   for day_x in anomaly_peaks]
            deep = min(average[idx] for idx in idxs)
            if deep < deep_level:
                if state in deeps:
                    deeps[state] = min(deep, deeps[state])
                else:
                    deeps[state] = deep
        # plot_average_ah_dev(
        #     average_ah_dev, THRESHOLD_COLORS, DATE_SHIFT_RANGE,
        #     title=state_resolver[state]['name'],
        #     save_to_file='results/usa_distinct/figure_state%s.png' %
        #                  state_resolver[state]['acronym'])

    for state, deep in sorted(deeps.items(), key=lambda x: x[1]):
        print('Deep level %f in %s state (%d)' % (
            deep, state_resolver[state]['acronym'], state)
        )


if __name__ == '__main__':
    t0 = time.time()
    # test_parser()
    # onset_distribution()
    # winter_range_investigation()
    # distinct_states()
    main()
    print('Time elapsed: %.2f sec' % (time.time() - t0))
