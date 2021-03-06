# !/usr/env/bin python3
# -*- coding: utf8 -*-
# Nikita Seleznev, 2017

import copy
import csv
import datetime
import json
import time
from collections import OrderedDict

from scipy import stats

from ah import get_ah_mean, get_ah_deviation, plot_average_ah_dev, draw_ah_mean
from hypothesis import generate_control_sample, generate_experimental_sample
from onset import get_average_ah_vs_onsets, Winter, draw_onset_distribution_by_week

AH_FILE_PATTERN = 'data/flu_dbase/%s.txt'
POPULATION_CSV_PATTERN = 'data/population/%s.csv'
CITIES = ['spb', 'msk', 'nsk', ]
PARIS = ['paris', ]
DATE_SHIFT_RANGE = range(-6 * 7, 4 * 7 + 1)
THRESHOLDS = [0.005, 0.01, 0.015, 0.02]
THRESHOLD_COLORS = {0.005: 'b', 0.01: 'g', 0.015: 'r', 0.02: 'c'}


def get_city_resolver():
    """
    :return: dict, such as
        dict['spb']['acronym'] = 'SPB'
        dict['spb']['name'] = 'Saint Petersburg'
    """
    resolver = {
        'spb': {'acronym': 'SPB', 'name': 'Saint Petersburg'},
        'msk': {'acronym': 'MSK', 'name': 'Moscow'},
        'nsk': {'acronym': 'NSK', 'name': 'Novosibirsk'},
        'paris': {'acronym': 'PAR', 'name': 'Paris'},
    }
    return resolver


def get_population(cities):
    """
    :param cities: list of strings, ['paris', 'spb'] for csv filename pattern
        in format (Year;Population)
    :return: dict[str] = {int: int}, for example
        data['paris'][1982] = 10073059
    """
    data = dict()
    for city in cities:
        data[city] = dict()
        with open(POPULATION_CSV_PATTERN % city, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter=';'):
                data[city][int(row['Year'])] = int(row['Population'])
    return data


def get_ah(cities):
    """
    :return: dict, data['dd.mm.year']['City Name'] = absolute humidity
    """
    data = dict()
    city_resolver = get_city_resolver()

    for city in cities:
        with open(AH_FILE_PATTERN % city, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter=' '):
                date = row['Date']

                if date.endswith('0229'):
                    continue  # omit leap year

                date_str = '%s.%s.%s' % (date[6:], date[4:6], date[:4])
                city_name = city_resolver[city]['name']
                if date_str not in data:
                    data[date_str] = OrderedDict()
                try:
                    data[date_str][city_name] = row['Humidity']
                except KeyError:
                    data[date_str] = {city_name: row['Humidity']}
    return data


def get_daily_morbidity(cities):
    """
    :return: dict, dict['City Code']['dd.mm.year'] = absolute morbidity
    """
    data = dict()
    for city_code in cities:
        data[city_code] = OrderedDict()

        with open(AH_FILE_PATTERN % city_code, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter=' '):
                morbidity = int(row['Incidence'])

                date = datetime.datetime.strptime(row['Date'], "%Y%m%d").date()
                date_str = '%02d.%02d.%04d' % (date.day, date.month, date.year)

                if date_str not in data[city_code]:
                    data[city_code][date_str] = morbidity
                else:
                    data[city_code][date_str] += morbidity
    return data


def get_morbidity_mean(morbidity):
    """
    :param morbidity: dict, dict['City Code']['dd.mm.year'] = absolute morbidity
    :return: dict, dict['City Code']['dd.mm'] = all-time mean morbidity
        for that date
    """
    morbidity_mean = OrderedDict()
    count = dict()

    # Collect the sum of morbidity
    for city, info in morbidity.items():
        if city not in morbidity_mean:
            morbidity_mean[city] = OrderedDict()
            count[city] = dict()

        for date, mor in info.items():
            if date[:5] not in morbidity_mean[city]:
                morbidity_mean[city][date[:5]] = float(mor)
                count[city][date[:5]] = 1
            else:
                morbidity_mean[city][date[:5]] += float(mor)
                count[city][date[:5]] += 1

    # Make actual mean values
    for city, info in morbidity_mean.items():
        for day_month in info.keys():
            info[day_month] /= count[city][day_month]
    return morbidity_mean


