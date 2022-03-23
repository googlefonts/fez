"""
Kerning
=======

The ``Kerning`` plugin provides the ``Kerning`` verb. This reads the kerning
information from the source file and outputs kerning rules.

    Feature kern {
        Kerning;
    }

The ``Kerning`` verb takes one optional parameters: a glyph selector to
match particular glyphs. If any glyph in either of the classes in either side
of the kern pair matches, then the rule is emitted; if not, it is not. The
idea of this parameter is to allow you to split your kerning rules by script.

    Feature kern {
        Kerning /(?!.*-ar$)/; # Non-Arabic kerns go into kern
    };

    Feature dist {
        Kerning /-ar$/; # Arabic kerns go into dist
    };

"""
from fontTools.feaLib.variableScalar import VariableScalar


from . import FEZVerb
import fontFeatures
import warnings

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = """
?start: action
action: glyphselector?
"""

VERBS = ["Kerning"]

class Kerning(FEZVerb):
    def action(self, args):
        glyphselector = args and args[0].resolve(self.parser.fontfeatures, self.parser.font)
        rules = []
        kerning = self.parser.font.default_master.kerning
        all_keys = [set(m.kerning.keys()) for m in self.parser.font.masters]
        for (l, r) in sorted(list(set().union(*all_keys))):
            kern = VariableScalar()
            kern.axes = self.parser.font.axes
            for m in self.parser.font.masters:
                thiskern = m.kerning.get((l, r), 0)
                kern.add_value(m.location, thiskern)

            if l.startswith("@"):
                if not l[1:] in self.parser.font.features.namedClasses:
                    warnings.warn(f"Left kerning group '{l}' not found")
                    continue
                l = self.parser.font.features.namedClasses[l[1:]]
            else:
                l = [l]
            if r.startswith("@"):
                if not r[1:] in self.parser.font.features.namedClasses:
                    warnings.warn(f"Right kerning group '{r}' not found")
                    continue
                r = self.parser.font.features.namedClasses[r[1:]]
            else:
                r = [r]

            l = [ g for g in l if g in self.parser.font.exportedGlyphs()]
            r = [ g for g in r if g in self.parser.font.exportedGlyphs()]
            for l1 in l:
                for r1 in r:
                    rules.append(fontFeatures.Positioning(
                        [[l1],[r1]],
                        [ fontFeatures.ValueRecord(xAdvance=kern), fontFeatures.ValueRecord() ],
                    flags=0x8
                    ))
        return rules


