from .job import AbstractJob

class Sequence:

    def __init__(self, *sequences_or_jobs, required=None):
        self.jobs = self.flatten(sequences_or_jobs)
        # create the chain of requirements in the sequence
        for previous, next in zip(self.jobs, self.jobs[1:]):
            next.requires(previous)
        # any requirements specified in the constructor
        # actually apply to the first item
        if self.jobs:
            self.jobs[0].requires(required)

    @staticmethod
    def flatten(sequences_or_jobs):
        """
        given a list of objects typed either AbstractJob or Sequence
        returns an ordered list of jobs
        """
        result = []
        for x in sequences_or_jobs:
            if x is None:
                continue
            if isinstance(x, AbstractJob):
                result.append(x)
            elif isinstance(x, Sequence):
                result += x.jobs
        return result

    def append(self, *sequences_or_jobs):
        if not sequences_or_jobs:
            return
        new_jobs = self.flatten(sequences_or_jobs)
        if self.jobs:
            new_jobs[0].requires(self.jobs[-1])
        self.jobs += new_jobs

    def requires(self, *requirements):
        if not self.jobs:
            # warning ?
            return
        self.jobs[0].requires(*requirements)
