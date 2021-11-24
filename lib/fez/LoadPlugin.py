"""
LoadPlugin
==========

The LoadPlugin verb is the means by which you can load additional plugins, both
those you write yourself, and the :ref:`optional plugins` which we will meet later.

For one of the plugins which comes with FEZ, you can just name it::

    LoadPlugin LigatureFinder;
    # Now the LigatureFinder verb is available!

For a plugin you write yourself, you will need to place it into a Python package,
(this basically means "creating a subdirectory and adding an empty file in it
called ``__init__.py`` as well as your plugin file") and give the full module name.
For example, if you're developing fonts for Telugu, you might create a package
called "TeluguTools" which has all your plugin files in. Suppose one of those
plugins is ``Conjuncts``. You would place a file ``TeluguTools/Conjuncts.py``
somewhere in your Python load path, and then say::

    LoadPlugin TeluguTools.Conjuncts;

A plugin may make available one or more verbs, so you need to read the plugin's
documentation to know which verbs are available.
"""

from fez import FEZVerb

PARSEOPTS = dict(use_helpers=True)

# We need a Python package name here, but a bare glyph name looks
# just like one.
GRAMMAR = """
    ?start: action
    action: BARENAME

    %import common(WS, LETTER, DIGIT)
    %ignore WS
"""

VERBS = ["LoadPlugin"]

class LoadPlugin(FEZVerb):
    immediate = True

    def __init__(self, parser):
        self.parser = parser

    def action(self, args):
        self.parser.load_plugin(args[0].value)
        return args[0].value
