"""
DotStyle is a helper class that takes care of details
when converting data to the DOT format.

This is not meant to be exported outside of this package.
"""

# pylint: disable=c0111


class DotStyle(dict):

    """
    DotStyle is a collection of formatting helpers for creating a DOT output
    """

    def __repr__(self):
        """
        repr() for a DotStyle instance is designed to be shown in the
        [] section for e.g. a node.
        """

        return ",".join(
            "{}={}".format(key, DotStyle.value(value_s))
            for key, value_s in self.items())

# we found a trick that removed the need for this
#    def cluster_repr(self):
#        """
#        same, but for being mentioned in a subgraph section, like e.g:
#
#            style = "foo,bar";
#            label = "some label";
#        """
#        return "".join(
#            "{}={};\n".format(key, DotStyle.value(value_s))
#            for key, value_s in self.items())

    @staticmethod
    def protect(data):
        string = str(data)
        # escape any double quote
        result = string.replace('"', r'\"')
        # and put double quotes around all this
        return '"{}"'.format(result)

    # output a list (typically for keys like 'shape'
    # or atomic (typically for 'label') value
    @staticmethod
    def value(value_s):
        if isinstance(value_s, list):
            return DotStyle.protect(format(",".join(v for v in value_s)))
        return DotStyle.protect(value_s)
