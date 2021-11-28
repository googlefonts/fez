"""
Loops
=====

FEZ has a ``For`` loop to allow you to iterate over glyph selectors. The
loop sets a variable to each of the selected glyphs in turn.

Examples::

    For $g in @glyphs {
        If width[$g] > 500 {
            Substitute $g -> $g.narrow;
        };
    };

"""

import fontFeatures
from .util import compare
from . import FEZVerb

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = ""

For_GRAMMAR = """
?start: action
action: "$" BARENAME "in" glyphselector "{" statement+ "}"
"""

For_beforebrace_GRAMMAR = """
?start: beforebrace
beforebrace: "$" BARENAME "in" glyphselector
"""

VERBS = ["For"]

class For(FEZVerb):
    def action(self, args):
        (before, statements, _) = args
        before = self.parser.expand_statements(before)
        varname, glyphselector = before
        glyphs = glyphselector.resolve(self.parser.fontfeatures, self.parser.font)

        rv = []
        for g in glyphs:
            self.parser.variables[varname] = g
            rv.extend(self.parser.expand_statements(statements))
        return rv
