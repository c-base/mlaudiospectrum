#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
Experimental Audio spectrum for mate light.
The calculations needs still some improvement!
The low frequencies are too dominant at this state.
"""

__author__ = 'Road Runner, Willy Coyote'
__copyright__ = 'Copyright 2014, Acme Inc.'
__credits__ = ['Road Runner', 'Road Runners best friend Harrold']
__license__ = 'MIT'
__version__ = '0.0.1'
__maintainer__ = 'Road Runners other friend Herb'
__email__ = 'appteam@acme.com'
__status__ = 'Development'

from sys import byteorder
from array import array
from struct import pack

import matplotlib.pyplot as plt

import pygame
import pyaudio
import wave
import numpy
import math
import time
import socket
import struct
from random import randint

THRESHOLD = 256
CHUNK_SIZE = 84
DB_NOISE_CORRECTION = 40
DROP_CHUNKS = 1
CHUNKS = 1
FORMAT = pyaudio.paInt16
RATE = 8192
SPACING = RATE / float(CHUNK_SIZE * CHUNKS)

ML_HEIGHT = 16
ML_WIDTH  = 40
MAX_AUDIO_HEIGHT = 100


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
    IP = "matelight.cbrp3.c-base.org"
    #IP = "localhost"
    PORT = 1337

    # scale resolution to matelight
    input_width = len(spectrum_list)
    width = input_width # TODO: scale
    height = ML_HEIGHT

    ml_buffer = numpy.zeros((ML_WIDTH, ML_HEIGHT))

    for x in range(len(spectrum_list)):
        pix_heigt = int(spectrum_list[x] * ML_HEIGHT / (MAX_AUDIO_HEIGHT - DB_NOISE_CORRECTION)) # scale fft height to matelight heigt
        for y in range(ML_HEIGHT - 1, ML_HEIGHT - pix_heigt, -1):
            ml_buffer[x][y] = bar_colors[y]

    checksum = "\x00\x00\x00\x00"

    image = ""

    for y in range(ML_HEIGHT):
        for x in range(ML_WIDTH):
            r = int(ml_buffer[x][y])          & 0xFF
            g = (int(ml_buffer[x][y]) >> 8)   & 0xFF
            b = (int(ml_buffer[x][y]) >> 16)  & 0xFF

            image += struct.pack('BBB', r, g, b)

    image += checksum

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(image, (IP, PORT))

def main():
    pygame.init()

    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)

    X = [s * SPACING for s in range(CHUNK_SIZE * CHUNKS / 2 - 1)][DROP_CHUNKS:]
    psd = len(X) * [0]

    psd[0] = 0
    psd[1] = 150

    plt.ion()
    graph = plt.plot(X, psd)[0]

    plt.ylabel('Volume (dB)')
    plt.xlabel('frequency (Hz)')
    plt.pause(0.00001)


    while True:
        r = array('h')
        for i in range(CHUNKS):
            # little endian, signed short
            stream.read(500 - CHUNK_SIZE)
            snd_data = array('h', stream.read(CHUNK_SIZE))
            #snd_data = [randint(0, 16000) for z in range(CHUNK_SIZE)]
            if byteorder == 'big':
                snd_data.byteswap()
            r.extend(snd_data)

        fft = numpy.fft.fft(r)
        dc, fft = fft[0], fft[1 + DROP_CHUNKS:]
        psd = [20 * math.log10(0.000001 + math.sqrt(x.real**2 + x.imag**2)) - DB_NOISE_CORRECTION for x in fft][1 + DROP_CHUNKS:len(r) / 2]
        psd = [p if p > 0 else 0 for p in psd]

        sendSpectrumToMateLight(psd)
        graph.set_ydata(psd)
        plt.pause(0.00001)

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    return sample_width, r


if __name__ == '__main__':
    main()