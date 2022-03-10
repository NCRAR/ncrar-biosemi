from pathlib import Path
import time

import matplotlib.pyplot as plt
import numpy as np

from ncrar_audio import babyface
from psiaudio.stim import read_wav


stim_path = Path(__file__).parent / 'stim'


n_blocks = 3
n_target = 25
n_non_target = 100
n_trials = n_target + n_non_target


rng = np.random.RandomState()



def main_play():
    sd = babyface.Babyface('earphones', 'XLR1', use_osc=False)
    stim_set = {
        'ga': read_wav(sd.fs, stim_path / 'fcv10a_ga.wav'),
        'ba': read_wav(sd.fs, stim_path / 'fcv08a_ba.wav'),
    }

    stim = stim_set['ba']
    recording = sd.play_mono(stim, 'left')
    recording = sd.play_mono(stim, 'right')
    return

    sm = stim.max(axis=-1)
    rm = recording.max(axis=-1)
    print(20*np.log10(sm/rm))

    figure, axes = plt.subplots(1, 2)
    axes[0].plot(stim[0], label='stim')
    axes[0].plot(recording[0], label='recording')
    axes[1].plot(stim[1])
    axes[1].plot(recording[1])
    axes[0].legend()
    plt.show()


if __name__ == '__main__':
    seq = generate_nback0(syllables)

    #try:
    #    check_sequence_nback0(['ba', 'ga', 'ba', 'ya', 'ba', 'da', 'ba'], 'ba', 3)
    #    print('success')
    #except Exception as e:
    #    print(e)
    #try:
    #    check_sequence_nback0(['ba', 'ga', 'ba', 'ba', 'ga', 'da', 'ba'], 'ba', 3)
    #    print('success')
    #except Exception as e:
    #    print(e)
    #try:
    #    check_sequence_nback0(['ba', 'ga', 'ba', 'ya', 'ga', 'ba', 'ba'], 'ba', 3)
    #    print('success')
    #except Exception as e:
    #    print(e)
    #try:
    #    check_sequence_nback0(['ba', 'ga', 'ba', 'ya', 'ya', 'ga', 'ba'], 'ba', 2)
    #    print('success')
    #except Exception as e:
    #    print(e)
