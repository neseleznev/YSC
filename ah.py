#!/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017

import copy
from collections import OrderedDict
import datetime
import os

import matplotlib
import matplotlib.dates as plt_dates
import pylab as plt


def get_ah_mean(ah):
    """
    :param ah: dict, dict['dd.mm.year']['State Name'] = absolute humidity
    :return: dict, dict['dd.mm']['State Name'] = all-time mean humidity
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


def get_ah_mean_for_site(ah_mean, cite_name):
    result = []

    for date, info in sorted(
            ah_mean.items(),
            key=lambda x: int(x[0][0:2]) + 31*int(x[0][3:5])
    ):
        for site, value in info.items():
            if site != cite_name:
                continue
            result.append(value)
    return result


def draw_ah_mean(ah_mean, sites, colors):
    """AH' for some sites (states for USA, cities for Russia)"""
    fig = plt.figure(figsize=(10, 6))
    matplotlib.rcParams.update({'font.size': 14})

    ax = fig.add_subplot(111)

    date_first = datetime.datetime(1970, 1, 1)
    date_last = datetime.datetime(1971, 1, 1)

    date_range = plt_dates.drange(date_first, date_last, datetime.timedelta(days=1))

    # DATES on Ox
    for site in sites:
        plt.plot_date(date_range,
                      get_ah_mean_for_site(ah_mean, site),
                      colors.get(site, 'k') + '-', label=site, linewidth=2.0)
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


def plot_average_ah_dev(average_ah_dev, colors, date_shift_range,
                        title=None, save_to_file=None):
    fig = plt.figure(figsize=(10, 6))
    matplotlib.rcParams.update({'font.size': 14})

    fig.add_subplot(111)
    if title:
        plt.title(title)
    plt.xlabel('Day Relative to Onset')
    plt.ylabel('Specific Humidity Anomaly (kg/kg)')

    # Enable scaling and 10^k formatting
    xfmt = plt.ScalarFormatter(useMathText=True)
    xfmt.set_powerlimits((0, 0))
    plt.gca().yaxis.set_major_formatter(xfmt)

    # Dashed line for AH' = 0
    plt.plot((date_shift_range[0], date_shift_range[-1]), (0, 0), 'k--')

    for threshold, average in average_ah_dev.items():
        plt.plot(date_shift_range, average,
                 colors.get(threshold, '') + '-', label=str(threshold))

    plt.legend(loc='best', fancybox=True, shadow=True)

    if save_to_file:
        os.makedirs(os.path.dirname('./' + save_to_file), exist_ok=True)
        plt.savefig(save_to_file, bbox_inches='tight')
    else:
        plt.show()
    plt.close()
