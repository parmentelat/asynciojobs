"""
A utility to print time and compute durations, mostly for debugging and tests.
"""

from datetime import datetime

class Watch:
    """
    This class essentially remembers a starting point, so that
    durations relative to that epoch can be printed for debug
    instead of a plain timestamp.

    Parameters:
      message(str): used in the printed message at creation time,
      show_elapsed(bool): tells if a message with the elapsed time needs
        to be printed at creation time (elapsed will be 0),
      show_wall_clock(bool): same for the wall clock.

    Examples:
      Here's a simple use case; note that ``print_wall_clock()``
      is a static because it is mostly useful, precisely, when you
      do not have a ``Watch`` object at hand::

        $ python3
        Python 3.6.4 (default, Mar  9 2018, 23:15:12)
        <snip>
        >>> from asynciojobs import Watch
        >>> import time
        >>> watch = Watch("hello there"); time.sleep(1); watch.print_elapsed()
        000.000  hello there
        001.000  >>>
        >>>
        >>> Watch.print_wall_clock()
        20:48:27.782 >>>
    """

    # default is to print the elapsed format only
    def __init__(self, message=None, *,
                 show_elapsed=True, show_wall_clock=False):
        self.start = 0
        self.reset()
        message = message if message is not None else ""
        if show_elapsed:
            self.print_elapsed(" {}\n".format(message))
        if show_wall_clock:
            self.print_wall_clock(" {}\n".format(message))

    def reset(self):
        """
        Use current wall clock as starting point.
        """
        self.start = datetime.now()

    def seconds(self):
        """
        Returns:
          float: time elapsed since start, in seconds.
        """
        return (datetime.now() - self.start).total_seconds()

    def elapsed(self):
        """
        Returns:
          str: number of seconds elapsed since start, formatted
          on 7 characters: 3 for seconds, a dot, 3 for milliseconds
        """
        return "{:07.3f}".format(self.seconds())

    def print_elapsed(self, suffix=" "):
        """
        Print the elapsed time since start in format
        SSS.MMM + a suffix.

        Parameters:
          suffix(str): is appended to the output; to be explicit,
            by default no newline is added.
        """
        print("{} {}".format(self.elapsed(), suffix),
              end="")

    @staticmethod
    def print_wall_clock(suffix=" "):
        """
        Print current time in HH:MM:SS.MMM + a suffix.

        Parameters:
          suffix(str): is appended to the output; to be explicit,
            by default no newline is added.
        """
        now = datetime.now()
        millisecond = now.microsecond // 1000
        timestamp = datetime.now().strftime("%H:%M:%S")
        print("{}.{}{}".format(timestamp, millisecond, suffix),
              end="")
