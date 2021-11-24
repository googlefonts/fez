from fez import FezParser, GlyphSelector, FEZVerb
from babelfont import load
import lark
from lark import Tree, Token
import pytest
import os
import re


def alltrim(a):
    a = re.sub("lookupflag 0;", "", a)
    a = re.sub("#.*", "", a)
    a = re.sub("\\s+", " ", a)
    a = re.sub("table GDEF.*GDEF;", "", a)
    return a.strip()

path, _ = os.path.split(__file__)
fontpath = os.path.join(path, "data", "LibertinusSans-Regular.otf")
font = load(fontpath)

@pytest.fixture
def parser():
    return FezParser(font)

############
# BareName #
############

class BareNameModule:
    GRAMMAR = """
    ?start: action
    action: BARENAME
    """

    VERBS = ["BareName"]

    PARSEOPTS = dict(use_helpers=True)

    class BareName(FEZVerb):
        def action(self, args):
            return args

def test_barename(parser):
    parser.register_plugin(BareNameModule, "BareName")

    def test_barename_string(test_bn):
        s = "BareName %s;" % test_bn
        a = parser.parseString(s)
        assert a == [Token('BARENAME', test_bn)]

    test_barename_string("foo")
    test_barename_string("CH_YEf1")
    test_barename_string("teh-ar")

#############
# ClassName #
#############

class ClassNameModule:
    GRAMMAR = """
    ?start: action
    action: CLASSNAME
    """

    VERBS = ["ClassName"]

    PARSEOPTS = dict(use_helpers=True)

    class ClassName(FEZVerb):
        def action(self, args):
            return args

def test_classname(parser):
    parser.register_plugin(ClassNameModule, "ClassName")

    def test_classname_string(test_bn):
        s = "ClassName %s;" % test_bn
        a = parser.parseString(s)
        assert a == [Token('CLASSNAME', test_bn)]

    test_classname_string("@foo")

###############
# InlineClass #
###############

class InlineClassModule:
    GRAMMAR = """
    ?start: action
    action: inlineclass
    """

    VERBS = ["InlineClass"]

    PARSEOPTS = dict(use_helpers=True)

    class InlineClass(FEZVerb):
        def action(self, args):
            return args

def test_inlineclass(parser):
    s = "InlineClass [a b c @foo];"
    parser.register_plugin(InlineClassModule, "InlineClass")
    a = parser.parseString(s)
    assert a == [Token('INLINECLASS', [{'barename': 'a'}, {'barename': 'b'}, {'barename': 'c'}, {'classname': 'foo'}])]

#################
# GlyphSelector #
#################

class GlyphSelectorModule:
    GRAMMAR = """
    ?start: action
    action: glyphselector
    """

    VERBS = ["GlyphSelector"]

    PARSEOPTS = dict(use_helpers=True)

    class GlyphSelector(FEZVerb):
        def action(self, args):
            return args


def test_glyphselector(parser):
    s = "[foo @bar].sc"
    stmt = "GlyphSelector %s;" % s
    parser.register_plugin(GlyphSelectorModule, "GlyphSelector")
    a = parser.parseString(stmt)
    (gs,) = a
    assert gs.as_text() == s

###############
# DefineClass #
###############

from fez import ClassDefinition

def test_classdefinition_with_conjunction(parser):
    s = """
    DefineClass @foo = /^[a-z]$/;
    DefineClass @bar = /^[g-o]\.sc$/;
    DefineClass @conjunction = @foo.sc & @bar;
    """
    parser.parseString(s)
    matches = set(["{}.sc".format(c) for c in "ghijklmno"])
    assert set(parser.fontfeatures.namedClasses["conjunction"]) == matches

def test_classdefinition_with_predicate(parser):
    s = r"DefineClass @foo = /\.sc$/ & (width > 500);"
    parser.parseString(s)
    assert len(parser.fontfeatures.namedClasses["foo"]) == 49

#################
# Substitutions #
#################

def test_substitute(parser):
    s = "Feature rlig { Substitute a -> b; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; sub a by b; } Routine_1; feature rlig { lookup Routine_1; } rlig;"
    )


def test_substitute2(parser):
    s = "Feature rlig { Substitute [a b] -> [c d]; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; sub [a b] by [c d]; } Routine_1; feature rlig { lookup Routine_1; } rlig;"
    )

###############
# Positioning #
###############
def test_positioning_simple(parser):
    s = "Feature kern { Position (b <xAdvance=123>); };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; pos b 123; } Routine_1; feature kern { lookup Routine_1; } kern;"
    )

#############
# Variables #
#############
def test_integer_variable(parser):
    s = "Set $a = 123; Feature kern { Position (b <xAdvance=$a>); };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; pos b 123; } Routine_1; feature kern { lookup Routine_1; } kern;"
    )


def test_glyph_variable(parser):
    s = "Set $a = 123; Set $glyph = \"b\"; Feature kern { Position ($glyph <xAdvance=$a>); };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; pos b 123; } Routine_1; feature kern { lookup Routine_1; } kern;"
    )


def test_wrong_context(parser):
    s = "Set $a = 123; Set $glyph = \"b\"; Feature kern { Position ($a <xAdvance=$a>); };"
    with pytest.raises(ValueError):
        parser.parseString(s)


def test_boolean_variable_true(parser):
    s = "Set $a = 1; Feature rlig { If $a { Substitute a -> b; }; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; sub a by b; } Routine_1; feature rlig { lookup Routine_1; } rlig;"
    )


def test_boolean_variable_false(parser):
    s = "Set $a = 0; Feature rlig { If $a { Substitute a -> b; }; If not $a { Substitute c -> d; }; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; sub c by d; } Routine_1; feature rlig { lookup Routine_1; } rlig;"
    )

###########
# Routine #
###########
def test_routine(parser):
    s = "Feature rlig { Routine foo { Substitute a -> b; } IgnoreMarks <<mym2/dflt>>; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup foo { lookupflag IgnoreMarks; ; sub a by b; } foo; feature rlig { script mym2; language dflt; lookup foo; } rlig;"
    )

def test_routine2(parser):
    s = "Routine foo { Substitute a -> b; } IgnoreMarks;"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup foo { lookupflag IgnoreMarks; ; sub a by b; } foo;"
    )



################
# Glyph values #
################
def test_glyph_value(parser):
    s = "Set $b_width = width[b];"
    parser.parseString(s)
    assert parser.variables["b_width"].resolve_as_integer() == 504;


################
# For loops    #
################
def test_for_loop(parser):
    s = "Feature rlig { For $g in /^[a-z]$/ { If width[$g] >= width[w] { Substitute $g -> $g.sc; }; }; };"
    parser.parseString(s)
    assert alltrim(parser.fontfeatures.asFea()) == alltrim(
        "lookup Routine_1 { ; sub m by m.sc; sub w by w.sc; } Routine_1; feature rlig { lookup Routine_1; } rlig;"
    )