def get_morbidity_excess(morbidity, morbidity_mean):
    """
    :param morbidity: dict, data['City Code']['dd.mm.year'] = absolute morbidity
    :param morbidity_mean: dict, dict['City Code']['dd.mm'] = mean morbidity
        for that date
    :return: dict, data['City Code']['dd.mm.year'] = absolute morbidity
        deviation from all-time mean value for that date
    """
    morbidity_deviation = copy.deepcopy(morbidity)
    for city, info in morbidity.items():
        for date, mor in info.items():
            morbidity_deviation[city][date] = \
                float(morbidity[city][date]) - morbidity_mean[city][date[:5]]

    return morbidity_deviation


def get_relative_weekly_morbidity_excess(morbidity_excess, population):
    """
    Transform Morbidity / 100,000 people week by week
    :param morbidity_excess: dict, data['City Code']['dd.mm.year'] = absolute
        morbidity deviation from all-time mean value for that date
    :param population: dict[str] = {int: int}, dict['paris'][1982] = 10073059,
        city's population in this year
    :return: dict, data['City Code']['dd.mm.year'] = absolute weekly morbidity
        deviation from all-time mean value for that date (only for mondays)
    """
    weekly_morbidity = dict()
    for city, info in morbidity_excess.items():
        weekly_morbidity[city] = OrderedDict()

        for date_str, mor in info.items():
            date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
            monday = date - datetime.timedelta(days=date.weekday())

            relative_mor = mor * (100000 / population[city][date.year])
            monday_str = '%02d.%02d.%04d' % (
                monday.day, monday.month, monday.year)

            if monday not in weekly_morbidity[city]:
                weekly_morbidity[city][monday_str] = relative_mor
            else:
                weekly_morbidity[city][monday_str] += relative_mor

    return weekly_morbidity


def get_onsets_by_morbidity(excess_data, thresholds, winter=Winter()):
    onsets = dict()
    for threshold in thresholds:
        onsets[threshold] = dict()
        for city in excess_data.keys():
            onsets[threshold][city] = list()

            excess = sorted(
                excess_data[city].items(),
                key=lambda x: int(x[0][0:2]) + 31*int(x[0][3:5]) + 366*int(x[0][6:10]))

            for idx in range(len(excess)):
                if idx == 0 or idx == 1:
                    continue
                prev2, prev1, current = excess[idx - 2], \
                    excess[idx - 1], excess[idx]

                current_date = \
                    datetime.datetime.strptime(current[0], "%d.%m.%Y").date()

                if current_date <= datetime.date(1986, winter.END.month, winter.END.day - 1) or \
                        current_date >= datetime.date(2015, winter.START.month, winter.START.day):
                    continue

                if prev2[1] >= threshold and prev1[1] >= threshold \
                        and winter.is_winter(current_date):
                    # Cutoff second epidemic in the same winter-time
                    if onsets[threshold][city] and current_date - onsets[threshold][city][-1] < \
                            datetime.timedelta(days=winter.days_count):
                        continue
                    onsets[threshold][city].append(current_date)
                    continue
    return onsets


def get_onsets_by_epidemiologists(cities, ah_file_pattern, thresholds):
    data = dict()
    for city_code in cities:
        data[city_code] = list()

        is_epidemic_prev = False

        with open(ah_file_pattern % city_code, 'r') as csv_file:
            for row in csv.DictReader(csv_file, delimiter=' '):
                date = datetime.datetime.strptime(row['Date'], "%Y%m%d").date()
                monday = date - datetime.timedelta(days=date.weekday())
                is_epidemic = int(row['IsEpidemic']) == 1

                if is_epidemic:
                    if not is_epidemic_prev:
                        data[city_code].append(monday)
                        is_epidemic_prev = True
                else:
                    is_epidemic_prev = False

    # Dummy wrapper for compatibility
    wrapper = dict()
    for threshold in thresholds:
        wrapper[threshold] = data
    return wrapper


