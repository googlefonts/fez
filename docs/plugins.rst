
Writing your own plugins
------------------------

The power of FEZ comes from its extensibility, and that means the ability to
write your own plugins. A guiding principle of writing feature code in the
FEZ language is that instead of *telling* the font specifically what to do
("move these two glyphs fifty units apart"), as much as possible you *query*
the font for information and then automatically *work out* the right thing to
do. This is done through writing "rules which write rules" in Python modules.

This takes a bit of work, but the end result should be that you have sets of
rules that you can carry from font to font without needing to rewrite them.

Let's take a look at a couple of sample plugins to see how they're constructed.

Grammars
^^^^^^^^

A fontFeatures plugin comes in two parts: the *grammar* and the *code*. Grammars
explain what kinds of arguments, and how many arguments, the verbs in the plugin
expect. Grammars are written in the notation used by
`Lark <https://lark-parser.readthedocs.io/en/latest/>`_ so you should start by
reading its documentation (or, if you're like me, by picking it up by looking
at existing examples).

Our first plugin is going to be called ``CopyAnchors``, and it will copy all
anchors from glyphs in one glyph class to glyphs in another glyph class. What
do we want the call to this verb to look like? Probably something like
``CopyAnchors @gc1 @gc2;``. So the arguments to ``CopyAnchors`` will be two
glyph selectors, separated by whitespace. Here's how we will start our plugin::

    PARSEOPTS = dict(use_helpers=True)

    GRAMMAR = """
    ?start: action
    action: glyphselector glyphselector
    """
    VERBS = ["CopyAnchors"]

A ``GRAMMAR`` contains a complete Lark grammar. ``PARSEOPTS`` must be defined;
its function is to describe how the grammar is to be parsed. If ``use_helpers``
is ``True``, then the grammar defined in ``__init__.py`` as ``HELPERS`` will be
prepended to your grammar. This grammar defines many useful elements, such as
``glyphselector``, which we reuse.

By convention, your grammar should always start with the line ``?start:
action``, and then work backwards defining action. In Lark, tokens
(*terminals*) are in all capital letters, while *rules* are in lowercase. One
of the rules imported by ``use_helpers`` is the handy ``%ignore WS``, which
inserts an implied optional whitespace between the two glyph selectors.

Now we have the grammar, and also defined the ``VERBS`` that this module
provides (don't forget that bit!), we can turn to implementation.

Verb implementations
^^^^^^^^^^^^^^^^^^^^

When a verb is "called" by a FEZ file, first the arguments to the verb are
parsed according to the grammar you've provided. Then, the abstract syntax tree
(AST) that is generated is transformed by our subclass of ``lark.Transformer``,
``FEZVerb``.

``FEZVerb`` gives us access to the font object, the ``fontFeatures`` object,
and other stuff we might need, through ``self.parser``. It is also possible to
only subclass ``lark.Transformer`` for low level access to the AST, but you
should only very seldom want to do this.

Let's set up our class, and then we'll talk about the content of those
arguments::

    class CopyAnchors(FEZVerb):
        def action(self, args):
            (fromglyphs, toglyphs) = args

Because we've subclassed ``FEZVerb``, we receive the benefits of this class;
both of our ``glyphselectors`` are transformed for us into
``fez.GlyphSelector`` objects which can be resolved. Note that
we, due to our grammar, know that ``args`` will contain exactly two
``glyphselector``'s. A grammar, however, could instead say ``glyphselector*``,
receiving any number, and making ``args`` return a variable number of them.

This is a common pattern you will see in a lot of FEZ plugins::

          fromglyphs = fromglyphs.resolve(self.parser.fontfeatures, self.parser.font)
          toglyphs = toglyphs.resolve(self.parser.fontfeatures, self.parser.font)

(It needs the ``fontfeatures`` object so that it can resolve named class
references; it needs the ``font`` object for the list of glyphs in the font.)
If we were going to *create* the ``toglyphs`` we would tell ``resolve`` that
the glyphs don't need to exist yet::

          toglyphs = toglyphs.resolve(parser.fontfeatures, parser.font, mustExist=False)

Now we have a list of from-glyphs, a list of to-glyphs, a ``fontFeatures``
object, and the rest is easy: ``fontFeatures`` stores a dictionary of anchors
for each glyph, so we just copy them across::

          for (f, t) in zip(fromglyphs,toglyphs):
            parser.fontfeatures.anchors[t] = parser.fontfeatures.anchors[f]

Normally a FEZ plugin would return a list of ``Routine`` objects, but we're
not creating any rules, so we just return an empty list::

          return []

And we're done. Now we'll look at a more involved plugin - one which inspects
the glyphs themselves, and emits some rules in response.

.. _imatra:

The IMatra Plugin
^^^^^^^^^^^^^^^^^

The IMatra plugin, described above, comes with fontFeatures. It matches the
"i" vowel sign in Devanagari to bases of the appropriate width. Let's see how
it works. First, we define the grammar. This is similar to the one above - just
three glyph selectors - but we use some constant symbols as a bit of "syntactic
sugar". Note that we only assign the glyph selectors to variables (and put them
into the return tuple), and not the syntactic sugar::

    PARSEOPTS = dict(use_helpers=True)

    GRAMMAR = """
    ?start: action
    //      bases             matra              matras
    action: glyphselector ":" glyphselector "->" glyphselector
    """

    VERBS = ["IMatra"]

