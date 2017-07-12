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

# Pass Entire US, Alaska, and Hawaii
CONTIGUOUS_STATES = [1] + list(range(3, 12)) + list(range(13, 52))
DATE_SHIFT_RANGE = range(-6 * 7, 4 * 7 + 1)


def get_state_resolver(state_codes_file):
    """
    :return: dict, such as
        dict['42']['acronym'] = 'DC'
        dict['42']['name'] = 'District of Columbia'
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


def is_winter(date: datetime.date):
    # if date.month == 2 and date.day == 29:
    #     return False
    return date.month in [12, 1, 2]


def get_onsets(excess_data, threshold):
    onsets = dict()
    for idx in range(52):
        onsets[idx] = list()

    for state in range(52):
        for idx in range(len(excess_data[state])):
            if idx == 0 or idx == 1:
                continue
            prev2, prev1, current = excess_data[state][idx - 2], \
                excess_data[state][idx - 1], excess_data[state][idx]

            if current['date'] <= datetime.date(1972, 2, 28) or \
                    current['date'] >= datetime.date(2002, 12, 1):
                continue

            if prev2['excess'] >= threshold and prev1['excess'] >= threshold \
                    and is_winter(current['date']):
                # Cutoff second epidemic in the same winter-time
                if onsets[state] and current['date'] - onsets[state][-1] < datetime.timedelta(days=90):
                    continue
                onsets[state].append(current['date'])
                continue
    return onsets


def draw_onset_distribution(onsets):
    import matplotlib.pyplot as pp

    onset_dates = [0 for _ in range(91)]
    for state in CONTIGUOUS_STATES:
        for date in onsets[state]:
            try:
                onset_dates[(date.month % 12) * 31 + (date.day - 1)] += 1
            except ValueError:
                print(date)
    pp.xlabel('день от начала зимы')
    pp.ylabel('количество эпидемий')
    pp.plot(onset_dates, "x")
    pp.show()


def main():
    excess_data = get_mortality_excess('data/WeeklyExcessNew.txt')
    draw_onset_distribution(excess_data)

if __name__ == '__main__':
    t0 = time.time()
    main()
    print('Time elapsed: %.2f sec' % (time.time() - t0))
