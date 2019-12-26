from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pygeodesy.sphericalTrigonometry import LatLon
import pygeodesy.dms as dms
import pytz
from skyfield.api import load, Topos
from skyfield.almanac import find_discrete
from skyfield.almanac import sunrise_sunset


def nearest_minute(dt):
    """ Round the time to the nearest minute

    See https://rhodesmill.org/skyfield/almanac.html#rounding-time-to-the-nearest-minute
    :param dt: DateTime object
    :return: DateTime object with time rounded
    """
    return (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)


def convert_to_minutes(dt):
    """ Report time in minutes from a full DateTime object

    :param dt: Datetime object
    :return: the time (HH:MM:SS) in minutes

    Note: tn = nearest_minute(time.utc_datetime()) # use if you want minutes only, seconds = 00
    By default, we observe seconds too.
    """
    tn = dt.utc_datetime()
    return tn.hour * 60 + tn.minute + tn.second / 60


def get_mp(lat1, lon1, lat2, lon2):
    """ Calculate the geographical midpoint of the circuit (TX to RX)

    Return lat, lon from LatLon, which must be converted to string, toStr()
    """
    a = LatLon(lat1, lon1)
    b = LatLon(lat2, lon2)

    return a.midpointTo(b).toStr().split(',')


# Initialize skyfield parameters
ts = load.timescale()
planets = load('de421.bsp')

# Timezone = UTC, elevation (elv) = 0 meters
tzn, elv = 'UTC', 0
tz = pytz.timezone(tzn)

# Set the TX variables
txname = "ZL1 Auckland"
txlat, txlon = -36.85, 174.77
txloc = Topos(txlat, txlon, elevation_m=elv)

### STOP: Set the start date and end date here ###
start_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
end_date = datetime.strptime("2020-02-01", "%Y-%m-%d")
# NOTE: end_date is not included in the range of dates

date_list = [start_date + timedelta(days=x) for x in range(0, (end_date-start_date).days)]

# Set the list of RX locations
dxcc = [
    ["3Y/B Bouvet", -54.42, 3.381],
    ["PY0T Trindade & Martim Vaz Is", -20.5, -29.33],
    ["W2 New York City, NY", 40.8, -74.0],
    ["OJ0 Märket Reef", 60.300833, 19.131389],
]