def test_parser():
    """
    Parse humidity data, draw a la Figure 1D from Shaman, 2010 article
    for Russian data
    """
    ah = get_ah(CITIES)
    ah_mean = get_ah_mean(ah)
    # ah_dev = get_ah_deviation(ah, ah_mean)

    # Graph 1D from Shaman 2010
    draw_ah_mean(
        ah_mean,
        sites=['Saint Petersburg', 'Moscow', 'Novosibirsk'],
        colors={'Saint Petersburg': 'b', 'Moscow': 'g', 'Novosibirsk': 'r'}
    )


def main_paris():
    state_resolver = get_city_resolver()
    population = get_population(PARIS)

    """
    Parameters
    """
    # THRESHOLDS = [-1000, 5, 10, 50, 100, 500, 750, ]
    # THRESHOLDS = [0, 5, 9, 25, 35, 40, 45, 50, ]
    THRESHOLDS = [9, 10, 20, 30]  # , 40, 50, ]
    # THRESHOLDS = [9, 10, 20, 30, 40, 50]
    # THRESHOLDS = [0, 25, 50, 75, 100, ]
    # THRESHOLDS = [10, 20, 30, 40, 50, 60, 70, 80]

    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 11, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)

    ah = get_ah(PARIS)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    morbidity = get_daily_morbidity(PARIS)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS, winter=winter)

    average_ah_dev = get_average_ah_vs_onsets(
        ah_dev, onsets, PARIS, THRESHOLDS,
        DATE_SHIFT_RANGE, state_resolver)

    title = f'Île-de-France: outbreaks in ' \
            f'{winter.START.strftime("%B")} — {winter.END.strftime("%B")}'
    filename = 'results/paris/paris_winter%d-%d_threshold%s.pdf' % (
        winter.START.month, winter.END.month,
        max(average_ah_dev.keys())
    )
    plot_average_ah_dev(
        average_ah_dev, THRESHOLD_COLORS, DATE_SHIFT_RANGE,
        limits=(-11e-4, 15e-4), title=title, save_to_file=filename)


def rf_epidemiologists():
    # CITIES = ['spb', ]
    THRESHOLDS = [0]

    city_resolver = get_city_resolver()
    ah = get_ah(CITIES)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    onsets = get_onsets_by_epidemiologists(
        CITIES, AH_FILE_PATTERN, THRESHOLDS)

    cases = [
        (['msk'], 'Moscow', 'Moscow'),
        (['spb'], 'SaintPetersburg', 'Saint Petersburg'),
        (['nsk'], 'Novosibirsk', 'Novosibirsk'),
        (['spb', 'msk', 'nsk'], 'spb,msk,nsk', 'All cities'),
    ]

    for case in cases:
        CUR_CITIES, name_suffix, title = case

        average_ah_dev = get_average_ah_vs_onsets(
            ah_dev, onsets, CUR_CITIES, THRESHOLDS,
            DATE_SHIFT_RANGE, city_resolver)

        filename = 'results/russia/epidemiologists/rf_%s.pdf' % name_suffix
        plot_average_ah_dev(average_ah_dev, THRESHOLD_COLORS, DATE_SHIFT_RANGE,
                            title=title, save_to_file=filename)


def main():
    """
    Parameters
    """
    THRESHOLDS = [30, 35, 40, 45]  # [25, 30, 35, 40, 45, 50]
    # CITIES = ['spb']
    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 11, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)

    city_resolver = get_city_resolver()
    population = get_population(CITIES)

    ah = get_ah(CITIES)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    morbidity = get_daily_morbidity(CITIES)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS, winter=winter)

    cases = [
        (['msk'], 'Moscow', 'Moscow'),
        (['spb'], 'SaintPetersburg', 'Saint Petersburg'),
        (['nsk'], 'Novosibirsk', 'Novosibirsk'),
        (['spb', 'msk', 'nsk'], 'spb,msk,nsk', 'All cities'),
    ]

    for case in cases:
        CUR_CITIES, name_suffix, title = case

        average_ah_dev = get_average_ah_vs_onsets(
            ah_dev, onsets, CUR_CITIES, THRESHOLDS,
            DATE_SHIFT_RANGE, city_resolver)

        filename = 'results/russia/morbidity/' \
                   'rf_m_%s_winter%d-%d_threshold%s-%s.pdf' % (
                    name_suffix, winter.START.month, winter.END.month,
                    min(average_ah_dev.keys()), max(average_ah_dev.keys()))
        plot_average_ah_dev(
            average_ah_dev, THRESHOLD_COLORS, DATE_SHIFT_RANGE,
            title=title, save_to_file=filename)


