# FEZ — Font Engineering made eaZy

![fez](fez.png)

*I wear a fez now. Fezzes are cool.*

The FEZ language is implemented via a Python library, `fontFeatures`. This format improves over Adobe FEA (`.fea`) in several important ways, and compiles to FEA or to raw GPOS/GSUB binary tables.

## FEZ Quickstart

Class definition is a time consuming element of writing FEA code. FEZ allows regular expressions to be used to define classes; each glyph name in the font is tested against the regular expression, and the glyphs added:

```
DefineClass @sc = /\.sc$/;
```

Ran as:

```sh
fez2fea tests/LibertinusSans-Regular.otf test.fez
```

Results in:

```fea
@sc = [parenleft.sc parenright.sc bracketleft.sc bracketright.sc ...];
```

Simple replacement can be done as easily as:

```
DefineClass @sc = /\.sc$/;
DefineClass @sc_able = @sc~sc;

Feature smcp {
	Substitute @sc_able -> @sc;
};
```

Quite complex classes can be built. All the glyphs which have a smallcap and alternate form:

```
DefineClass @sc_and_alt_able = /.*/ and hasglyph(/$/ .alt) and hasglyph(/$/ .sc);
```

Returning:

```fea
@sc_and_alt_able = [h y germandbls];
```

FEZ can even do substitutions impossible in FEA. For example:

```
DefineClass @digits =    U+0031=>U+0039; # this is range(U+0031, U+0039) inclusive
DefineClass @encircled = U+2474=>U+247C;

# Un-CJK parenthesize
Feature ss01 {
	Substitute @encircled -> parenleft @digits parenright;
};
```

Gives us:

```fea
feature ss01 {
    lookup Routine_1 {
            sub uni2474 by parenleft one parenright;
            sub uni2475 by parenleft two parenright;
            sub uni2476 by parenleft three parenright;
            sub uni2477 by parenleft four parenright;
            sub uni2478 by parenleft five parenright;
            sub uni2479 by parenleft six parenright;
            sub uni247A by parenleft seven parenright;
            sub uni247B by parenleft eight parenright;
            sub uni247C by parenleft nine parenright;
    } Routine_1;
} ss01;
```

FEZ can do much more; see the [plugins documentation](https://fez.readthedocs.io/en/latest/fez-format.html#standard-plugins). Writing your own plugins is as simple as [defining its grammar, verb, and adding a class with an `action()` method](https://fez.readthedocs.io/en/latest/fez-format.html#writing-your-own-plugins).

## Contributors

See the [CONTRIBUTORS.txt](CONTRIBUTORS.TXT) file for the full list of contributors. Major contributions are described below:

* FEZ was originally written by Simon Cozens
* Fred Brennan contributed a new parser and documentation updates
