from json import JSONEncoder

from .sequence import Stim


class BiosemiEncoder(JSONEncoder):

    def default(self, o):
        if isinstance(o, Stim):
            result = o.__dict__.copy()
            result.pop('self')
            return result
        return super().default(o)