# Run calculations from TX to the 'dxcc' list of locations
for country in dxcc:

    dates, t_sr, t_ss, r_sr, r_ss, mp_sr, mp_ss = [], [], [], [], [], [], []

    # Receive site params
    cty, rxlat, rxlon = country
    prefix = cty\
        .replace(' ', '_')\
        .replace('.', '')\
        .replace(',', '')\
        .replace('/', '')
    rxloc = Topos(rxlat, rxlon, elevation_m=elv)
    print("Processing %s..." % cty)

    # Coordinates of circuit midpoint
    mp_lat, mp_lon = get_mp(txlat, txlon, rxlat, rxlon)
    mp_lat, mp_lon = dms.parseDMS2(mp_lat, mp_lon)
    mploc = Topos(mp_lat, mp_lon, elevation_m=elv)

    # Formatters for plotting
    mondays = mdates.WeekdayLocator(mdates.MONDAY)
    alldays = mdates.DayLocator()
    weekFormatter = mdates.DateFormatter('%b %d')
    dayFormatter = mdates.DateFormatter('%d')

    # Run for date range given
    for date in date_list:

        e = tz.localize(date)
        t0 = ts.utc(e)
        t1 = ts.utc(tz.normalize(e + timedelta(1)))
        dates.append(str(t0.utc_strftime("%Y-%m-%d")))

        # calculate sunrise and sunset times, and check if they exist
        # tx = list of sunrise/sunset times, specified by yt where True = sunrise, False = sunset
        tx, yt = find_discrete(t0, t1, sunrise_sunset(planets, txloc))

        # check if no sunrise and no sunset
        if not len(tx):
            t_sr.append(np.nan)
            t_ss.append(np.nan)
        # check if sunrise or sunset but not both
        elif len(yt) == 1:
            if yt:
                # yt = True, so sunset missing
                t_ss.append(np.nan)
            else:
                t_sr.append(np.nan)

        rx, yr = find_discrete(t0, t1, sunrise_sunset(planets, rxloc))
        if not len(rx):
            r_sr.append(np.nan)
            r_ss.append(np.nan)
        elif len(rx) == 1:
            if yr:
                # yr = True, so sunset missing
                r_ss.append(np.nan)
            else:
                r_sr.append(np.nan)

        mp, ym = find_discrete(t0, t1, sunrise_sunset(planets, mploc))
        if not len(mp):
            mp_sr.append(np.nan)
            mp_ss.append(np.nan)
        elif len(mp) == 1:
            if ym:
                # ym = True, so sunset missing
                mp_ss.append(np.nan)
            else:
                mp_sr.append(np.nan)

        # process calculated sunrise and sunset times
        for time, yx in zip(tx, yt):
            if yx:
                t_sr.append(convert_to_minutes(time))
            else:
                t_ss.append(convert_to_minutes(time))

        # Handle a rare case where there are 3 sunrise/sunset events in one single day
        if len(list(zip(tx, yt))) == 3:
            # delete third value from list, keeping sunrise/sunset pairs in sync (= 2 values only)
            if yx:
                t_sr.pop()
            else:
                t_ss.pop()

        for time, yy in zip(rx, yr):
            if yy:
                r_sr.append(convert_to_minutes(time))
            else:
                r_ss.append(convert_to_minutes(time))

        if len(list(zip(rx, yr))) == 3:
            if yy:
                r_sr.pop()
            else:
                r_ss.pop()

        for time, yz in zip(mp, ym):
            if yz:
                mp_sr.append(convert_to_minutes(time))
            else:
                mp_ss.append(convert_to_minutes(time))

        if len(list(zip(mp, ym))) == 3:
            if yz:
                mp_sr.pop()
            else:
                mp_ss.pop()

    # Convert ISO dates to matplotlib's internal date format.
    x = mdates.datestr2num(dates)

    fig, ax = plt.subplots(1, 1, figsize=(12, 9))

    time = ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
            '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
            '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
            '18:00', '19:00', '20:00', '21:00', '22:00', '23:00',
            '24:00']

    # this will place the time strings above at every 60 min
    tick_location = [t * 60 for t in range(25)]
    ax.set_yticks(tick_location)
    ax.set_yticklabels(time)
    ax.set_yticks(range(0, 1500, 60))
    ax.set_yticks(range(30, 1440, 60), minor=True)
    ax.set_ylim(0, 1440)
    ax.xaxis.set_major_locator(mondays)
    ax.xaxis.set_minor_locator(alldays)
    ax.xaxis.set_major_formatter(weekFormatter)

    tx_sr, = ax.plot(x, t_sr, 'red', linestyle='dotted', linewidth=2.0)
    rx_sr, = ax.plot(x, r_sr, 'red', linewidth=1)
    m_sr, = ax.plot(x, mp_sr, 'red', linestyle="-.", linewidth=1.0)
    tx_ss, = ax.plot(x, t_ss, 'black', linestyle='dotted', linewidth=2.0)
    rx_ss, = ax.plot(x, r_ss, 'black', linewidth=1)
    m_ss, = ax.plot(x, mp_ss, 'black', linestyle="-.", linewidth=1.0)
    ax.xaxis_date()

    if t_sr <= t_ss:
        ax.fill_between(x, t_ss, 1440, facecolor='lightgrey', alpha=0.3, interpolate=True)
        ax.fill_between(x, t_sr, 0, facecolor='lightgrey', alpha=0.3, interpolate=True)
    else:
        ax.fill_between(x, t_ss, t_sr, facecolor='blue', alpha=0.3, interpolate=True)

    if r_sr <= r_ss:
        ax.fill_between(x, r_ss, 1440, facecolor='blue', alpha=0.1, interpolate=True)
        ax.fill_between(x, r_sr, 0, facecolor='blue', alpha=0.1, interpolate=True)
    else:
        ax.fill_between(x, r_ss, r_sr, facecolor='blue', alpha=0.1, interpolate=True)

    plt.legend(
        (tx_sr, tx_ss, rx_sr, rx_ss, m_sr, m_ss),
        ('%s sr' % txname,
         '%s ss' % txname,
         '%s sr' % cty,
         '%s ss' % cty,
         'Midpoint sr',
         'Midpoint ss',
         ),
        loc='best'
    )
    plt.grid(True, alpha=0.3)

    plt.setp(plt.gca().get_xticklabels(), rotation=90, horizontalalignment='right')
    title_text = "%d Sunrise/Sunset Analysis for circuit: %s to %s" % (start_date.year, txname, cty)
    plt.title(title_text)

    plt.savefig('%s_%s_%s' % (start_date.year, txname, prefix))
    plt.close(plt.gcf())
    print("Saving for %s... " % cty)

print("++ END ++")
