from collections import Counter
import numpy as np


class Stim:

    def __init__(self, stim, is_target, is_response, stim_index):
        self.__dict__.update(locals())
        self.is_correct = None

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


################################################################################
# N-back 0
################################################################################
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


################################################################################
# Common (for N-back 1 and up)
################################################################################
def get_targets(syllables, n_target, rng):
    '''
    Now, randomly select targets (without replacement) from the list of
    syllables. If we run out of syllables, then we will repeat (this
    essentially balances the presentations of the syllables).
    '''
    syllables = sorted(syllables)
    targets = []
    while len(targets) < n_target:
        n = n_target - len(targets)
        rng.shuffle(syllables)
        targets.extend(syllables[:n])
    return targets


def get_indices(n_back, n_target, n_trials, rng):
    # N-back requires two slots (for the repeat) plus one slot after so that
    # we don't have back-to-back repeats. Then, we need to account for the
    # sandwich filler (i.e., n_back - 1).
    if (n_target * ((n_back - 1) + 3)) >= n_trials:
        raise ValueError(f'Cannot encode {n_target} repeats in {n_trials} trials')

    target_indices = []
    # The index is the time of the first syllable in the sandwich. It can occur
    # anytime after the very first slot (i.e., slot 1 in a zero-based numbering
    # system), but we need to make sure that the "first" syllable in the
    # sandwich does not occur too close to the end otherwise we can't finish
    # the sandwich.
    indices = set(range(1, n_trials-n_back))
    for _ in range(n_target):
        i = rng.choice(list(indices))
        target_indices.append(i)
        # Now, discard a window around the sandwich to make sure another
        # sandwich does not occur too close to this one.
        for j in range(-1-n_back, 2+n_back):
            indices.discard(i+j)

    return target_indices


def get_filler(n_back, syllables, exclude, rng):
    filler = [s for s in syllables if s not in exclude]
    syllable = rng.choice(filler)
    stim_index = syllables.index(syllable)
    stim = Stim(syllable, False, False, stim_index)
    return stim


def get_sequence(n_back, syllables, targets, target_indices, n_trials, rng):
    target_indices.sort()
    syllables = sorted(syllables)
    sequence = []
    next_target = targets.pop(0)
    next_target_index = target_indices.pop(0)
    while len(sequence) < n_trials:
        if len(sequence) == next_target_index:
            # Create the repeat
            stim_index = syllables.index(next_target)
            stim = Stim(next_target, True, False, stim_index)
            sequence.append(stim)

            for i in range(n_back - 1):
                exclude = [next_target, sequence[-n_back].stim]
                stim = get_filler(n_back, syllables, exclude, rng)
                sequence.append(stim)

            stim = Stim(next_target, True, True, stim_index)
            sequence.append(stim)

            # Now, update to the next target/target index
            try:
                next_target = targets.pop(0)
                next_target_index = target_indices.pop(0)
            except:
                next_target = None
                next_target_index = n_trials + 2
        else:
            # Not beginning of a repetition. Just pick a filler.
            exclude = []
            if len(sequence) >= n_back:
                # Make sure we don't accidentally create a sandwich with the
                # syllable n_back ago.
                exclude.append(sequence[-n_back].stim)

            if (len(sequence) + n_back) == next_target_index:
                # Now, make sure we don't accidentally create a sandwich "early".
                exclude.append(next_target)

            stim = get_filler(n_back, syllables, exclude, rng)
            sequence.append(stim)

    return sequence


def generate_nback_sequence(n_back, syllables, n_target, n_trials, rng=None):
    if n_back == 0:
        raise ValueError('Use the generate_nback0_sequence function instead')

    if rng is None:
        rng = np.random.RandomState()

    targets = get_targets(syllables, n_target, rng)
    target_indices = get_indices(n_back, n_target, n_trials, rng)
    sequence = get_sequence(n_back, syllables, targets, target_indices, n_trials, rng)
    check_sequence_nback(n_back, sequence, n_target, n_trials)
    return sequence


def check_sequence_nback(n_back, sequence, n_target, n_trials):
    if len(sequence) != n_trials:
        raise ValueError('Incorrect number of trials')
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
        if i >= (n_trials - n_back):
            continue
        if stim.is_target and not stim.is_response:
            if sequence[i-n_back].stim == stim.stim:
                raise ValueError('Spurious repetition before')
        if stim.is_response and i < n_trials:
            if sequence[i+n_back].stim == stim.stim:
                raise ValueError('Spurious repetition after')
    resp_i = np.array([i for i, s in enumerate(sequence) if s.is_response])
    if np.any(np.diff(resp_i) < (2 + n_back)):
        raise ValueError('Repeats too close together')
    if sequence[0].is_target:
        raise ValueError('Target too close to beginning')


if __name__ == '__main__':
    syllables = ['ra', 'ga', 'ya', 'la', 'ka', 'sha', 'pa', 'da', 'ma', 'wa',
                 'sa', 'na']

    #block = generate_nback_sequence(0, syllables, 5, 20)
    #print(block)

    #block = generate_nback_sequence(1, syllables, 5, 20)
    #print(block)

    block = generate_nback_sequence(2, syllables, 3, 20)
    print(len(block))
    print(block)
