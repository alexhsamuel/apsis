#!/usr/bin/python3

from   contextlib import closing
from   datetime import date as Date, timedelta as Timedelta
from   pprint import pformat
import sys

DAY = Timedelta(days=1)

def extract_ics(text):
    i0 = text.find("BEGIN:VCALENDAR")
    assert i0 >= 0
    i1 = text.find("END:VCALENDAR")
    assert i1 >= 0
    text = text[i0 : i1 + len("END:VCALENDAR")]
    text = text.replace("\n ", "")
    lines = text.split("\n")
    lines = [ l for l in lines if len(l) > 0 ]
    ics = [ tuple(l.split(":", 1)) for l in lines ]
    return ics


def parse_event(lines):
    event = {}
    while True:
        line = next(lines)
        if line == ("END", "VEVENT"):
            break
        else:
            key, value = line
            event[key] = value
    return event


def parse_calendar(lines):
    meta = {}
    events = []
    while True:
        line = next(lines)
        if line == ("END", "VCALENDAR"):
            break
        elif line == ("BEGIN", "VEVENT"):
            events.append(parse_event(lines))
        else:
            key, value = line
            meta[key] = value
    return meta, events


def parse_date(text):
    assert len(text) == 8
    return Date(int(text[: 4]), int(text[4 : 6]), int(text[6 :]))


def extract_holidays(events):
    for event in events:
        categories = event["CATEGORIES"].split(",")
        if "Holidays" in categories:
            start = parse_date(event["DTSTART;VALUE=DATE"])
            end   = parse_date(event["DTEND;VALUE=DATE"])
            
            date = start
            while date < end:
                yield date, event["SUMMARY"]
                date += DAY


def main(argv):
    filename, = argv[1 :]
    with closing(open(filename)) as file:
        text = file.read()
    lines = iter(extract_ics(text))
    line = next(lines)
    assert line == ("BEGIN", "VCALENDAR")
    meta, events = parse_calendar(lines)

    holidays = tuple(extract_holidays(events))
    for date, name in sorted(holidays):
        print(date, name)


if __name__ == "__main__":
    main(sys.argv)


