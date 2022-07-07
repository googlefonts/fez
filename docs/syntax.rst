
Writing Font Feature Code in the FEZ Language
=============================================

Now we've seen what the FEZ language can do for us, let's look in depth at
how to write our rules in it.

Verbs and arguments
-------------------

FEZ statements consist of a *verb* followed by *arguments* and terminated
with a semicolon (``;``). Each verb defines their own set of arguments,
and this means that there is considerable flexibility in how the arguments
appear. For example, the ``Anchors`` statement takes a glyph name, followed
by an open curly brace (``{``), a series of anchor name / anchor position
pairs, and a close curly brace (``}``) - but no other verb has this pattern.
(Plugin writers are encouraged to keep the argument syntax simple and
intuitive.)

In general, amount and type of whitespace is not significant so long
as arguments are separated unambiguously, and comments may be inserted
between sentences in the usual form (``# ignored to end of line``).

Here is a simple FEZ file::

  DefineClass @comma = [uni060C uni061B];
  Feature ss08 {
    Substitute @comma -> @comma.alt;
  };

``DefineClass``, ``Feature`` and ``Substitute`` are all verbs, and all have
their own different argument patterns: ``DefineClass`` takes a class name, an
equals and then a *glyph selector* (which we'll meet soon); ``Feature`` takes
a feature name, a curly brace, some statements and a closing curly brace;
```Substitute`` takes a number of glyph selectors, an arrow, and a number of
glyph selectors, and so on.

The meaning of the above code should be fairly obvious to users of Adobe feature
syntax, but some features (particularly the use of "dot suffixing" to create
a synthetic class) will be unfamiliar. Here's an AFDKO translation::

  @comma = [uni060C uni061B];

  feature ss08 {
    sub @comma by [uni060C.alt uni061B.alt];
  } ss08;


We'll begin by discussing how to address a set of glyphs within the
FEZ language before moving on to the verbs that are available.

Glyph Selectors
---------------

A *glyph selector* is a way of specifying a set of glyphs in the FEZ language.
There are various forms of glyph selector:

- A single glyph name: ``a``
- An class name: ``@lc``
- An inline class: ``[a e i o u]`` (Inline classes may also contain class names, but may *not* contain ranges.)
- A regular expression: ``/\.sc/``. All glyph names in the font which match the expression will be selected. (This is another reason why FEZ needs the font beforehand.)
- A Unicode codepoint: ``U+1234`` (This will be mapped to a glyph in the font. If no glyph exists, an error is raised.)
- A range of Unicode points: ``U+30=>U+39``, described below.

The final form of glyph selector, the Unicode range selector (``=>``) matches
all glyphs between two Unicode codepoints. For example, digits in a font usually
have the standard glyph names ``zero``, ``one``, ``two``, ``three`` and so on.
It's a common task to refer to all the digits, but at the same time, it's a pain
to have to list them out by hand, and there isn't a way to do it with a regular
expression glyph selector. But they do have contiguous Unicode codepoints -
``zero`` is codepoint U+0030 and ``nine`` has codepoint U+0039 - so it's easy
enough select them with a Unicode range selector:

    DefineClass @digits = U+0030=>U+0039;

Using Unicode codepoints instead of glyph names helps to make your rules "portable"
between different fonts targeting the same scripts.

Any of these glyph selector forms may be followed by zero or more *suffixing operations*
or *desuffixing operations*. A suffixing operation begins with a period,
and adds the period plus its argument to the end of any glyph names matched
by the selector. In the example above, ``@comma.alt`` refers to the glyphs
in ``@comma`` with the suffix ``.alt`` added; the glyphs in ``@comma`` are
``uni060C`` and ``uni061B``, so the glyphs in ``@comma.alt`` are ``uni060C.alt``
and ``uni061B.alt``.

A *desuffixing* operation, on the other hand, begins with a tilde, and *removes*
the dot-suffix from the name of all glyphs matched by the selector. So if you
happened to have a glyph class ``@comma_alternates`` consisting of ``uni060C.alt uni061B.alt``,
then ``@comma_alternates~alt`` would take the ``.alt`` off each glyph name,
and refer to glyphs ``uni060C uni06B1``.

Desuffixing operations combine very nicely with regular expression glyph selectors.
Above, we saw the example ``/\.sc$/`` which finds all glyphs which end with the
suffix ``.sc``. Let's say this resolves to ``[a.sc b.sc c.sc]``. If you then
desuffix that glyph selector - ``/\.sc$/~sc`` - you get the bare, non-small-caps
forms of those glyphs: ``[a b c]``. In other words, the glyphs in the font which
hayve a corresponding small-caps form. Now you don't have to keep track of which
glyphs you have small-caps forms of; you can select the list of small
caps glyphs, and turn that back into the unsuffixed form::

    Substitute /\.sc$/~sc -> /\.sc$/;
    # Equivalent to "Substitute [a b c ...] -> [a.sc b.sc c.sc ...];"

Standard verbs
--------------

In FEZ, *all* verbs are provided by Python plugins. There are no "built-in"
verbs. However, the following plugins are automatically loaded and their
verbs are always available.

.. automodule:: fez.ClassDefinition
.. automodule:: fez.Variables
.. automodule:: fez.Feature
.. automodule:: fez.LoadPlugin
.. automodule:: fez.Routine
.. automodule:: fez.Substitute
.. automodule:: fez.Position
.. automodule:: fez.Chain
.. automodule:: fez.Anchors
.. automodule:: fez.Conditional
.. automodule:: fez.Include
