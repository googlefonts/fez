import lark

import collections
import pathlib
import re
import warnings

from importlib import import_module
from fontFeatures import FontFeatures
from more_itertools import collapse
from fontTools.feaLib.variableScalar import VariableScalar
from lark.visitors import VisitError
from glyphtools import get_glyph_metrics


def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
    return "# %s\n" % (message)


warnings.formatwarning = warning_on_one_line


class GlyphSelector:
    def __init__(self, selector, suffixes, location):
        self.selector = selector
        self.suffixes = suffixes
        self.location = location

    def __repr__(self):
        return "GlyphSelector<{}>".format(self.as_text())

    def as_text(self):
        if "variable" in self.selector:
            returned = "$" + self.selector["variable"].token.value
        elif "barename" in self.selector:
            returned = self.selector["barename"]
        elif "classname" in self.selector:
            returned = "@" + self.selector["classname"]
        elif "regex" in self.selector:
            returned = "/" + self.selector["regex"] + "/"
        elif "unicodeglyph" in self.selector:
            returned = "U+%04X" % self.selector["unicodeglyph"]
        elif "unicoderange" in self.selector:
            returned = "U+%04X=>U+%04X" % self.selector["unicoderange"].start, self.selector["unicoderange"].stop
        elif "inlineclass" in self.selector:
            items = [
                GlyphSelector(i, (), self.location)
                for i in self.selector["inlineclass"]
            ]
            returned = "[" + " ".join([item.as_text() for item in items]) + "]"

        else:
            raise ValueError("Unknown selector type %s" % self.selector)
        for s in self.suffixes:
            returned = returned + s["suffixtype"] + s["suffix"]
        return returned

    def _apply_suffix(self, glyphname, suffix):
        if suffix["suffixtype"] == ".":
            glyphname = glyphname + "." + suffix["suffix"]
        else:
            if glyphname.endswith("." + suffix["suffix"]):
                glyphname = glyphname[: -(len(suffix["suffix"]) + 1)]
        return glyphname

    def resolve(self, fontfeatures, font, mustExist=True):
        returned = []
        # assert isinstance(font, Font)
        glyphs = font.exportedGlyphs()
        if "variable" in self.selector:
            returned = [self.selector["variable"].resolve_as_glyph()]
        elif "barename" in self.selector:
            returned = [self.selector["barename"]]
        elif "unicodeglyph" in self.selector:
            cp = self.selector["unicodeglyph"]
            glyph = font.unicode_map.get(cp, None)
            if not glyph:
                if not mustExist:
                    returned = []
                else:
                    raise ValueError(
                        "Font does not contain glyph for U+%04X (at %s)"
                        % (cp, self.location)
                    )
            else:
                returned = [glyph]
        elif "unicoderange" in self.selector:
            returned = list(
                collapse(
                    [
                        GlyphSelector({"unicodeglyph": i}, (), self.location).resolve(fontfeatures, font, mustExist=False)
                        for i in self.selector["unicoderange"]
                    ]
                )
            )
            if not returned and mustExist:
                raise ValueError(
                    "Font does not contain any glyphs for U+%04X-U+%04X (at %s)"
                    % (self.selector["unicoderange"][0], self.selector["unicoderange"][-1], self.location)
                )
        elif "inlineclass" in self.selector:
            returned = list(
                collapse(
                    [
                        GlyphSelector(i, (), self.location).resolve(fontfeatures, font)
                        for i in self.selector["inlineclass"]
                    ]
                )
            )
        elif "classname" in self.selector:
            classname = self.selector["classname"]
            if not classname in fontfeatures.namedClasses:
                raise ValueError(
                    "Tried to expand glyph class '@%s' but @%s was not defined (at %s)"
                    % (classname, classname, self.location)
                )
            returned = fontfeatures.namedClasses[classname]
        elif "regex" in self.selector:
            regex = self.selector["regex"]
            try:
                pattern = re.compile(regex)
            except Exception as e:
                raise ValueError(
                    "Couldn't parse regular expression '%s' at %s"
                    % (regex, self.location)
                )

            returned = list(filter(lambda x: re.search(pattern, x), glyphs))
        for s in self.suffixes:
            returned = [self._apply_suffix(g, s) for g in returned]
        if mustExist:
            notFound = list(filter(lambda x: x not in glyphs, returned))
            returned = list(filter(lambda x: x in glyphs, returned))
            if len(notFound) > 0:
                plural = ""
                if len(notFound) > 1:
                    plural = "s"
                glyphstring = ", ".join(notFound)
                warnings.warn(
                    "# Couldn't find glyph%s '%s' in font (%s at %s)"
                    % (plural, glyphstring, self.as_text(), self.location)
                )
        return list(returned)


