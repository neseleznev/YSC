#!/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017

import datetime
import os

import matplotlib.pyplot as plt
import numpy as np


class Winter:
    START = datetime.date(1971, 12, 1)
    END = datetime.date(1972, 2, 29)

    @property
    def days_count(self):
        return (self.END - self.START).days + 1

    def get_day_index(self, date: datetime.date):
        if type(date) is dict:
            print(date)
        if date.month > 6:  # End of year
            year = self.START.year
        else:
            year = self.END.year
        days = (datetime.date(year, date.month, date.day) - self.START).days
        if 0 <= days < self.days_count:
            return days
        else:
            raise ValueError('date ' + str(date) + ' is out of winter range')

    def is_winter(self, date: datetime.date):
        if date.month > self.START.month or \
                date.month == self.START.month and date.day >= self.START.day:
            return True
        if date.month < self.END.month or \
                date.month == self.END.month and date.day <= self.END.day:
            return True
        return False
        # if date.month == 2 and date.day == 29:
        #     return False
        # return date.month in [12, 1, 2]


def draw_onset_distribution_by_week(onsets, sites, winter=Winter(),
                                    title=None, save_to_file=None):
    onset_dates = [0 for _ in range(winter.days_count // 7 + 1)]
    for site in sites:
        for date in onsets[site]:
            try:
                onset_dates[winter.get_day_index(date) // 7] += 1
            except ValueError:
                print(date)
                pass

    fig = plt.figure()
    if title:
        plt.title(title)
    ax = fig.add_subplot(111)

    plt.xlabel('Week of winter')
    plt.ylabel('Number of epidemics')
    plt.plot(onset_dates)  # , "x")

    ax.text(0.65, 0.9, 'Overall epidemics: ' + str(sum(onset_dates)),
            transform=ax.transAxes,
            style='italic',
            bbox={'facecolor': 'red', 'alpha': 0.5, 'pad': 10})

    if save_to_file:
        os.makedirs(os.path.dirname('./' + save_to_file), exist_ok=True)
        plt.savefig(save_to_file, bbox_inches='tight')
    else:
        plt.show()


def get_average_ah_vs_onsets(ah_dev, onsets, sites, thresholds,
                             date_shift_range, state_resolver):
    average_ah_dev = dict()

    for threshold in thresholds:
        all_onsets = []
        for site in sites:
            for date in onsets[threshold][site]:
                all_onsets.append(date.strftime("%d.%m.%Y"))

        print('Found %d epidemic for %f threshold: %s' % (
            sum(len(onsets[threshold][site]) for site in sites), threshold,
            str(all_onsets)))

        relative_ah_devs = []
        for site in sites:
            site_name = state_resolver[site]['name']

            for onset in onsets[threshold][site]:
                current_ah_dev = []

                for day_shift in date_shift_range:
                    date = onset + datetime.timedelta(days=day_shift)

                    if date.month == 2 and date.day == 29 or date.month in [3, 4, 5]:
                        date += datetime.timedelta(days=1)  # TODO figure out how to manage it
                    current_ah_dev.append(
                        ah_dev[date.strftime('%d.%m.%Y')][site_name])
                relative_ah_devs.append(np.array(current_ah_dev))

        relative_ah_devs = np.array(relative_ah_devs)
        average_ah_dev[threshold] = np.average(relative_ah_devs, axis=0)

    return average_ah_dev
