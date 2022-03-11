from collections import Counter
import numpy as np


class Stim:

    def __init__(self, stim, is_target, is_response, stim_index):
        self.__dict__.update(locals())

    def encode(self):
        return self.is_target | \
            (self.is_response << 1) | \
            (self.stim_index << 2)

    @classmethod
    def decode(cls, value, stim=None):
        stim = sorted(stim)
        result = {
            'is_target': value & 1,
            'is_response': (value >> 1) & 1,
            'stim_index': (value >> 2),
        }
        result['stim'] = stim[result['stim_index']]
        return cls(**result)

    def __repr__(self):
        if self.is_target and self.is_response:
            return f'*{self.stim.upper()}'
        if self.is_target:
            return self.stim.upper()
        return self.stim.lower()


def generate_nback0_blocks(syllables, n_blocks, n_target, n_trials):
    rng = np.random.RandomState()
    targets = []
    sequences = []
    for block in range(n_blocks):
        if len(targets) == 0:
            targets = syllables.copy()
            rng.shuffle(targets)
        target = targets.pop(0)
        sequence = generate_nback0_sequence(syllables, target, n_target,
                                            n_trials, rng)
        sequences.append(sequence)
    return sequences


def generate_nback0_sequence(syllables, target, n_target, n_trials, rng=None):
    if rng is None:
        rng = np.random.RandomState()

    syllables = sorted(syllables)
    nontarget = syllables.copy()
    nontarget.remove(target)

    indices = set(range(2, n_trials))

    target_indices = [0]
    for _ in range(n_target):
        i = rng.choice(list(indices))
        target_indices.append(i)
        indices.discard(i-1)
        indices.discard(i)
        indices.discard(i+1)

    target_indices.sort()
    if np.any(np.diff(target_indices) < 2):
        raise ValueError('Bad target sequence')

    sequence = []
    for i in range(n_trials):
        if i in target_indices:
            syllable = target
            is_target = True
            is_response = i != 0
        else:
            syllable = rng.choice(nontarget)
            is_target = False
            is_response = False
        stim_index = syllables.index(syllable)
        stim = Stim(syllable, is_target, is_response, stim_index)
        sequence.append(stim)

    check_sequence_nback0(sequence, target, n_target)
    return sequence


def check_sequence_nback0(sequence, target, n_target):
    seq = np.array([s.stim for s in sequence])
    if np.sum(seq == target) != (n_target + 1):
        raise ValueError('Target not represented correctly')
    if np.any((seq[:-1] == target) & (seq[:-1] == seq[1:])):
        raise ValueError('Target repeated!')


def generate_nback1_sequence(syllables, n_target, n_trials, rng=None):
    if rng is None:
        rng = np.random.RandomState()

    if (n_target * 3) >= n_trials:
        raise ValueError(f'Cannot encode {n_target} repeats in {n_trials} trials')

    syllables = sorted(syllables)
    targets = []
    while len(targets) < n_target:
        n = n_target - len(targets)
        rng.shuffle(syllables)
        targets.extend(syllables[:n])

    target_indices = []
    indices = set(range(1, n_trials-1))
    for _ in range(n_target):
        i = rng.choice(list(indices))
        target_indices.append(i)
        for j in range(-2, 3):
            indices.discard(i+j)

    target_indices.sort()
    syllables = sorted(syllables)
    i = 0
    sequence = []
    next_target = targets.pop(0)
    next_target_index = target_indices.pop(0)
    while i < n_trials:
        if i == next_target_index:
            # Create the repeat
            stim_index = syllables.index(next_target)
            stim = Stim(next_target, True, False, stim_index)
            sequence.append(stim)
            stim = Stim(next_target, True, True, stim_index)
            sequence.append(stim)
            i += 2

            # Now, update to the next target/target index
            try:
                next_target = targets.pop(0)
                next_target_index = target_indices.pop(0)
            except:
                next_target = None
                next_target_index = n_trials + 2
        else:
            # Not beginning of a repetition. Just pick a filler.
            filler = syllables.copy()
            if len(sequence) > 0:
                filler.remove(sequence[-1].stim)
            if (i + 1) == next_target_index:
                try:
                    filler.remove(next_target)
                except:
                    # This will occur if it was already removed because the
                    # previous stim was that.
                    pass

            syllable = rng.choice(filler)
            stim_index = syllables.index(syllable)
            stim = Stim(syllable, False, False, stim_index)
            sequence.append(stim)
            i += 1

    check_sequence_nback1(sequence, n_target, n_trials)
    return sequence


def check_sequence_nback1(sequence, n_target, n_trials):
    response = np.array([s.is_response for s in sequence])
    if np.sum(response) != n_target:
        raise ValueError('Not enough targets')
    target = np.array([s.is_target for s in sequence])
    if np.sum(target) != (n_target * 2):
        raise ValueError('Target not repeated properly')
    tar_seq = np.array([s.stim for s in sequence if s.is_target])
    if not np.all(tar_seq[:-1:2] == tar_seq[1::2]):
        raise ValueError('Target not repeated properly')
    resp_seq = np.array([s.stim for s in sequence if s.is_response])
    counter = Counter(resp_seq)
    counts = np.fromiter(counter.values(), 'int')
    if counts.ptp() > 1:
        raise ValueError('Targets not balanced properly')
    for i, stim in enumerate(sequence):
        if i == 0:
            continue
        if i == (n_trials - 1):
            continue
        if stim.is_target and not stim.is_response:
            if sequence[i-1].stim == stim.stim:
                raise ValueError('Spurious repetition before')
        if stim.is_response and i < n_trials:
            if sequence[i+1].stim == stim.stim:
                raise ValueError('Spurious repetition after')
    resp_i = np.array([i for i, s in enumerate(sequence) if s.is_response])
    if np.any(np.diff(resp_i) < 3):
        raise ValueError('Repeats too close together')
    if sequence[0].is_target:
        raise ValueError('Target too close to beginning')


if __name__ == '__main__':
    syllables = ['ra', 'ga', 'ya', 'la', 'ka', 'sha', 'pa', 'da', 'ma', 'wa',
                 'sa', 'na']
    #block = generate_nback0_sequence(syllables, 'ra', 5, 25)
    block = generate_nback1_sequence(syllables, 5, 20)
    print(block)

    #for stim in block:
    #    print(stim, stim.encode(), Stim.decode(stim.encode(), syllables))
