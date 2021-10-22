
Writing Font Feature Code in the FEZ Language
=============================================

Overview of the FEZ language
----------------------------

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

The meaning should be fairly obvious to users of Adobe feature syntax,
but some features (particularly the use of "dot suffixing" to create
a synthetic class) will be unfamiliar. We'll start by discussing how
to address a set of glyphs within the FEZ language before moving on to
the verbs that are available.

Glyph Selectors
---------------

A *glyph selector* is a way of specifying a set of glyphs in the FEZ language. There are various forms of glyph selector:

- A single glyph name: ``a``
- An class name: ``@lc``
- An inline class: ``[a e i o u]`` (Inline classes may also contain class names, but may *not* contain ranges.)
- A regular expression: ``/\.sc/``. All glyph names in the font which match the expression will be selected. (This is another reason why FEZ needs the font beforehand.)
- A Unicode codepoint: ``U+1234`` (This will be mapped to a glyph in the font. If no glyph exists, an error is raised.)

Any of these forms may be followed by zero or more *suffixing operations*
or *desuffixing operations*. A suffixing operation begins with a period,
and adds the period plus its argument to the end of any glyph names matched
by the selector. In the example above ``@comma.alt``, the glyphs selected
would be ``uni060C.alt`` and ``uni060C.alt``.

A desuffixing operation, on the other hand, begins with a tilde, and *removes* the dot-suffix from the name of all glyphs matched by the selector.
For example, the glyph selector ``/\.sc$/~sc`` turns out to be a useful
way of identifying all glyphs which have a ``.sc`` suffix and turning
them back into their bare forms, suitable for the left-hand side of a
substitution operation. Now you don't have to keep track of which
glyphs you have small-caps forms of; you can select the list of small
caps glyphs, and turn that back into the unsuffixed form::

    Substitute /\.sc$/~sc -> /\.sc$/;
    # Equivalent to "Substitute [a b c ...] -> [a.sc b.sc c.sc ...];"

Standard plugins
----------------

In FEZ, *all* verbs are provided by Python plugins. There are no "built-in"
verbs. However, the following plugins are automatically loaded and their
verbs are always available.

.. automodule:: fez.ClassDefinition
.. automodule:: fez.Conditional
.. automodule:: fez.Feature
.. automodule:: fez.LoadPlugin
.. automodule:: fez.Routine
.. automodule:: fez.Substitute
.. automodule:: fez.Position
.. automodule:: fez.Chain

Optional plugins
----------------

.. automodule:: fez.Anchors
.. automodule:: fez.Arabic
.. automodule:: fez.BariYe
.. automodule:: fez.FontEngineering
.. automodule:: fez.IfCollides
.. automodule:: fez.IMatra
.. automodule:: fez.KernToDistance
.. automodule:: fez.LigatureFinder
.. automodule:: fez.MedialRa
.. automodule:: fez.Swap
