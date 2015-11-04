#!/usr/bin/python3

from datetime import date, timedelta

DAY = timedelta(days=1)

MONDAY      = 0
TUESDAY     = 1
WEDNESDAY   = 2
THURSDAY    = 3
FRIDAY      = 4
SATURDAY    = 5
SUNDAY      = 6

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", )

def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

for offset in range(146097):
    d = date(2000, 3, 1) + offset * DAY
    day = d.day - 1
    ordinal = (d - date(d.year, 1, 1)).days
    weekday = d.weekday()

    thursday = ordinal + THURSDAY - weekday
    if thursday < 0:
        dec31_weekday = weekday - day - 1
        cal = (
            d.year - 1, 
            52 if (dec31_weekday == THURSDAY
                   or (dec31_weekday == FRIDAY and is_leap(d.year - 1)))
            else 51)
    elif thursday >= 365 and (thursday >= 366 or not is_leap(d.year)):
        cal = (d.year + 1, 0)
    else:
        cal = (d.year, thursday // 7)

    isocalendar = (cal[0], cal[1] + 1, weekday + 1)
    if isocalendar != d.isocalendar():
        print("{:5d} {} {:03d} {} {}".format(offset, d, ordinal, d.isocalendar(), isocalendar))


