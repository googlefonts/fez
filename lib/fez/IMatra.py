"""
Matra selection
===============

In Devanagari fonts, it is common to have a basic glyph to represent the "i"
matra, and then a set of variant glyphs of differing widths. The "arm" of the
"i" matra should reach the stem of the following base consonant, which leads to an
interesting font engineering question: how do we produce a set of substitution
rules which replaces the basic glyph for each width-specific variant most
appropriate to the widths of the each consonant?

Obviously you don't want to work that out manually, because the next time you
engineer a Devanagari font you have to work it out again, and no programmer is
going to do the same set of operations more than once without automating it.

The ``IMatra`` plugin provides a verb which matches the consonants to the
matra variant with the appropriate sized arm and emits substitution rules. It
takes a glyph selector to represent the consonants, the basic i-matra glyph,
and a glyph selector for all the i-matra variants::

    LoadPlugin IMatra;
    DefineClass @consonants = /^dv.*A$/;
    IMatra @consonants : dvmI -> /^dvmI/;

For more on how this plugin actually operates, see :ref:`imatra`.
"""

import fontFeatures
import warnings

from fez import FEZVerb

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = """
?start: action
action: glyphselector ":" glyphselector "->" glyphselector
"""

VERBS = ["IMatra"]


class IMatra(FEZVerb):
    def action(self, args):
        parser = self.parser
        (bases, matra, matras) = args
        bases = bases.resolve(parser.fontfeatures, parser.font)
        matra = matra.resolve(parser.fontfeatures, parser.font)
        matras = matras.resolve(parser.fontfeatures, parser.font)

        # Organise matras into overhang widths
        matras2bases = {}
        matrasAndOverhangs = [
            (m, -parser.font.default_master.get_glyph_layer(m).rsb) for m in matras
        ]
        for b in bases:
            w = self.find_stem(parser.font, b)
            warnings.warn("Stem location for %s: %s" % (b,w))
            (bestMatra, _) = min(matrasAndOverhangs, key=lambda s: abs(s[1] - w))
            if not bestMatra in matras2bases:
                matras2bases[bestMatra] = []
            matras2bases[bestMatra].append(b)
        rv = []
        for bestMatra, basesForThisMatra in matras2bases.items():
            rv.append(
                fontFeatures.Substitution(
                    [matra], postcontext=[basesForThisMatra], replacement=[[bestMatra]]
                )
            )
        return [fontFeatures.Routine(rules=rv)]

    def find_stem(self, font, base):
        glyph = font.default_master.get_glyph_layer(base)
        # Try stem anchors first
        possible = [a.x for a in glyph.anchors if a.name == "abvm.e" or a.name == "abvm" ]
        if possible:
            return possible[0]
        # Try a right margin
        if 0x0947 in font.unicode_map:
            dvme_anchors = font.default_master.get_glyph_layer(font.unicode_map(0x0947)).anchors
            margin = [a.x for a in dvme_anchors if a.name == "_abvm.e" or a.name == "_abvm" ]
            if margin:
                return glyph.width + margin[0]
        return glyph.width / 2