class ScalarOrVariable:
    def __init__(self, token, parser, metric=None):
        self.token = token
        self.parser = parser
        self.metric = metric
        if hasattr(self.token, "line"):
            self.line = self.token.line
        if hasattr(self.token, "column"):
            self.column = self.token.column
        if isinstance(self.token, lark.Token):
            assert self.token.type == "VARIABLE"
        else:
            assert isinstance(self.token, (int, float, VariableScalar))

    def resolve_as_bool(self):
        if isinstance(self.token, VariableScalar):
            self.token.values[k] = v.resolve_as_integer()
            return any(bool(x) for x in self.token.values.values())
        if not isinstance(self.token, lark.Token):
            return bool(self.token)
        assert self.token.type == "VARIABLE"
        name = self.token.value

        if name not in self.parser.variables:
            raise ValueError("Undefined variable: $%s" % name)

        value = self.parser.variables[name]

        if self.metric:
            return bool(get_glyph_metrics(self.parser.font, value)[self.metric])

        if isinstance(value, ScalarOrVariable): # Of course variables can also point to variables
            return value.resolve_as_bool()

        return bool(value)


    def resolve_as_integer(self):
        if isinstance(self.token, VariableScalar):
            for k,v in self.token.values.items():
                self.token.values[k] = v.resolve_as_integer()
            return self.token
        if not isinstance(self.token, lark.Token):
            return self.token

        assert self.token.type == "VARIABLE"
        name = self.token.value

        if name not in self.parser.variables:
            raise ValueError("Undefined variable: $%s" % name)

        value = self.parser.variables[name]

        if self.metric:
            return get_glyph_metrics(self.parser.font, value)[self.metric]

        if isinstance(value, ScalarOrVariable): # Of course variables can also point to variables
            return value.resolve_as_integer()
        if isinstance(value, str):
            # Hmm. This is the wrong kind of thing. Can we make it the right kind?
            try:
                intvalue = int(value)
                return intvalue
            except ValueError as e:
                raise ValueError("Couldn't make string variable $%s (\"%s\") into an integer" % (name, value))
        else:
            return value

    def resolve_as_glyph(self):
        assert isinstance(self.token, lark.Token), "Integer value used as glyph name (FEZ grammar bug)"
        name = self.token.value
        if name not in self.parser.variables:
            raise ValueError("Undefined variable: $%s" % name)
        value = self.parser.variables[name]
        if isinstance(value, ScalarOrVariable): # Of course variables can also point to variables
            try:
                return value.resolve_as_glyph()
            except AssertionError as e:
                raise ValueError("Variable $%s (=%s) used as a glyph name, but it wasn't one" % (name, value))
        if not isinstance(value, str):
            raise ValueError("Variable $%s (=%s) used as a glyph name, but it wasn't one" % (name, value))
        else:
            return value


GRAMMAR="""
    ?start: statement+

    %import python(COMMENT)
    %import common(LETTER, DIGIT, WS)
    %ignore WS // this only omits whitespace not handled by other rules. e.g. between statements
    %ignore COMMENT
"""

TESTVALUE_METRICS=["width", "lsb", "rsb", "xMin", "xMax", "yMin", "yMax", "rise", "run", "fullwidth"]

