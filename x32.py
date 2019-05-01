#!/usr/bin/env python3

"""
Audio spectrum analyzer for mate light which talks over OSC to a Behringer X32 Rack as a data source.

# TODO:
# - use UDP socket directly instead of scapy
# - do not poll batchsubscribe OSC msg. after subscribing, the x32-rack should xmit its spectrum data
    # automatically with an interval of 50ms for about 10s.
# - The provides 100 frequencies but matelight is only able to display 40 since it consists of 40 columns. At this point
    every second frequency is taken and afterwards the first 5 and last 5 frequencies are cut to get to 40 columns.
    It would be better implementing some kind of interpolation.
# - Add peak hold bars
"""

__author__ = 'coon, uk'
__copyright__ = 'Copyright 2019, c-base e.V.'
__version__ = '0.1'
__email__ = 'coon@c-base.org, uk@c-base.org'
__status__ = 'Prototype'

from scapy.layers.inet import IP, UDP
from scapy.all import Raw
from scapy.sendrecv import sr1
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


while True:
    # TODO: - replace scapy.sr1() by socket.sendto()
    #       - do not poll batchsubscribe msg. after subscribing, the x32-rack should xmit its spectrum data
    #         automatically with an interval of 50ms for about 10s.

    response = sr1(IP(dst='10.0.1.37')/UDP(sport=12345, dport=10023)/Raw(load=payload))
    l = list(dec(response.load))[::2][5:-5] # only use every second bar and cut off the first 5 and the last 5 bars
    l = [2 * i for i in l] # double the gain
    termplot.plot([128] + l)
    sendSpectrumToMateLight(l)
