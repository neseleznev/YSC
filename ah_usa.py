#!/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017
"""
    Parse humidity data, draw Figure 1D from Shaman, 2010 article
"""

import copy
from collections import OrderedDict
import csv
import datetime
import time

import matplotlib
import matplotlib.dates as plt_dates
import pylab as plt

AH_CSV_FILE = 'data/stateAHmsk_oldFL.csv'


def get_ah():
    """
    :return: dict, data['dd.mm.year']['State Name'] = absolute humidity
    """
    data = dict()

    with open(AH_CSV_FILE, 'r') as csv_file:
        ah_reader = csv.DictReader(csv_file, delimiter=';')

        for row in ah_reader:
            if row['Date'].startswith('29.02'):
                continue  # omit leap year

            date = row['Date']
            del row['Date']
            data[date] = row

    return data


def get_ah_mean(ah):
    """
    :param ah: dict, dict['dd.mm.year']['State Name'] = absolute humidity
    :return: dict, dict['dd.mm']['State Name'] = 31y mean value of humidity
        for that date
    """
    ah_mean = OrderedDict()
    count = dict()

    # Collect the sum of humidity
    for date, info in ah.items():
        if date[:5] not in ah_mean:
            ah_mean[date[:5]] = OrderedDict()
            count[date[:5]] = 0
        count[date[:5]] += 1

        for state, humidity in info.items():
            if state not in ah_mean[date[:5]]:
                ah_mean[date[:5]][state] = float(humidity)
            else:
                ah_mean[date[:5]][state] += float(humidity)

    # Make actual mean values
    for day_month, info in ah_mean.items():
        for state in info.keys():
            info[state] /= count[day_month]
    return ah_mean


def get_ah_deviation(ah, ah_mean):
    """
    :param ah: dict, data['dd.mm.year']['State Name'] = absolute humidity
    :param ah_mean: dict, dict['dd.mm']['State Name'] = mean humidity
        for that date
    :return: dict, data['dd.mm.year']['State Name'] = absolute humidity
        deviation from 31y mean value for that date
    """
    ah_deviation = copy.deepcopy(ah)
    for date, info in ah.items():
        for state, humidity in info.items():
            ah_deviation[date][state] = float(ah[date][state]) - ah_mean[date[:5]][state]

    return ah_deviation


def get_ah_mean_for_state(ah_mean, state_name):
    result = []

    for date, info in ah_mean.items():
        for state, value in info.items():
            if state != state_name:
                continue
            result.append(value)
    return result


def draw_ah_mean(ah_mean, states):
    """AH' for some states"""
    fig = plt.figure(figsize=(10, 6))
    matplotlib.rcParams.update({'font.size': 14})

    ax = fig.add_subplot(111)

    date_first = datetime.datetime(1970, 1, 1)
    date_last = datetime.datetime(1971, 1, 1)

    date_range = plt_dates.drange(date_first, date_last, datetime.timedelta(days=1))

    # DATES on Ox
    colors = {'Arizona': 'b', 'Florida': 'g', 'Illinois': 'r', 'New York': 'c', 'Washington': 'm'}
    for state in states:
        plt.plot_date(date_range,
                      get_ah_mean_for_state(ah_mean, state),
                      colors.get(state, 'k') + '-', label=state, linewidth=2.0)
    # plt.plot_date(date_range[delta: delta + len(y_real)],
    #               y_real,
    #               "bo", label='Data', markersize=6)

    # print([dtf.convertFloatToDate(x) for x in date_range[delta : delta + len(y_real)]])

    formatter = plt_dates.DateFormatter('%d.%m')
    ax.xaxis.set_major_formatter(formatter)

    plt.legend(loc='best', fancybox=True, shadow=True)

    # plt.figtext(0.15, 0.8, "$R^2 = %.3f$" % R2, fontsize=27)

    # plt.ylabel('Absolute ARI incidence, cases')

    # plt.title('{0}, {1} to {2} ({3})'.format(
    #     city_name,
    #     dtf.convertDateToStringMY(date_first + datetime.timedelta(days=model_beg_index)),
    #     dtf.convertDateToStringMY(date_first + datetime.timedelta(delta + len(y_real))),
    #     method_name))
    plt.grid()

    # plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.show()
    plt.close()


if __name__ == '__main__':
    t0 = time.time()

    ah = get_ah()
    ah_mean = get_ah_mean(ah)
    # ah_dev = get_ah_deviation(ah, ah_mean)

    print(time.time() - t0)
    
    # Graph 1D from Shaman 2010
    draw_ah_mean(ah_mean, ['Arizona', 'Florida', 'Illinois', 'New York', 'Washington'])