We're going to need to know how wide all of our matras and bases are, and the
fontFeatures way to do this is to use the `get_glyph_metrics <https://glyphtools.readthedocs.io/en/latest/#glyphtools.get_glyph_metrics>`_ function from the `glyphtools <https://glyphtools.readthedocs.io/>`_ library::

    import fontFeatures
    from glyphtools import get_glyph_metrics

Now we're ready to write our action method, which will start with the usual
resolving of glyph selectors into glyph name lists::

    class IMatra:
        def action(self, args):
            (bases, matra, matras) = args
            bases = bases.resolve(self.parser.fontfeatures, self.parser.font)
            matra = matra.resolve(self.parser.fontfeatures, self.parser.font)
            matras = matras.resolve(self.parser.fontfeatures, self.parser.font)

Let's think what we need to do now. We have a list of matras, with different
"overhangs" (negative RSBs). For each matra, we want a list of bases which this
matra best fits, and then we emit a set of substitution rules. First, we'll
create a dictionary to hold our "best fits" bases for each matra, and
arrange the list of matras into a list of (glyphname, overhang) tuples::

        matras2bases = {}
        matrasAndOverhangs = [
            (m, -get_glyph_metrics(parser.font, m)["rsb"]) for m in matras
        ]

Now we loop over the bases, and find the matra which has the smallest difference
between the base width and the matra overhang::

        for b in bases:
            w = get_glyph_metrics(parser.font, b)["width"]
            (bestMatra, _) = min(matrasAndOverhangs, key=lambda s: abs(s[1] - w))

And store this in the dictionary::

            if not bestMatra in matras2bases:
                matras2bases[bestMatra] = []
            matras2bases[bestMatra].append(b)

When the loop is finished and we have processed all the bases, we can now
turn the dictionary into a list of substitution rules. We want to emit rules
with this kind of form::

    Substitute { iMatra-deva } @bases_3 -> iMatra-deva.3;

i.e. the bases are the post-context for the matra substitution. This is how
we do it::

        rv = []
        for bestMatra, basesForThisMatra in matras2bases.items():
            rv.append(
                fontFeatures.Substitution(
                    [matra],
                    postcontext=[basesForThisMatra],
                    replacement=[[bestMatra]]
                )
            )

You may have noticed that ``bestMatra`` goes into a list of lists, but ``matra``
does not. It's good to think through why this is, because it will help you
understand fontFeatures rules. Resolving a glyph selector always returns a
list. So resolving the glyphselector ``matra`` returned a list of glyph names,
although probably that list had only one element. A substitution or positioning
rule defines its input as a list of glyph stream positions, each of which is a
list of glyph names that can match at this position. In essence, every element
of the glyph stream position list must be expressed as a "glyph class", even if
it is a one-element class. So the input will be::

    [
      # Glyph position 1:
      matra # We got a one-element list from `.resolve` e.g. ["iMatra-deva"]
    ]

For the postcontext, we want to match a glyph class. ``basesForThisMatra`` is
a list, so this is also fine::

    [
      # Glyph position 1:
      basesForThisMatra # e.g. [ "ga-deva", "gha-deva", ... ]
    ]

We want the replacement parameter to look the same: for each position in the
replacement glyph stream, a list of glyphs to be substituted. (This is because
``Substitution`` *also* supports "alternate" substitutions, in which glyph
position 1 will substitute multiple glyphs, and also because regularity is
good and leads to fewer surprises.) However, ``bestMatra`` is not a list,
but a single glyph; this is why we have to make it into one::

    [
      # Glyph position 1:
      [ "iMatra-deva.3" ]
    ]

Finally, all that remains to do is wrap up our list of substitution rules into
a routine, and return it::

        return [fontFeatures.Routine(rules=rv)]

In more complex scenarios, you may find yourself enumerating all the
combinations of glyphs within a sequence (the ``itertools.product`` function
is useful for this); checking whether a given set of glyphs causes a collision
when positioned (the :py:mod:`fontFeatures.jankyPOS` positioner and the `collidoscope <https://pypi.org/project/collidoscope/>`_ library may help you);
inspecting the paths and doing some sums based on them (:py:mod:`fontFeatures.pathUtils` and the `beziers <https://pypi.org/project/beziers/>`_ library are good for this).

To gain more understanding of what this might look like, try working through
the code of the :py:mod:`fez.IfCollides` and
:py:mod:`fez.BariYe` plugins.

Defining multiple verbs
^^^^^^^^^^^^^^^^^^^^^^^

Up until now, we've defined extensions which have only one verb. An example of
this can be seen in the default ``Substitute.py`` extension. ``GRAMMAR``, in
this case, applies to the entire extension. Then, you can define::

    Substitute_GRAMMAR = """
    ?start: action
    action: normal_action | contextual_action
    """

    ReverseSubstitute_GRAMMAR = """
    ?start: action
    action: normal_action
    """

    VERBS = ["Substitute", "ReverseSubstitute"]

Notes on curly brackets
^^^^^^^^^^^^^^^^^^^^^^^

In order to prevent grammars from ever being ambiguous, ``{`` and ``}`` are not
allowed in your grammar with any meaning other than grouping other verbs. So,
extensions like ``Feature`` and ``Routine`` may use them, but they must not be
used unless it's to group other verbs.

If you do need to group, note the different way that such grammars are parsed.
If you want to define arguments before and after the braces, you must define
``beforebrace`` and ``afterbrace`` grammars; see ``Feature.py`` and
``Routine.py`` in the ``fez`` directory for examples.

Generally, it's recommended to avoid curly brackets, as they should normally
not be useful for user extensions now that ``Feature`` and ``Routine`` already
exist.
