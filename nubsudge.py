#!/usr/bin/env python3
import argparse
import codecs
import collections
import pdb
import re
import sys

def info(type, value, tb):
    if hasattr(sys, 'ps1') or not sys.stderr.isatty():
        sys.__excepthook__(type, value, tb)
    else:
        import traceback
        traceback.print_exception(type, value, tb)
        pdb.pm()
sys.excepthook = info

def _by_block(content):
    lines = content.split('\r\n')
    parts = []
    for line in lines:
        parts.append(line)
        if line == '':
            yield parts
            parts = []
    raise StopIteration

class Timestamp():
    def __init__(self, hours, minutes, seconds, milliseconds):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds
        self.milliseconds = milliseconds
        self.total_seconds = (hours * 60 * 60) + (minutes * 60) + seconds + (milliseconds * .001)

    def __str__(self):
        return "{:02d}:{:02d}:{:02d},{:03d}".format(self.hours, self.minutes, self.seconds, self.milliseconds)

    @classmethod
    def from_seconds(cls, total_seconds):
        hours = int(total_seconds / (60 * 60))
        remaining = total_seconds - (hours * 60 * 60)
        minutes = int(remaining / 60)
        remaining = remaining - (minutes * 60)
        seconds = int(remaining)
        milliseconds = int(1000 * (remaining - seconds))
        return Timestamp(hours, minutes, seconds, milliseconds)

OFFSET_PATTERN = re.compile(r'(?P<hours>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2}),(?P<milliseconds>\d{3})')
def _read_offsets(line):
    start, _, end = line.partition(' --> ')
    startm = OFFSET_PATTERN.match(start)
    if not startm:
        raise Exception("Unable to match {} with pattern".format(start))
    endm = OFFSET_PATTERN.match(end)
    if not endm:
        raise Exception("Unable to match {} with pattern".format(end))
    starttime = Timestamp(**{k: int(v) for k, v in startm.groupdict().items()})
    endtime = Timestamp(**{k: int(v) for k, v in endm.groupdict().items()})
    return starttime, endtime

def _to_string(offsets):
    return "{} --> {}".format(offsets[0], offsets[1])

class Subtitle():
    def __init__(self, block):
        self.number = int(block[0])
        self.offsets = _read_offsets(block[1])
        self.content = '\r\n'.join(block[2:])

    def __str__(self):
        return "\r\n".join([str(self.number), _to_string(self.offsets), self.content])

def parse(content):
    return [Subtitle(block) for block in _by_block(content)]

def skew(total, current, to_nudge):
    percent = current / total
    return current + (percent * to_nudge)

def nudge(subtitles, to_nudge):
    end = subtitles[-1]
    total_seconds = end.offsets[1].total_seconds
    for subtitle in subtitles:
        start, end = subtitle.offsets
        newstart = skew(total_seconds, start.total_seconds, to_nudge)
        newend = skew(total_seconds, end.total_seconds, to_nudge)
        subtitle.offsets = Timestamp.from_seconds(newstart), Timestamp.from_seconds(newend)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='The file to operate on')
    parser.add_argument('to_nudge', type=int, help='The amount in seconds to linearly nudge the subtitles')
    args = parser.parse_args()

    with codecs.open(args.input, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    subtitles = parse(content)

    nudge(subtitles, args.to_nudge)
    for subtitle in subtitles:
        print(subtitle)

if __name__ == '__main__':
    main()