HELPERS="""
    statement: verb args ";"
    verb: VERB
    args: arg* | (arg* "{{" statement* "}}" arg*)
    arg: ARG WS*

    VERB: /[A-Z]/ (LETTER | DIGIT | "_")+
    ARG: (/[^\\s;]+/)

    STARTGLYPHNAME: LETTER | DIGIT | "_"
    MIDGLYPHNAME: STARTGLYPHNAME | "." | "-"
    BARENAME: STARTGLYPHNAME MIDGLYPHNAME*
    inlineclass: "[" (WS* (CLASSNAME | BARENAME | REGEX | UNICODEGLYPH))* "]"
    CLASSNAME: "@" STARTGLYPHNAME+

    ANYTHING: /[^\\s]/
    REGEX: "/" ANYTHING* "/"

    HEXDIGIT: /[0-9A-Fa-f]/
    UNICODEGLYPH: "U+" HEXDIGIT~1..6
    unicoderange: UNICODEGLYPH "=>" UNICODEGLYPH

    SUFFIXTYPE: ("." | "~")
    glyphsuffix: SUFFIXTYPE STARTGLYPHNAME+
    glyphselector: (unicoderange | UNICODEGLYPH | REGEX | CLASSNAME | inlineclass | singleglyph) glyphsuffix*
    singleglyph: BARENAME | glyph_variable
    glyph_variable: VARIABLE

    valuerecord: valuerecord_number | fez_value_record | fea_value_record
    valuerecord_number: variable_scalar | basic_valuerecord_number
    basic_valuerecord_number: integer_container
    fez_value_record: "<" ( FEZ_VALUE_VERB "=" valuerecord_number )+ ">"
    FEZ_VALUE_VERB: "xAdvance" | "xPlacement" | "yAdvance" | "yPlacement"
    fea_value_record: "<" valuerecord_number valuerecord_number valuerecord_number valuerecord_number ">"

    variable_scalar: "(" (location_spec ":" basic_valuerecord_number)+ ")"
    location_spec: (axis_location ",")* axis_location
    axis_location: axis_tag "=" basic_valuerecord_number
    axis_tag: /[A-Za-z][A-Za-z0-9]{{,3}}/

    METRIC: {}
    metric_comparison: METRIC COMPARATOR integer_container
    constant_glyphvalue: METRIC "[" BARENAME "]"
    variable_glyphvalue: METRIC "[" glyph_variable "]"

    VARIABLE: "$" LETTER STARTGLYPHNAME*
    integer_container: integer_constant | VARIABLE | variable_glyphvalue
    integer_constant: constant_glyphvalue | SIGNED_NUMBER
    COMPARATOR: ">=" | "<=" | "==" | "<" | ">"

    languages: "<<" (SCRIPT "/" LANG)+ ">>"
    SCRIPT: (LETTER | "2" | "3")~3..4 | "*" // TODO: Validate
    LANG: LETTER~3..4 | "*" // TODO: Validate

    %import common(ESCAPED_STRING, SIGNED_NUMBER, NUMBER, LETTER, DIGIT, WS)
    %ignore WS
""".format(" | ".join(['"{}"'.format(tv) for tv in TESTVALUE_METRICS]))

# These are options usable by plugins to affect parsing. It is recommended to
# leave use_helpers True in almost all cases, unless you want to handle parsing
# of arguments at a low level in your plugin. The helpers parse things like
# glyph classes, regular expressions, etc. in a consistent way across different
# plugins.
PARSEOPTS = dict(use_helpers=True)

class NullParser:
    def parse(*args, **kwargs):
        pass

class Verb:
    transformer = None
    parser = None

