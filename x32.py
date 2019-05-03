#!/usr/bin/env python3

"""
Audio spectrum analyzer for mate light which talks over OSC to a Behringer X32 Rack as a data source.

# TODO:
# - The provides 100 frequencies but matelight is only able to display 40 since it consists of 40 columns. At this point
    every second frequency is taken and afterwards the first 5 and last 5 frequencies are cut to get to 40 columns.
    It would be better implementing some kind of interpolation.
# - Add peak hold bars
"""

__author__ = 'coon, uk'
__copyright__ = 'Copyright 2019, c-base e.V.'
__version__ = '0.2'
__email__ = 'coon@c-base.org, uk@c-base.org'
__date__ = '2019-05-03'
__status__ = 'Prototype'

import struct
import numpy
import termplot
import time
import socket

ML_HEIGHT = 16
ML_WIDTH  = 40
MAX_AUDIO_HEIGHT = 128

def RGB(red, green, blue):
    return red | green << 8 | blue << 16

bar_colors = [
    RGB(255, 0,     0),
    RGB(255, 0,     0),
    RGB(255, 0,     0),
    RGB(255, 0,     0),
    RGB(255, 64,   15),
    RGB(255, 127,  36),
    RGB(255, 127,  36),
    RGB(255, 127,  36),
    RGB(255, 200,   0),
    RGB(255, 255,   0),
    RGB(255, 255,   0),
    RGB(255, 255,   0),
    RGB(192, 255,   0),
    RGB(0,   255,   0),
    RGB(0,   255,   0),
    RGB(0,   255,   0)
]

def sendSpectrumToMateLight(spectrum_list):
    IP = "matelight"
    PORT = 1337

    ml_buffer = numpy.zeros((ML_WIDTH, ML_HEIGHT))

    for x in range(len(spectrum_list)):
        pix_heigt = int(spectrum_list[x] * ML_HEIGHT / MAX_AUDIO_HEIGHT)
        for y in range(ML_HEIGHT - 1, ML_HEIGHT - pix_heigt, -1):
            ml_buffer[x][y] = bar_colors[y]

    checksum = b'\x00\x00\x00\x00'

    image = b''

    for y in range(ML_HEIGHT):
        for x in range(ML_WIDTH):
            r = int(ml_buffer[x][y])          & 0xFF
            g = (int(ml_buffer[x][y]) >> 8)   & 0xFF
            b = (int(ml_buffer[x][y]) >> 16)  & 0xFF

            image += struct.pack('BBB', r, g, b)

    image += checksum

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(image, (IP, PORT))

payload = '/batchsubscribe\x00,ssiii\x00\x00meters/15\x00\x00\x00/meters/15\x00\x00\x00\x00\x00\x10\x00\x00\x00\x10\x00\x00\x00\x01'

def dec(data):
    for i in range(23, len(data), 2):
        b = bytearray(data[i:i+2])
        if len(b) < 2:
            continue

        d = struct.unpack('>H', b)
        f = 128 + numpy.short(d[0]) / 256.0
        yield f

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
start = 0

while True:
    if time.time() - start >= 1:
        # TODO: xmit /renew instead of /batchsubscribe again?
        sock.sendto(payload.encode(), ('x32rack', 10023))
        start = time.time()

    response = sock.recvfrom(1024)[0]

    l = list(dec(response))
    l = l[::2] # only use every second bar
    l = l[5:-5] # cut off the first 5 and the last 5 bars
    l = [2 * i for i in l] # double the gain
    termplot.plot([128] + l)
    sendSpectrumToMateLight(l)

