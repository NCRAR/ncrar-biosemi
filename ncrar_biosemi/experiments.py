import asyncio
from pathlib import Path

from atom.api import Atom, Int, Str

from . import sequence
from .psi_controller import PSIController
from psiaudio.stim import read_wav
from ncrar_audio import babyface, cpod

import time


class ExperimentConfig(Atom):

    subject_id = Str()
    note = Str()
    n_blocks = Int(3)
    n_targets = Int(5)
    n_trials = Int(25)


def load_stim_set(fs):
    stim_path = Path(__file__).parent / 'stim'
    stim = {}
    for filename in stim_path.glob('*.wav'):
        syllable = filename.stem.rsplit('_', 1)[1]
        stim[syllable] = read_wav(fs, filename)
    return stim


async def nback_0(config):
    sd = babyface.Babyface('earphones', 'XLR', use_osc=False)
    cp = cpod.CPod()
    wav_files = load_stim_set(sd.fs)
    syllables = sorted(list(wav_files.keys()))
    blocks = sequence.generate_nback0_blocks(syllables, config.n_blocks,
                                             config.n_targets, config.n_trials)

    async with PSIController('ws://localhost:8765') as psi:
        await psi.start()

        # Now, walk through the blocks!
        for block in blocks:
            for stim in block:
                with cp.set_code(stim.encode()):
                    sd.play_stereo(wav_files[stim.stim])
                results = await psi.monitor(0.5)
                print(results)


def nback_1():
    print('Launching N-back 1')


def nback_2():
    print('Launching N-back 2')


available_experiments = {
    'N-Back 0': nback_0,
    'N-Back 1': nback_1,
    'N-Back 2': nback_2,
}


if __name__ == '__main__':
    config = ExperimentConfig()
    asyncio.run(nback_0(config))