def onset_distribution_epidemiologists():
    winter = Winter()
    winter.START = datetime.date(winter.START.year, 10, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)

    onsets = get_onsets_by_epidemiologists(
        CITIES, AH_FILE_PATTERN, [0])

    filename = 'results/onsets/russia_epidemiologists.png'
    draw_onset_distribution_by_week(
        onsets[0], CITIES, winter=winter,
        title='Epidemic number distribution in Russia\n'
              'given by Influenza Institute (October — March)',
        save_to_file=filename)


def onset_distribution():
    # Params
    THRESHOLDS = [10]
    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 10, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)
    # End params

    population = get_population(CITIES)

    morbidity = get_daily_morbidity(CITIES)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS, winter=winter)

    filename = f'results/onsets/russia' \
               f'_winter{winter.START.month}-{winter.END.month}' \
               f'_threshold{THRESHOLDS[0]}.png'
    draw_onset_distribution_by_week(
        onsets[THRESHOLDS[0]], CITIES,
        winter=winter,
        title='Epidemic number distribution in Russia',
        save_to_file=filename)


def onset_distribution_paris():
    # Params
    THRESHOLDS = [5]
    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 10, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)
    # End params

    population = get_population(PARIS)

    morbidity = get_daily_morbidity(PARIS)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS, winter=winter)

    filename = f'results/onsets/paris' \
               f'_winter{winter.START.month}-{winter.END.month}' \
               f'_threshold{THRESHOLDS[0]}.png'
    draw_onset_distribution_by_week(
        onsets[THRESHOLDS[0]], PARIS,
        winter=winter,
        title='Epidemic number distribution in Paris,\n'
              'determined with mordibity deviation (October — March)',
        save_to_file=filename)


def hypothesis_test():
    """
    Parameters
    """
    # THRESHOLDS = [5, 10, 15]
    THRESHOLDS = [5, 10, 15, 20, 25, 28, 30, 35, 40, 43, 44, 45, 50]
    # CITIES = ['spb']
    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 11, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)

    city_resolver = get_city_resolver()
    population = get_population(CITIES)

    ah = get_ah(CITIES)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    morbidity = get_daily_morbidity(CITIES)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS, winter)
    years = range(1986, 2015)

    for threshold in THRESHOLDS:
        generate_control_sample(
            onsets, threshold, ah_dev, winter, CITIES, city_resolver, years,
            filename=f'results/stats/russia/ah_sample.{threshold}.json')
        generate_experimental_sample(
            onsets, threshold, ah_dev, winter, CITIES, city_resolver,
            filename=f'results/stats/russia/epidemic_sample.{threshold}.json')

    for threshold in THRESHOLDS:
        print(f'threshold {threshold}')
        with open(f'results/stats/russia/ah_sample.{threshold}.json', 'r') as f:
            ah_sample = json.load(f)
        with open(f'results/stats/russia/epidemic_sample.{threshold}.json', 'r') as f:
            epidemic_sample = json.load(f)

        print(f"AH' sample size = {len(ah_sample)}")
        print(f"Epidemic sample size = {len(epidemic_sample)}")
        # t, prob = stats.ttest_ind(ah_sample, epidemic_sample)
        # print(f"Equal variance (Student's t-test): P-value = {prob}")
        t, prob = stats.ttest_ind(ah_sample, epidemic_sample, equal_var=False)
        print(f"Not equal variance (Welch’s t-test): P-value = {prob}")
        print()


