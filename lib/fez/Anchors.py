"""
Anchor Management
=================

The ``Anchors`` plugin provides the ``Anchors``, ``LoadAnchors`` and ``Attach`` verbs.

``Anchors`` takes a glyph name followed by anchor names and
positions, like so::

      Anchors A top <679 1600> bottom <691 0>;

Note that there are no semicolons between anchors. The *same thing* happens
for mark glyphs::

      Anchors acutecomb _top <-570 1290>;

If you don't want to define these anchors manually but instead are dealing with
a source font file which contains anchor declarations, you can load the anchors
automatically from the font by using the ``LoadAnchors;`` verb.

Once all your anchors are defined, the ``Attach`` verb can be used to attach
marks to bases::

      Feature mark { Attach &top &_top bases; };

The ``Attach`` verb takes three parameters: a base anchor name, a mark anchor
name, and a class filter, which is either ``marks``, ``bases`` or ``cursive``.
The verb acts by collecting all the glyphs which have anchors defined, and
filtering them according to their class definition in the ``GDEF`` table.
In this case, we have asked for ``bases``, so glyph ``A`` will be selected.
Then it looks for anchor definitions containing the mark anchor name
(here ``_top``), which will select ``acutecomb``, and writes an attachment
rule to tie them together. As shown in the example, this
is the most efficient way of expressing a mark-to-base feature.

Writing a mark-to-mark feature is similar; you just need to define a corresponding
anchor on the mark, and use the ``marks`` class filter instead of the ``bases``
filter::

      Anchors acutecomb _top <-570 1290> top <-570 1650>;
      Feature mkmk { Attach &top &_top marks; };

Writing a cursive attachment figure can be done by defining ``entry`` and ``exit``
anchors, and using an ``Attach`` statement like the following::

        Feature curs {
            Routine { Attach &entry &exit cursive; } IgnoreMarks;
        };

"""

from . import FEZVerb
import fontFeatures

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = ""

Anchors_GRAMMAR = """
?start: action
action: glyphselector anchors
anchors: anchor+
anchor: BARENAME "<" integer_container integer_container ">"
"""

Attach_GRAMMAR = """
?start: action
action: "&" BARENAME "&" BARENAME ATTACHTYPE
ATTACHTYPE: "marks" | "bases" | "cursive"
"""

LoadAnchors_GRAMMAR = """
?start: action
action:
"""

PropagateAnchors_GRAMMAR = """
?start: action
action:
"""

VERBS = ["Anchors", "Attach", "LoadAnchors", "PropagateAnchors"]

class Anchors(FEZVerb):
    def anchors(self, args):
        return args

    def anchor(self, args):
        (name, x, y) = args
        name = name.value
        return (name, x, y)

    def action(self, args):
        (glyphselector, anchors) = args

        glyphs = glyphselector.resolve(self.parser.fontfeatures, self.parser.font)
        for g in glyphs:
            if not g in self.parser.fontfeatures.anchors:
                self.parser.fontfeatures.anchors[g] = {}
            for a in anchors:
                (name, x, y) = a
                self.parser.fontfeatures.anchors[g][name] = (x, y)

        return []

class LoadAnchors(FEZVerb):
    def action(self, _):
        for glyphname in self.parser.font.exportedGlyphs():
            g = self.parser.font.default_master.get_glyph_layer(glyphname)
            for a in g.anchors:
                if glyphname not in self.parser.fontfeatures.anchors:
                    self.parser.fontfeatures.anchors[glyphname] = {}
                self.parser.fontfeatures.anchors[glyphname][a.name] = (int(a.x), int(a.y))

class Attach(FEZVerb):
    def action(self, args):
        (aFrom, aTo, attachtype) = args    

        bases = {}
        marks = {}
        catcache = {}
        def _category(k):
            if k not in catcache:
                catcache[k] = self.parser.fontfeatures.glyphclasses.get(k, self.parser.font.glyphs[k].category)
            return catcache[k]

        for k, v in self.parser.fontfeatures.anchors.items():
            if aFrom in v:
                bases[k] = v[aFrom]
            if aTo in v:
                marks[k] = v[aTo]
            if attachtype == "marks":
                bases = {
                    k: v
                    for k, v in bases.items()
                    if _category(k) == "mark"
                }
            else:
                bases = {
                    k: v
                    for k, v in bases.items()
                    if _category(k) == "base"
                }
            if attachtype != "cursive":
                marks = {
                    k: v
                    for k, v in marks.items()
                    if _category(k) == "mark"
                }
        return [
            fontFeatures.Routine(
                rules=[
                    fontFeatures.Attachment(aFrom, aTo, bases, marks, font=self.parser.font)
                ]
            )
        ]


class PropagateAnchors(FEZVerb):
    def action(self, _):
        for glyphname in self.parser.font.exportedGlyphs():
            # This does a simple, first-come-first-served base component propagation
            g = self.parser.font.default_master.get_glyph_layer(glyphname)
            if not g.components:
                continue
            if glyphname not in self.parser.fontfeatures.anchors:
                self.parser.fontfeatures.anchors[glyphname] = {}
            anchor_dict = self.parser.fontfeatures.anchors[glyphname]

            for comp in g.components:
                comp_glyph = self.parser.font.default_master.get_glyph_layer(comp.ref)
                for a in comp_glyph.anchors:
                    if a.name not in anchor_dict:
                        transformed = comp.transform.transformPoint((a.x, a.y))
                        anchor_dict[a.name] = (int(transformed[0]), int(transformed[1]))

