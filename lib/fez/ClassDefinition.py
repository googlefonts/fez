"""
Class Definitions
=================

To define a named glyph class in the FEZ language, use the ``DefineClass``
verb. This takes three arguments: the first is a class name, which must start
with the ``@`` character; the second is the symbol ``=``; the third is a glyph
selector as described above::

    # Create a class which consists of the members of @upper, with the .alt
    # suffix added to each glyph.
    DefineClass @upper_alts = @upper.alt;

    # Create a class of all glyphs matching the regex /^[a-z]$/ - i.e.
    # single character lowercase names "a", "b", "c" ... "z"
    DefineClass @lower = /^[a-z]$/;

    # Create a class of the named uppercase glyphs, plus the contents of
    # @lower.
    DefineClass @upper_and_lower = [A B C D E F G @lower];

In addition, glyph classes can be *combined* within the ``DefineClass``
statement using the intersection (``|``), union (``&``) and subtraction (``-``)
operators.

The ``|`` operator combines two classes together::

    # Equivalent to [@lower_marks @upper_marks]
    DefineClass @all_marks = @lower_marks | @upper_marks;

Whereas the ``&`` operator returns only glyphs which are common to both classes::

    DefineClass @uppercase_vowels = @uppercase & @vowels;

The ``-`` returns the glyphs in the first class which are not in the
second class::

    DefineClass @ABCD = A | B | C | D;

    # Everything in @ABCD apart from D (i.e. A, B, C)
    DefineClass @ABC = @ABCD - D;

Finally, within the context of a class definition, glyphs can also be selected
based on certain *predicates*, which test the glyphs for various properties::

    # All glyphs which start with the letters BE and whose advance width is
    # less than 200 units.
    DefineClass @short_behs = /^BE/ & width < 200;

There are a number of metric predicates:

  - ``width`` (advance width)
  - ``lsb`` (left side bearing)
  - ``rsb`` (right side bearing)
  - ``xMin`` (minimum X coordinate)
  - ``xMax`` (maximum X coordinate)
  - ``yMin`` (minimum Y coordinate)
  - ``yMax`` (maximum Y coordinate)
  - ``rise`` (difference in Y coordinate between cursive entry and exit)
  - ``fullwidth`` (``xMax``-``xMin``)

These predicates are followed by a comparison operator (``>=``, ``<=``, ``=``, ``<``, or
``>``) and then an integer. So::

    DefineClass @overhands = rsb < 0;

Alternatively, instead of an integer, you may supply a metric name and the name
of a single glyph in brackets. For example, the following definition selects
all members of the glyph class ``@alpha`` whose advance width is less than the
advance width of the ``space`` glyph::

    DefineClass @shorter_than_space = @alpha & width < width(space);

As well as testing for glyph metrics, the following other predicates are available:

- ``hasglyph(regex string)``

This is true for all glyphs where, if you take the glyph's name, and replace the
regular expression with the given string, you get the name of another glyph
in the font. For example::

  DefineClass @small_capable = hasglyph(/$/ .sc);

So we look at the glyph ``A``, for example, and test "If I replace the end of
this glyph's name with ``.sc`` - i.e. ``A.sc`` - do I get the name of a valid
glyph?" If so, then ``A`` is small-cap-able and goes into our class. Next we
look at ``B``, and so on.

  DefineClass @localizable_digits = @digits & hasglyph(/-arab/ "-farsi");

I have ``one-arab`` in my ``@digits`` class, but when I replace ``-arab`` with
``-farsi`` yielding ``one-farsi``, I don't see that in my font; so ``one-arab``
is not a localizable digit. But when I replace the ``-arab`` in ``four-arab`` to
get ``four-farsi``, I do see that in my font, so ``four-arab`` *is* a localizable
digit.

- ``hasanchor(anchorname)``

This predicate is true if the glyph has the given anchor in the font source.
(You will need to use either the ``LoadAnchors`` or ``Anchor`` verb before using
this predicate!) Example::

    DefineClass @topmarks = hasanchor(_top);

- ``category(categoryname)``

This predicate is true if the glyph has the given category in the font source.
The category is expected to be ``base``, ``mark`` or ``ligature``.

    DefineClass @stackable_marks = category(mark) & (hasanchor(_bottom) | hasanchor(_top));

This defines ``@stackable_marks`` to be all mark glyphs with either a ``_bottom``
or ``_top`` anchor.

Experience has shown that with smart enough class definitions, you can get away
with pretty dumb rules.

Binned Definitions
------------------

Sometimes it is useful to split up a large glyph class into a number of
smaller classes according to some metric, in order to treat them
differently. For example, when performing an i-matra substitution in
Devanagari, you would generally want to split your base glyphs by width,
and apply the appropriate matra for each set of glyphs. FEZ calls the
operation of organising glyphs into groups of similar metrics "binning".

The ``ClassDefinition`` plugin also provides the ``DefineClassBinned`` verb,
which generated a set of related glyph classes. The arguments of ``DefineClassBinned``
are identical to that of ``DefineClass``, except that after the class name
you must specify an open square bracket, one of the metrics listed above
to be used to bin the glyphs, a comma, the number of bins to create, and a
close bracket, like so::

    DefineClassBinned @bases[width,5] = @bases;

This will create five classes, called ``@bases_width1`` .. ``@bases_width5``,
grouped in increasing order of advance width.

Note that the size of the bins is not guaranteed to be equal, but bins are "smart":
glyphs are clustered according to the similarity of their metric. For example, if
the advance widths are 99, 100, 110, 120, 500, and 510 and two bins are created,
one bin will contain four glyphs (those with widths 99-120) and the other bin
will contain two glyphs (those with widths 500-510).

(This is just an example for the purpose of explaining binning. We'll show a
better way to handle the i-matra question later.)

Glyph Class Debugging
---------------------

The combination of the above rules allows for extreme flexibility in creating
glyph classes, to the extent that it may become difficult to understand the
final composition of glyph classes! To alleviate this, the verb ``ShowClass``
will take any glyph selector and display its contents on standard error.

"""

