from fez import HELPERS, FEZVerb, FezParser
import lark
from lark.visitors import VisitError
from babelfont import Font, Axis, Glyph
from babelfont.Glyph import GlyphList

test_font = Font()
test_font.axes = [
    Axis(name="width", tag="wdth", min=100, max=400, default=200),
    Axis(name="weight", tag="wght", min=100, max=1000, default=900)
]
test_font.glyphs.append(Glyph(name="a"))


def test_variable_scalar():
    GRAMMAR="""
        ?start: variable_scalar+

        %import python(COMMENT)
        %import common(LETTER, DIGIT, WS)
        %ignore WS
        %ignore COMMENT
    """
    parser = lark.Lark(HELPERS+GRAMMAR)
    s = "(wght=200:-100 wght=900:-150 wght=900,wdth=150:-120)"
    parser.font = test_font
    transformer = FEZVerb(parser)
    try:
        scalar = transformer.transform(parser.parse(s)).resolve_as_integer()
    except VisitError as e:
        raise e.orig_exc
    assert scalar.get_deltas_and_supports() == (
        [-150, 30, 50],
        [{}, {'wdth': (-0.5, -0.5, 0)}, {'wght': (-0.875, -0.875, 0)}]
    )

def test_variable_pos():
    parser = FezParser(test_font)
    s = """
Routine Foo {
    Position (a <xAdvance=(wght=200:-100 wght=900:-150 wght=900,wdth=150:-120)>);
};
"""
    parser.parseString(s)
    assert parser.fontfeatures.routines[0].rules[0].asFea() == """pos a (wdth=200,wght=200:-100 wdth=200,wght=900:-150 wdth=150,wght=900:-120);"""