def hypothesis_test_paris():
    THRESHOLDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30]
    winter = Winter()
    # if params[1] in [10, 12, 1, 3, 5]:
    #     last_day = 31
    # elif params[1] in [9, 11, 4]:
    #     last_day = 30
    winter.START = datetime.date(winter.START.year, 10, 1)
    winter.END = datetime.date(winter.END.year, 3, 31)

    city_resolver = get_city_resolver()
    population = get_population(PARIS)

    ah = get_ah(PARIS)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    morbidity = get_daily_morbidity(PARIS)
    morbidity_mean = get_morbidity_mean(morbidity)
    morbidity_excess = get_morbidity_excess(
        morbidity, morbidity_mean)
    excess_data = get_relative_weekly_morbidity_excess(
        morbidity_excess, population)

    onsets = get_onsets_by_morbidity(excess_data, THRESHOLDS)
    years = range(1986, 2015)

    for threshold in THRESHOLDS:
        generate_control_sample(onsets, threshold, ah_dev, winter, PARIS, city_resolver, years,
                                filename=f'results/stats/paris/ah_sample.{threshold}.json')
        generate_experimental_sample(onsets, threshold, ah_dev, winter, PARIS, city_resolver,
                                     filename=f'results/stats/paris/epidemic_sample.{threshold}.json')

    for threshold in THRESHOLDS:
        print(f'threshold {threshold}')
        with open(f'results/stats/paris/ah_sample.{threshold}.json', 'r') as f:
            ah_sample = json.load(f)
        with open(f'results/stats/paris/epidemic_sample.{threshold}.json', 'r') as f:
            epidemic_sample = json.load(f)

        print(f"AH' sample size = {len(ah_sample)}")
        print(f"Epidemic sample size = {len(epidemic_sample)}")
        t, prob = stats.ttest_ind(ah_sample, epidemic_sample)
        print(f"Equal variance (Student's t-test): P-value = {prob}")
        t, prob = stats.ttest_ind(ah_sample, epidemic_sample, equal_var=False)
        print(f"Not equal variance (Welch’s t-test): P-value = {prob}")
        print()


def hypothesis_test_epidemiologists():
    THRESHOLDS = [0]
    threshold = 0

    city_resolver = get_city_resolver()
    ah = get_ah(CITIES)
    ah_mean = get_ah_mean(ah)
    ah_dev = get_ah_deviation(ah, ah_mean)

    onsets = get_onsets_by_epidemiologists(
        CITIES, AH_FILE_PATTERN, THRESHOLDS)
    years = range(1986, 2015)

    from hypothesis import generate_control_sample, generate_experimental_sample

    generate_control_sample(onsets, threshold, ah_dev, Winter(), CITIES, city_resolver, years,
                            filename=f'results/stats/russia_epid/ah_sample.{threshold}.json')
    generate_experimental_sample(onsets, threshold, ah_dev, Winter(), CITIES, city_resolver,
                                 filename=f'results/stats/russia_epid/epidemic_sample.{threshold}.json')

    print(f'threshold {threshold}')
    with open(f'results/stats/russia_epid/ah_sample.{threshold}.json', 'r') as f:
        ah_sample = json.load(f)
    with open(f'results/stats/russia_epid/epidemic_sample.{threshold}.json', 'r') as f:
        epidemic_sample = json.load(f)

    print(f"AH' sample size = {len(ah_sample)}")
    print(f"Epidemic sample size = {len(epidemic_sample)}")
    t, prob = stats.ttest_ind(ah_sample, epidemic_sample)
    print(f"Equal variance (Student's t-test): P-value = {prob}")
    t, prob = stats.ttest_ind(ah_sample, epidemic_sample, equal_var=False)
    print(f"Not equal variance (Welch’s t-test): P-value = {prob}")
    print()


if __name__ == '__main__':
    t0 = time.time()
    # test_parser()
    # rf_epidemiologists()
    # main_paris()
    # main()
    # onset_distribution_epidemiologists()
    # onset_distribution()
    # onset_distribution_paris()
    hypothesis_test()
    # hypothesis_test_paris()
    # hypothesis_test_epidemiologists()
    print('Time elapsed: %.2f sec' % (time.time() - t0))
