import asyncio
from functools import partial
import json
from pathlib import Path
from threading import Thread
import time

from atom.api import Atom, Dict, Enum, Int, List, Str, observe, Property, Value
from enaml.application import deferred_call
import numpy as np

from psiaudio.stim import read_wav
from ncrar_audio import babyface, cpod

from .sequence import generate_nback0_sequence, generate_nback_sequence
from .psi_controller import PSIController
from .util import BiosemiEncoder


data_path = Path('c:/ncrar-biosemi/n-back')


def load_stim_set(fs):
    stim_path = Path(__file__).parent / 'stim'
    stim = {}
    for filename in stim_path.glob('*.wav'):
        syllable = filename.stem.rsplit('_', 1)[1]
        stim[syllable] = read_wav(fs, filename)
    return stim


async def nback(n_back, config, filename, exclude_targets=None, trial_cb=None):
    filename = Path(filename)

    rng = np.random.RandomState()
    if trial_cb is None:
        def trial_cb(s, i, n):
            print(f'{s}: {i}: {n}')
    if exclude_targets is None:
        exclude_targets = []

    sd = babyface.Babyface('earphones', 'XLR', use_osc=False)
    cp = cpod.CPod()
    wav_files = load_stim_set(sd.fs)
    syllables = sorted(list(wav_files.keys()))

    settings = {
        'version': '0.0.1',
        'syllables': syllables,
        'n_targets': config.n_targets,
        'n_trials': config.n_trials,
        'n_back': n_back,
    }

    # The N-back 0 special case.
    if n_back == 0:
        target_options = [s for s in syllables if s not in exclude_targets]
        target = rng.choice(target_options)
        settings['target'] = target
        sequence = generate_nback0_sequence(syllables, target,
                                            config.n_targets, config.n_trials,
                                            rng)
    else:
        # N-back 1 and 2 case.
        if len(exclude_targets):
            m = f'exclude_targets not supported when n_back={n_back}'
            raise ValueError(m)
        sequence = generate_nback_sequence(n_back, syllables, config.n_targets,
                                           config.n_trials, rng)
    settings['sequence'] = sequence
    config.experiment_info.set_current_sequence(sequence)

    config.experiment_info.set_current_stim(sequence[0])
    config.experiment_info.score_stim(sequence[0], True)
    config.experiment_info.set_current_stim(sequence[1])
    config.experiment_info.score_stim(sequence[1], False)
    config.experiment_info.set_current_stim(sequence[2])
    config.experiment_info.score_stim(sequence[2], False)
    config.experiment_info.set_current_stim(sequence[3])
    config.experiment_info.score_stim(sequence[3], False)
    config.experiment_info.set_current_stim(sequence[4])

    results = []
    try:
        async with PSIController('ws://localhost:8765') as psi:
            await psi.running()
            for stim in sequence:
                config.experiment_info.set_current_stim(stim)
                with cp.set_code(stim.encode()):
                    wav = wav_files[stim.stim]
                    sd.play_stereo(wav)
                iti = np.random.uniform(1.5, 2.5)
                result, = await psi.monitor(iti)
                config.experiment_info.score_stim(stim, result['is_correct'])
                result['iti'] = iti
                results.append(result)
    except Exception as exc:
        settings['error'] = str(exc)
        filename = filename.parent / f'{filename.stem}_incomplete'
    finally:
        settings['results'] = results
        with filename.with_suffix('.json').open('w') as fh:
            json.dump(settings, fh, cls=BiosemiEncoder, indent=2)


available_experiments = {
    0: partial(nback, 0),
    1: partial(nback, 1),
    2: partial(nback, 2),
}


class ExperimentInfo(Atom):

    current_sequence = List()
    current_stim = Value()

    def set_current_sequence(self, sequence):
        deferred_call(setattr, self, 'current_sequence', sequence)

    def set_current_stim(self, stim):
        deferred_call(setattr, self, 'current_stim', stim)

    def score_stim(self, stim, is_correct):
        deferred_call(setattr, stim, 'is_correct', is_correct)


class ExperimentConfig(Atom):

    subject_id = Str()
    n_targets = Int(2)
    n_trials = Int(10)
    filename = Property()
    experiment = Enum(*list(available_experiments.keys()))

    current_runs = Dict()
    current_targets = Dict()

    experiment_info = ExperimentInfo()
    thread = Value()

    @observe('subject_id')
    def _check_current_runs(self, event=None):
        current_runs = {}
        current_targets = {}
        for i in available_experiments.keys():
            runs = [-1]
            targets = []
            pattern = f'{self.subject_id}_N{i}_run*_complete.json'
            for filename in data_path.glob(pattern):
                if 'practice' in filename.stem:
                    continue
                run = filename.stem.rsplit('_', 2)[1]
                run = int(run[3:])
                runs.append(run)
                targets.append(json.loads(filename.read_text())['target'])
            current_runs[i] = max(runs) + 1
            current_targets[i] = targets

        # Be sure to set runs *after* targets since this is what I'm listening
        # for in the GUI to update.
        self.current_targets = current_targets
        self.current_runs = current_runs

    def run(self, practice):
        if self.thread is not None and self.thread.is_alive():
            self.thread.stop()

        cb = available_experiments[self.experiment]
        run = self.current_runs[self.experiment]
        base_filename = f'{self.subject_id}_N{self.experiment}_run{run}'
        if practice:
            base_filename = f'{base_filename}_practice'
        else:
            base_filename = f'{base_filename}'
        filename = data_path / base_filename
        exclude = self.current_targets[self.experiment]

        coroutine = cb(self, filename, exclude_targets=exclude)
        loop = asyncio.get_event_loop()
        task = loop.create_task(coroutine)
        self.thread = Thread(target=asyncio.run, kwargs={'main': coroutine})
        self.thread.start()


if __name__ == '__main__':
    config = ExperimentConfig()
    asyncio.run(nback(1, config, 'test.txt'))
