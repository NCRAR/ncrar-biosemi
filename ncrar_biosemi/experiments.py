import logging
log = logging.getLogger(__name__)

import asyncio
from functools import partial
import json
from pathlib import Path
from threading import Thread
import time

from atom.api import (Atom, Bool, Dict, Enum, Event, Int, List, Str, observe,
                      Property, Typed, Value)
from enaml.application import deferred_call
import numpy as np

from ncrar_audio import babyface, cpod
from psiaudio.stim import read_wav

from .sequence import generate_nback0_sequence, generate_nback_sequence
from .psi_controller import PSIController
from .util import BiosemiEncoder


data_path = Path('c:/ncrar-biosemi/n-back')


def load_stim_set(fs):
    '''
    Loads set of syllables used for N-Back experiment
    '''
    stim_path = Path(__file__).parent / 'stim'
    stim = {}
    for filename in stim_path.glob('*.wav'):
        syllable = filename.stem.rsplit('_', 1)[1]
        stim[syllable] = read_wav(fs, filename)
    return stim


async def nback(n_back, config, filename, exclude_targets=None):
    '''
    Runs the n-back experiment
    '''
    # This is a hack to allow sounddevice to work in a new thread. For some
    # reason the PortAudio bindings to the ASIO drivers (or the ASIO drivers --
    # who knows) do not allow us to call them in a thread separate from the one
    # where the library was loaded.
    import importlib
    import sounddevice
    sounddevice._ffi.dlclose(sounddevice._lib)
    importlib.reload(sounddevice)

    filename = Path(filename)
    incomplete_filename = filename.parent / f'{filename.stem}_incomplete'
    complete_filename = filename.parent / f'{filename.stem}_complete'

    rng = np.random.RandomState()
    if exclude_targets is None:
        exclude_targets = []

    sd = babyface.Babyface('earphones', 'XLR', use_osc=False)
    wav_files = load_stim_set(sd.fs)

    sd.play_stereo(wav_files['wa'])
    cp = cpod.CPod()
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
    results = []
    try:
        async with PSIController('ws://localhost:8765') as psi:
            await psi.running()
            # Now, sleep for 1 sec to ensure that we can capture baseline
            # before first stim.
            time.sleep(1)
            for stim in sequence:
                config.experiment_info.set_current_stim(stim)
                with cp.set_code(stim.encode()):
                    wav = wav_files[stim.stim]
                    sd.play_stereo(wav)
                iti = np.random.uniform(1.5, 2.5)
                result = await psi.monitor(iti)
                if len(result) != 1:
                    log.error('We failed to get the trigger for this stim')
                    result = {}
                else:
                    result = result[0]
                    result['iti'] = iti
                    config.experiment_info.score_stim(stim, result['is_correct'])
                results.append(result)
        if incomplete_filename.exists():
            incomplete_filename.unlink()
    except Exception as exc:
        raise
        settings['error'] = str(exc)
    finally:
        if len(results) !=  len(sequence):
            filename = incomplete_filename
        else:
            filename = complete_filename
        settings['results'] = results
        with filename.with_suffix('.json').open('w') as fh:
            json.dump(settings, fh, cls=BiosemiEncoder, indent=2)
        config.experiment_info.mark_complete()


available_experiments = {
    0: partial(nback, 0),
    1: partial(nback, 1),
    2: partial(nback, 2),
}


class ExperimentInfo(Atom):

    current_sequence = List()
    current_stim = Value()
    complete = Bool(False)

    def set_current_sequence(self, sequence):
        deferred_call(setattr, self, 'current_sequence', sequence)

    def set_current_stim(self, stim):
        deferred_call(setattr, self, 'current_stim', stim)

    def score_stim(self, stim, is_correct):
        deferred_call(setattr, stim, 'is_correct', is_correct)

    def mark_complete(self):
        self.set_current_stim(None)
        deferred_call(setattr, self, 'complete', True)


class ExperimentConfig(Atom):

    subject_id = Str()
    n_targets = Int(20)
    n_trials = Int(120)
    filename = Property()
    experiment = Enum(*list(available_experiments.keys()))

    current_runs = Dict()
    current_targets = Dict()

    experiment_info = Typed(ExperimentInfo)
    base_filename = Typed(Path)
    thread = Value()

    def _default_experiment_info(self):
        # Subscribe to complete attribute so that we can ensure that the
        # current runs for the subject are updated at completion of an
        # experiment.
        ei = ExperimentInfo()
        ei.observe('complete', self._check_current_runs)
        return ei

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
                config = json.loads(filename.read_text())
                if 'target' in config:
                    targets.append(config['target'])
            current_runs[i] = max(runs) + 1
            current_targets[i] = targets

        # Be sure to set runs *after* targets since this is what I'm listening
        # for in the GUI to update.
        self.current_targets = current_targets
        self.current_runs = current_runs

    def get_base_filename(self, practice):
        run = self.current_runs[self.experiment]
        base_filename = f'{self.subject_id}_N{self.experiment}_run{run}'
        if practice:
            base_filename = f'{base_filename}_practice'
        return data_path / base_filename

    def run(self, practice):
        if self.thread is not None and self.thread.is_alive():
            self.thread.stop()

        self.experiment_info.complete = False
        self.base_filename = self.get_base_filename(practice)
        cb = available_experiments[self.experiment]
        coroutine = cb(
            self,
            self.base_filename,
            exclude_targets=self.current_targets[self.experiment]
        )
        loop = asyncio.get_event_loop()
        task = loop.create_task(coroutine)
        self.thread = Thread(target=asyncio.run, kwargs={'main': coroutine})
        self.thread.start()


if __name__ == '__main__':
    config = ExperimentConfig()
    asyncio.run(nback(1, config, 'test.txt'))
