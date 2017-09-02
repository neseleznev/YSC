#!/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017
import datetime
import json
import os
from pathlib import Path
import random

INTERVAL_LENGTH = 28  # days
CONTROL_SAMPLE_SIZE = 10000


def generate_control_sample(onsets, threshold, ah_dev, winter, sites, site_resolver, years, filename):

    onset_count = sum(len(onsets[threshold][site]) for site in sites)  # n
    os.makedirs(os.path.dirname('./' + filename), exist_ok=True)

    ah_samples = []
    for iteration in range(CONTROL_SAMPLE_SIZE + 1):

        # Print progress and add chunk to result
        if iteration % 1000 == 0:
            print(f'{int(100 * iter / CONTROL_SAMPLE_SIZE)} %')
            if Path(filename).is_file():
                with open(filename, 'r') as f:
                    saved = json.load(f)
            else:
                saved = []

            print(f'{len(saved)} saved values, {len(ah_samples)} new added')
            ah_samples += saved
            with open(filename, 'w') as f:
                f.write(json.dumps(ah_samples))
            if ah_samples:
                print(f'min {min(ah_samples)}, '
                      f'avg {sum(ah_samples) / len(ah_samples)}, '
                      f'max {max(ah_samples)}')
            ah_samples = []

        ah_dev_interval = []
        for i in range(onset_count):
            site = random.choice(sites)
            site_name = site_resolver[site]['name']
            year = random.choice(years)
            day_idx = random.randint(0, winter.days_count - 1)
            date = datetime.date(year, winter.START.month, winter.START.day)\
                + datetime.timedelta(days=day_idx)

            for j in range(INTERVAL_LENGTH):
                current_date = date + datetime.timedelta(days=j)
                if current_date.day == 29 and current_date.month == 2:  # Skip 29.02
                    current_date -= datetime.timedelta(days=1)
                ah_dev_interval.append(ah_dev[current_date.strftime('%d.%m.%Y')][site_name])

        ah_sample = sum(ah_dev_interval) / len(ah_dev_interval)
        ah_samples.append(ah_sample)


def generate_experimental_sample(onsets, threshold, ah_dev, winter, sites, site_resolver, filename):

    onset_average_ah_sample = []
    os.makedirs(os.path.dirname('./' + filename), exist_ok=True)

    for site in sites:
        site_name = site_resolver[site]['name']

        for date in onsets[threshold][site]:  # For every onset
            current_onset_ah = []

            for j in range(INTERVAL_LENGTH):
                current_date = date + datetime.timedelta(days=-j)
                if current_date.day == 29 and current_date.month == 2:  # Skip 29.02
                    current_date -= datetime.timedelta(days=1)
                current_onset_ah.append(ah_dev[current_date.strftime('%d.%m.%Y')][site_name])
            onset_average_ah_sample.append(sum(current_onset_ah) / len(current_onset_ah))

    print('Onset-prior AH\' sample computed')
    print(f'min {min(onset_average_ah_sample)}, '
          f'avg {sum(onset_average_ah_sample) / len(onset_average_ah_sample)}, '
          f'max {max(onset_average_ah_sample)}')
    with open(filename, 'w') as f:
        f.write(json.dumps(onset_average_ah_sample))
