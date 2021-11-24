"""
Variables
=========

FEZ allows you to give a name to any number or string in your feature file. These
names, called variables, begin with the dollar sign, and you to more easily understand a
rule by acting as a form of documentation. They also you allows to place all the "magic
numbers" together in your file so that they can be more easily tweaked later.

So instead of saying::

    DefineClass @tall_bases = @bases & yMax > 750;

    # ...

    Position @tall_bases (@top_marks <yPlacement=+150>);

you can say::

    Set $tall_base_height = 750;
    Set $tall_base_mark_adjustment = 150;

    DefineClass @tall_bases = @bases & yMax > $tall_base_height;

    # ...

    Position @tall_bases (@top_marks <yPlacement=$tall_base_mark_adjustment>);

You can also store a single glyph name in a variable and use it as a glyph
selector::

    Set $virama = "dvVirama";

    Substitute $virama @consonants -> @consonants.conjunct;

This is most helpful when combined with the ``For`` loop.
"""

from . import FEZVerb
import lark
from glyphtools import get_glyph_metrics, bin_glyphs_by_metric
from . import TESTVALUE_METRICS

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = """
    ?start: action
    action: "$" BARENAME "=" value
    value:  number_value | string_value
    number_value: integer_container
    string_value: ESCAPED_STRING

    %ignore WS
"""

VERBS = ["Set"]

class Set(FEZVerb):
    def __init__(self, parser):
        self.parser = parser

    def action(self, args):
        self.parser.variables[args[0].value] = args[1]
        return (args[0].value, args[1])

    def value(self, args):
        return args[0]

    def string_value(self, args):
        return args[0][1:-1]

    def number_value(self, args):
        return args[0]