import lark
import re
from glyphtools import bin_glyphs_by_metric

import warnings

from . import FEZVerb
from .util import compare
from fez import GlyphSelector

GRAMMAR = """
has_glyph_predicate: "hasglyph(" REGEX MIDGLYPHNAME* ")"
has_anchor_predicate: "hasanchor(" BARENAME ")"
category_predicate: "category(" BARENAME ")"
predicate: has_glyph_predicate | has_anchor_predicate | category_predicate | metric_comparison
negated_predicate: "not" predicate

CONJUNCTOR: "&" | "|" | "-"
primary_action: glyphselector | conjunction | predicate | negated_predicate
primary: primary_action | ("(" primary_action ")")
conjunction: primary CONJUNCTOR primary

"""

DefineClass_GRAMMAR = """
?start: action
action: CLASSNAME "=" primary
"""

DefineClassBinned_GRAMMAR = """
?start: action
action: CLASSNAME "[" METRIC "," NUMBER "]" "=" primary
"""

PARSEOPTS = dict(use_helpers=True)
VERBS = ["DefineClass", "DefineClassBinned"]

class DefineClass(FEZVerb):
    def _add_glyphs_to_named_class(self, glyphs, classname):
        self.parser.fontfeatures.namedClasses[classname] = glyphs

    def has_glyph_predicate(self, args):
        (glyphre, withs) = args[0], "".join([a.value for a in args[1:]])
        value = {"replace": re.compile(glyphre.value[1:-1]), "with": withs}
        return {"predicate": "hasglyph", "value": value, "inverted": False}

    def has_anchor_predicate(self, args):
        (barename,) = args
        return {"predicate": "hasanchor", "value": barename.value, "inverted": False}

    def category_predicate(self, args):
        (barename,) = args
        return {"predicate": "category", "value": barename.value, "inverted": False}

    def metric_comparison(self, args):
        (metric, comparator, comp_value) = args
        metric = metric.value
        comparator = comparator.value
        comp_value = comp_value.resolve_as_integer()
        return lambda metrics, glyphname: compare(metrics[metric], comparator, comp_value)

    def predicate(self, args):
        (predicate,) = args

        if callable(predicate): # if it's a comparison
            return predicate
        else:
            return lambda _, glyphname: self.meets_predicate(glyphname, predicate, self.parser)

    def negated_predicate(self, args):
        (predicate,) = args
        return lambda metrics, glyphname: not predicate(metrics, glyphname)

    def primary_action(self, args):
        return args[0]

    def primary(self, args):
        (primary,) = args
        if isinstance(primary, GlyphSelector) or (isinstance(primary, dict) and "conjunction" in primary):
            glyphs = self.resolve_definition(self.parser, primary)
            return glyphs
        else: # we're holding a predicate, apply it to all glyphs
            glyphs = self._predicate_for_all_glyphs(primary)
            return glyphs

    def _predicate_for_all_glyphs(self, predicate):
        all_glyphs = list(self.parser.font.exportedGlyphs())
        return [g for g in all_glyphs if predicate(self._get_metrics(g), g)]

    def conjunction(self, args):
        l, conjunctor, r = args

        if isinstance(l, list) and callable(r):
            return [g for g in l if r(self._get_metrics(g), g)]

        return {"conjunction": {"&":"and","|":"or","-":"subtract"}[conjunctor], "left": l, "right": r}

    def action(self, args):
        parser = self.parser
        classname, glyphs = args
        classname = classname[1:] # -@

        self._add_glyphs_to_named_class(glyphs, classname)

        return args[0]

    @classmethod
    def resolve_definition(self, parser, primary):
        if isinstance(primary, dict) and "conjunction" in primary:
            left = set(primary["left"])
            right = set(primary["right"])
            if primary["conjunction"] == "or":
                return list(left | right)
            elif primary["conjunction"] == "and":
                return list(left & right)
            else: #subtract
                return set(left) - set(right)
        else:
            return primary.resolve(parser.fontfeatures, parser.font)

    @classmethod
    def meets_predicate(self, glyphname, predicate, parser):
        metric = predicate["predicate"]
        if metric == "hasanchor":
            anchor = predicate["value"]
            truth = glyphname in parser.fontfeatures.anchors and anchor in parser.fontfeatures.anchors[glyphname]
        elif metric == "category":
            cat = predicate["value"]
            truth = parser.font.glyphs[glyphname].category == cat
        elif metric == "hasglyph":
            truth = re.sub(predicate["value"]["replace"], predicate["value"]["with"], glyphname) in parser.font.exportedGlyphs()
        else:
            raise ValueError("Unknown metric {}".format(metric))
        return truth

class DefineClassBinned(DefineClass):
    def action(self, args):
        # glyphs is already resolved, because this class has functions of DefineClass, which resolves `primary`
        classname, (metric, bincount), glyphs = args[0], (args[1].value, args[2].value), args[3]
        binned = bin_glyphs_by_metric(self.parser.font, glyphs, metric, bincount=int(bincount))
        for i in range(1, int(bincount) + 1):
            self.parser.fontfeatures.namedClasses["%s_%s%i" % (classname, metric, i)] = tuple(binned[i - 1][0])

        return classname, (metric, bincount), glyphs

"""
class DefineClassBinned(DefineClass):
    @classmethod
    def action(self, parser, metric, bincount, classname, definition):
        glyphs = self.resolve_definition(parser, definition[0])
        predicates = definition[1]
        for p in predicates:
            glyphs = list(filter(lambda x: self.meets_predicate(x, p, parser), glyphs))

        binned = bin_glyphs_by_metric(parser.font, glyphs, metric, bincount=int(bincount))
        for i in range(1, int(bincount) + 1):
            parser.fontfeatures.namedClasses["%s_%s%i" % (classname["classname"], metric, i)] = tuple(binned[i - 1][0])
"""
