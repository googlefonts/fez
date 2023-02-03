from fez import FezParser
from babelfont import load

import unittest
import re


class TestFezAnchors(unittest.TestCase):
    def assertSufficientlyEqual(self, s1, s2):
        def alltrim(a):
            a = re.sub("lookupflag 0;", "", a)
            a = re.sub("#.*", "", a)
            a = re.sub("\\s+", " ", a)
            a = re.sub("table GDEF.*GDEF;", "", a)
            return a.strip()

        self.assertEqual(alltrim(s1), alltrim(s2))

    def test_parse_to_ff(self):
        p = FezParser(load("tests/data/Roboto-Regular.ttf"))
        p.parseString(
            """
      Anchors A
        top <679 1600>
        bottom <691 0>
      ;

      Anchors B
        top <611 1612>
      ;

      Anchors acutecomb _top <-570 1290>;
      Anchors tildecomb _top <-542 1256>;

      Feature mark { Attach &top &_top @top bases; };
"""
        )

        self.assertEqual(p.fontfeatures.anchors["A"]["top"], (679, 1600))
        self.assertSufficientlyEqual(
            p.fontfeatures.asFea(),
            """    markClass acutecomb <anchor -570 1290> @top;
    markClass tildecomb <anchor -542 1256> @top;

lookup Routine_1 { ;
                        pos base A <anchor 679 1600> mark @top;
            pos base B <anchor 611 1612> mark @top;

} Routine_1;

feature mark {  lookup Routine_1;
} mark;
""",
        )
