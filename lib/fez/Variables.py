"""
Variables
=========

FEZ allows you to give a name to any number in your feature file. These names,
called variables, begin with the dollar sign, and you to more easily understand a
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

"""

import lark

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = """
    ?start: action
    action: BARENAME "=" SIGNED_NUMBER

    %ignore WS
"""

VERBS = ["Set"]

class Set(lark.Transformer):
    def __init__(self, parser):
        self.parser = parser

    def action(self, args):
        self.parser.variables[args[0].value] = args[1].value
        return (args[0].value, args[1].value)