class FezParser:
    DEFAULT_PLUGINS = [
        "LoadPlugin",
        "ClassDefinition",
        "Conditional",
        "ForLoop",
        "Feature",
        "Substitute",
        "Position",
        "Chain",
        "Anchors",
        "Kerning",
        "Routine",
        "Include",
        "Variables",
    ]

    plugins = dict()
    variables = dict()
    current_file = pathlib.Path().absolute()
    lark_kwargs = dict(propagate_positions=True)

    parser = lark.Lark(HELPERS+GRAMMAR, **lark_kwargs)

    def __init__(self, font):
        for p in self.DEFAULT_PLUGINS:
            self.load_plugin(p)

        self.font = font
        self.transformer = FezTransformer(self)
        self.fontfeatures = FontFeatures()
        self.fontfeatures.setGlyphClassesFromFont(self.font)
        self.current_feature = None
        self.font_modified = False

    def load_plugin(self, plugin) -> bool:
        if "." not in plugin:
            resolved_plugin = "fez." + plugin
        else:
            resolved_plugin = plugin

        mod = import_module(resolved_plugin)

        if not all([hasattr(mod, attr) for attr in ("PARSEOPTS", "GRAMMAR", "VERBS")]) or \
                not "use_helpers" in mod.PARSEOPTS:
            warnings.warn("Module {} is not a FEZ plugin".format(resolved_plugin))
            return False

        return self.register_plugin(mod, plugin)

    def register_plugin(self, mod, plugin) -> bool:
        verbs = getattr(mod, "VERBS")
        popts = getattr(mod, "PARSEOPTS")
        rules = HELPERS+mod.GRAMMAR if popts["use_helpers"] else mod.GRAMMAR

        for v in verbs:
            verb = Verb()
            verb_grammar = getattr(mod, v+"_GRAMMAR", None)
            verb_bbgrammar = getattr(mod, v+"_beforebrace_GRAMMAR", None)
            verb_abgrammar = getattr(mod, v+"_afterbrace_GRAMMAR", None)

            if verb_grammar:
                verb.parser = lark.Lark(rules+verb_grammar, **self.lark_kwargs)
            else:
                verb.parser = lark.Lark(rules, **self.lark_kwargs)

            if verb_bbgrammar:
                verb.bbparser = lark.Lark(rules+verb_bbgrammar, **self.lark_kwargs)
            else:
                verb.bbparser = NullParser()

            if verb_abgrammar:
                verb.abparser = lark.Lark(rules+verb_abgrammar, **self.lark_kwargs)
            else:
                verb.abparser = NullParser()

            verb.transformer = getattr(mod, v)
            self.plugins[v] = verb

    def parseFile(self, filename):
        """Load a FEZ features file.

        Args:
            filename: Name of the file to read.
        """
        with open(filename, "r") as f:
            data = f.read()
        self.current_file = filename
        return self.parseString(data)

    def parseString(self, s, top_is_statements=True):
        """LoadFEZ features information from a string.

        Args:
            s: Layout rules in FEZ format.
        """
        try:
            rv = self.transformer.transform(self.parser.parse(s))
            if top_is_statements:
                rv = self.expand_statements(rv)
        except VisitError as e:
            raise e.orig_exc
        return rv

    def filterResults(self, results):
        ret = [x for x in collapse(results) if x and not isinstance(x, str)]
        return ret

    def expand_statements(self, statements, cannot_fail=True):
        rv = []
        # Gross
        if isinstance(statements, tuple):
            statements = [statements]
        for verb, args in statements:
            if not args:
                continue
            if args[0] == FEZVerb._THUNK:
                thunk, callback = args
                returned = callback()
                if returned:
                    rv.extend(returned)
                elif cannot_fail:
                    warnings.warn("Bad callback in verb %s" % verb)
            else:
                rv.extend(args)
        return rv


class FezTransformer(lark.Transformer):
    def __init__(self, parser):
        self.parser = parser

    def start(self, args):
        return args

    def statement(self, args):
        verb, args = args
        # print("FezTransformer.statement", verb, args)
        if verb not in self.parser.plugins:
            warnings.warn("Unknown verb: %s" % verb)
            return (verb, args)

        requested_plugin = self.parser.plugins[verb]

        # This branch is called for plugins that use `statement` in their grammar (and use_helpers), it allows the statements to resolve themselves so you aren't given the args as a string. Most such plugins use brackets, e.g. Feature, Routine
        tuple_idxs = list( (i for i,v in enumerate(args) if isinstance(v, tuple)) )
        if len(tuple_idxs) > 0:
            first_tuple_idx, last_tuple_idx = tuple_idxs[0], tuple_idxs[-1]
            statements = [args[ti] for ti in tuple_idxs]
            before = args[:first_tuple_idx]
            after = args[last_tuple_idx+1:]
            before_tree = requested_plugin.bbparser.parse(' '.join(before))
            after_tree  = requested_plugin.abparser.parse(' '.join(after))
            transformer = requested_plugin.transformer(self.parser)
            ret = []
            if before_tree:
                try:
                    before_args = (verb, [transformer._THUNK, lambda : transformer.transform(before_tree)])
                except VisitError as e:
                    raise e.orig_exc
                ret.insert(0, before_args if len(before_args) > 0 else None)
            else:
                ret.insert(0, None)
            ret.append(statements)
            if after_tree:
                try:
                    after_args = (verb, [transformer._THUNK, lambda : transformer.transform(after_tree)])
                except VisitError as e:
                    raise e.orig_exc
                ret.append(after_args if len(after_args) > 0 else None)
            else:
                ret.append(None)
            verb_ret = (verb, [transformer._THUNK, lambda: transformer.action(ret)])
        # For normal plugins that don't take statements
        elif len(args) == 0 or isinstance(args[0], str):
            tree = requested_plugin.parser.parse(' '.join(args))
            try:
                transformer = requested_plugin.transformer(self.parser)
                if transformer.immediate:
                    verb_ret = (verb, requested_plugin.transformer(self.parser).transform(tree))
                else:
                    verb_ret = (verb, [transformer._THUNK, lambda : transformer.transform(tree) ])
            except VisitError as e:
                raise e.orig_exc
        else:
            raise ValueError("Arguments of unknown type: {}".format(type(args)))

        #print("Parsed line...", verb_ret)
        return verb_ret

    def verb(self, args):
        assert len(args) == 1
        return args[0].value

    def args(self, args):
        return args

    def arg(self, args):
        return args[0].value

