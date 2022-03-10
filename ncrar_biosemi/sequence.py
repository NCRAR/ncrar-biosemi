import numpy as np


'''
C-pod channel details

    0: Experiment (high = experiment running)

    7: High = can read lines 8-15.
    8-15: Stim code.
'''


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


def generate_nback0_sequence(syllables, target, n_target, n_trials, rng):
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


if __name__ == '__main__':
    syllables = ['ra', 'ga', 'ya', 'la', 'ka', 'sha', 'pa', 'da', 'ma', 'wa',
                 'sa', 'na']
    blocks = generate_nback0_blocks(syllables, 3, 5, 25)
    for block in blocks:
        print(block)

    for stim in block:
        print(stim, stim.encode(), Stim.decode(stim.encode(), syllables))

