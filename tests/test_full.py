import os
from io import BytesIO

import numpy as np

from amodem import send
from amodem import recv
from amodem import common
from amodem import dsp
from amodem import sampling

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-12s %(message)s')


class Args(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run(size, chan=None, df=0, success=True):
    tx_data = os.urandom(size)
    tx_audio = BytesIO()
    send.main(Args(silence_start=1, silence_stop=1,
              input=BytesIO(tx_data), output=tx_audio))

    data = tx_audio.getvalue()
    data = common.loads(data)
    if chan is not None:
        data = chan(data)
    if df:
        sampler = sampling.Sampler(data, sampling.Interpolator())
        sampler.freq += df
        data = sampler.take(len(data))

    data = common.dumps(data)
    rx_audio = BytesIO(data)

    rx_data = BytesIO()
    result = recv.main(Args(skip=0, input=rx_audio, output=rx_data))
    rx_data = rx_data.getvalue()

    assert result == success
    if success:
        assert rx_data == tx_data


def test_small():
    run(1024, chan=lambda x: x)


def test_error():
    skip = 1 * send.config.Fs  # remove trailing silence
    run(1024, chan=lambda x: x[:-skip], success=False)


def test_frequency_error():
    for ppm in [0.1, 1, 10]:
        for sign in [+1, -1]:
            run(1024, df=sign*ppm*1e-6)


def test_lowpass():
    run(1024, chan=lambda x: dsp.lfilter(b=[0.9], a=[1.0, -0.1], x=x))


def test_highpass():
    run(1024, chan=lambda x: dsp.lfilter(b=[0.9], a=[1.0, 0.1], x=x))


def test_attenuation():
    run(5120, chan=lambda x: x * 0.1)


def test_low_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.0001))


def test_medium_noise():
    r = np.random.RandomState(seed=0)
    run(5120, chan=lambda x: x + r.normal(size=len(x), scale=0.001))


def test_large():
    run(54321, chan=lambda x: x)