def _UNICODEGLYPH(u):
    return int(u[2:], 16)

class FEZVerb(lark.Transformer):
    immediate = False
    _THUNK = "__THUNK__"

    def __init__(self, parser):
        self.parser = parser

    def beforebrace(self, args):
        return args

    def SIGNED_NUMBER(self, tok):
        return int(tok)

    def VARIABLE(self, tok):
        return lark.Token("VARIABLE", tok[1:])

    def singleglyph(self, args):
        return args[0]

    def integer_constant(self, args):
        return int(args[0])

    def constant_glyphvalue(self, args):
        (metric, glyph) = args
        return self._get_metrics(glyph.value, metric.value)

    def variable_glyphvalue(self, args):
        (metric, glyph) = args
        return ScalarOrVariable(glyph.token, self.parser, metric=metric.value)

    def _get_metrics(self, glyph, metric=None):
        metrics = get_glyph_metrics(self.parser.font, glyph)
        if metric is not None:
            if metric not in TESTVALUE_METRICS:
                raise ValueError("Unknown metric '%s'" % metric)
            else:
                return metrics[metric]
        else:
            return metrics

    def glyphsuffix(self, args):
        (suffixtype, suffix) = args[0].value, "".join([a.value for a in args[1:]])
        return dict(suffixtype=suffixtype, suffix=suffix)

    def integer_container(self, args):
        if isinstance(args[0], ScalarOrVariable): # variable metric
            return args[0]
        return ScalarOrVariable(args[0], self.parser)

    def glyph_variable(self, args):
        return ScalarOrVariable(args[0], self.parser)

    def unicoderange(self, args):
        return lark.Token("UNICODERANGE", range(_UNICODEGLYPH(args[0].value), _UNICODEGLYPH(args[1].value)+1), args[0].pos_in_stream)

    def inlineclass(self, args):
        return lark.Token("INLINECLASS", [self._glyphselector(t) for t in args if t.type != "WS"])

    def _glyphselector(self, token):
        if isinstance(token, ScalarOrVariable):
            return {"variable": token}
        if token.type == "CLASSNAME":
            val = token.value[1:]
        elif token.type == "REGEX":
            val = token.value[1:-1]
        elif token.type == "UNICODEGLYPH":
            val = _UNICODEGLYPH(token.value)
        else:
            val = token.value

        return {token.type.lower(): val}

    def glyphselector(self, args):
        token, suffixes = args[0], args[1:]
        gs = self._glyphselector(token)
        return GlyphSelector(gs, suffixes, (token.line, token.column))

    def axis_tag(self, args):
        return "%-4s" % args[0].value

    def location_spec(self, args):
        loc = {}
        for spec in args:
             # XXX Parse-time resolution of locations is wrong
            loc[spec.children[0]] = spec.children[1].resolve_as_integer()
        return loc

    def variable_scalar(self, args):
        vs = VariableScalar()
        vs.axes = self.parser.font.axes
        args = iter(args)
        for locspec, value in zip(args, args):
            vs.add_value(locspec, value)
        return ScalarOrVariable(vs, self.parser)

    def valuerecord_number(self, args):
        return args[0]

    def basic_valuerecord_number(self, args):
        return args[0]
