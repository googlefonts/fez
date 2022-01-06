"""
Routine
=======

To group a set of rules into a routine, use the ``Routine`` verb. This takes
a name and a block containing rules::

    Routine {
        ...
    };

Note that in FEZ syntax you must not repeat the routine name at the end of
the block, as is required in AFDKO syntax. Instead, any routine flags are
added to the end of the block, and may be any combination of ``RightToLeft``;
``IgnoreBases`` (AFDKO users, note the changed name); ``IgnoreLigatures``;
``IgnoreMarks`` or ``UseMarkFilteringSet`` followed by a glyph selector.

For example, in AFDKO::

    lookup test {
        lookupflag IgnoreBaseGlyphs UseMarkFilteringSet @thing;
        # ... rules ...
    } test;

becomes::

    Routine test {
        # ... rules ...
    } IgnoreBases UseMarkFilteringSet @thing;

As in AFDKO, a ``Routine`` may appear within a ``Feature`` block or outside one,
in which case it defines a named routine to be accessed later. In simple cases,
you do not need to wrap rules in a routine inside of a feature block; however,
to combine rules with different flags, you must place the rules within a routine.

FEZ routines do not always correspond directly to OpenType lookups, although in
many cases they will. FEZ routines are more flexible, and may contain a mixture of
rule types and may even contain rules targetting different languages::

    Routine test {
        Substitute [four-arab five-arab] -> [four-urdu five-urdu] <<arab/URD>>;
        Substitute [four-arab five-arab] -> [four-farsi five-farsi] <<arab/FAR>>;
    };

FEZ will resolve these routines into one or more OpenType lookups and alter the
lookup references inside features accordingly when compiling to AFDKO syntax.

FEZ routines themselves may apply to certain script/language combinations, using
the language syntax:

    Routine test {
        Substitute [four-arab five-arab] -> [four-urdu five-urdu];
    } <<arab/URD>>;

As with AFDKO, this syntax can only be used when inside a feature block.
"""

PARSEOPTS = dict(use_helpers=True)

GRAMMAR = """
SIMPLE_FLAG: "RightToLeft" | "IgnoreBases" | "IgnoreLigatures" | "IgnoreMarks"
COMPLEX_FLAG: "MarkAttachmentType" | "UseMarkFilteringSet"
complexflag: COMPLEX_FLAG glyphselector
flag: SIMPLE_FLAG | complexflag
flags: flag*
ROUTINENAME: (LETTER|DIGIT|"_")+
"""

Routine_GRAMMAR = """
?start: action
action: ROUTINENAME? "{" statement+ "}" flags languages?
"""

Routine_beforebrace_GRAMMAR = """
?start: beforebrace
beforebrace: ROUTINENAME?
"""

Routine_afterbrace_GRAMMAR = """
?start: afterbrace
afterbrace: flags languages?
"""

VERBS = ["Routine"]

FLAGS = {
    "RightToLeft": 0x1,
    "IgnoreBases": 0x2,
    "IgnoreLigatures": 0x4,
    "IgnoreMarks": 0x8,
    "MarkAttachmentType": 0xFF00,
    "UseMarkFilteringSet": 0x10
}

ROUTINE_ID = 0

import fontFeatures
from . import FEZVerb

class Routine(FEZVerb):
    def beforebrace(self, args):
        return args

    def languages(self, args):
        rv = []
        while args:
            rv.append(tuple(map((lambda x: "%-4s" % x),args[0:2])))
            args = args[2:]
        return rv

    def afterbrace(self, args):
        if len(args) < 2:
            args.append([])
        return [args[0], args[1]]

    flags = beforebrace

    def complexflag(self, args):
        return (FLAGS[args[0].value], args[1])

    def flag(self, args):
        (flag,) = args

        if isinstance(flag, str):
            return FLAGS[flag]
        elif isinstance(flag, tuple):
            return flag

    def action(self, args):
        (routinename, statements, flags_languages) = args
        routinename = self.parser.expand_statements(routinename, cannot_fail=False)
        flags_languages = self.parser.expand_statements(flags_languages)

        flags, languages = flags_languages
        statements = self.parser.expand_statements(statements)

        if len(routinename) > 0:
            routinename = routinename[0].value
        elif routinename is not None:
            global ROUTINE_ID
            routinename = "FEZUnnamedRoutine{}".format(ROUTINE_ID)
            ROUTINE_ID += 1
        else:
            raise ValueError

        if flags is None: flags = []

        if not statements:
            rr = fontFeatures.RoutineReference(name = routinename)
            return [rr]

        r = fontFeatures.Routine()
        if routinename:
            r.name = routinename
        r.rules = []
        for res in self.parser.filterResults(statements):
            if isinstance(res, fontFeatures.Routine):
                r.rules.extend(res.rules)
            else:
                r.rules.append(res)
        r.flags = 0
        for f in flags:
            if isinstance(f, tuple):
                r.flags |= f[0]
                if f[0] == 0x10:
                    r.markFilteringSet = f[1].resolve(self.parser.fontfeatures, self.parser.font)
                elif f[0] == 0xFF00:
                    r.markAttachmentSet = f[1].resolve(self.parser.fontfeatures, self.parser.font)
            else:
                r.flags |= f
        r.languages = languages
        if not self.parser.current_feature:
            self.parser.fontfeatures.routines.append(r)
        return [r]
