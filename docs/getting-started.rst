Getting Started
===============

What do I need to know?
-----------------------

To use FEZ, you will need to be aware of what OpenType programming is and what
capabilities are available: for example, what a contextual substitution does,
what a feature is, and so on. If you've ever worked with the examples in the
`OpenType Cookbook <http://opentypecookbook.com/>`_, you will be fine. If not,
I recommend starting with my `Introduction to OpenType Programming <https://simoncozens.github.io/fonts-and-layout/features.html>`_.

For slightly advanced usage of FEZ, you'll want to know regular expressions.
(You can get by without them, but they'll make things *so* much cooler.)
`RegexOne <https://regexone.com>`_ is a great tutorial for people who like to
learn by experiment and example.

In order to develop your own plugins, which you will want to do if you are
automating particularly tricky rules, you will need to know Python. FEZ uses
some Python libraries to inspect the font file (`Babelfont 3 <https://simoncozens.github.io/babelfont/>`_)
and to represent OpenType rules (`fontFeatures <https://fontfeatures.readthedocs.io/en/latest/>`_).
Learning how to use these libraries would be useful, but you should be able to
pick up the main ideas just by reading and modifying the examples in this documentation.

Installing
----------

FEZ is a Python library; you can install it with `pip install fez-language`.

Hello FEZ
---------

To use Adobe's AFDKO language, you write a ``.fea`` file; to use FEZ, you write
a ``.fez`` file.

Ah, but of course, it's a little more complicated than that. Because AFDKO is
built into most font editors, the process of writing out the feature file and
compiling the rules into the binary font is all done behind your back. Since
FEZ is not built into font editors, we have to do some of this work by hand.

Let's assume we have a fairly standard setup: we have a Glyphs source file in
``source/MyFont.glyphs``, and we export our fonts to ``fonts/ttf/MyFont-Regular.ttf``.
If you're using a different font editor, don't worry - just adjust the instructions
appropriately for your source file.

Let's first create our FEZ file with some rules in. You can really put the FEZ
file wherever you like, but I would recommend placing it inside the ``source/``
directory as well. We'll create a file in a text editor (I use
`Sublime Text <https://www.sublimetext.com>`_, but anything will do) called
``source/MyFont.fez``. It doesn't have to be called that, but that's what we're
going to call it. Paste in the following contents and save it::

  Feature liga {
    Substitute f f -> f_f;
  };

We're going to compile this into our font in three short steps:

- First, export the font as normal from your font editor. It won't have any
  feature rules, but that's OK for now. I'll assume we have our font sitting
  in ``fonts/ttf/MyFont-Regular.ttf``.

- Now we'll convert our FEZ file into an AFDKO ``.fea`` file. Again, it's
  up to you where you put this and what you call it, but an emerging standard is
  to create a directory ``source/build`` for things which are generated as
  part of the build process. Let's make an empty directory called ``build``
  under ``source/``.

  To convert FEZ to AFDKO, we use a command-line utility called ``fez2fea``. This
  was installed when we installed ``fez-language`` above. From a terminal application
  sat inside the root directory of the font project, do this::

    fez2fea source/MyFont.glyphs source/MyFont.fez > source/build/features.fea

  That's::

    fez2fea (font source) (FEZ source) > (where to put FEA file)

  Notice that we give ``fez2fea`` the font source file as well as the FEZ file we
  just wrote. The font source file can be either Glyphs, UFO, or even TrueType binary.
  (Source files work better for handling things like anchors.) There's also rudimentary
  support for FontLab ``.vfj`` source files.

  The reason we provide the font source file is that FEZ needs to be able to look
  at the glyphs in the font and take action based on various glyph properties. This
  gets exciting, and we'll see examples of it later.

- If that went well, we will have an Adobe feature file in ``source/build/features.fea``.
  Now we need to get those rules into the font binary::

    fonttools feaLib -o fonts/ttf/MyFont-Regular.ttf source/build/features.fea fonts/ttf/MyFont-Regular.ttf

  That's::

    fonttools feaLib -o (final font) (FEA file we made) (exported font)

  but in our case we want to write the final font onto the same file we exported
  from Glyphs.

Congratulations! You've made your first font with FEZ rules. Now since that was
a bit of a process, you might want to write a build script or a ``Makefile`` to put those
two commands (``fez2fea`` and ``fonttools feaLib``) together - especially if you
also use ``fontmake`` to export your font file::

  #!/bin/sh
  fontmake -o variable -g source/MyFont.glyphs
  fez2fea source/MyFont.glyphs source/MyFont.fez > source/build/features.fea
  fonttools feaLib -o fonts/ttf/MyFont-VF.ttf source/build/features.fea variable/MyFont-VF.ttf

They say I should put a motivating example here
-----------------------------------------------

In the introduction, I mentioned that FEZ is *expressive* and *extensible*. Let's
look at an example of that. We'll break down how to write code like this in the
next chapter, but seeing it in action will give you an example of what FEZ is all
about.

Let's suppose we're working on a Myanmar font and want to form below-base
conjuncts. The basic rule for this is: if we see the sequence
``virama-myanmar`` followed by some consonant, we replace it with the
corresponding glyph whose name ends with the ``.below`` suffix if that glyph
exists.

Writing these features in AFDKO requires us to write out all the possibilities
by hand::

  feature rlig {
    sub virama-myanmar ka-myanmar by ka-myanmar.below;
    sub virama-myanmar kha-myanmar by kha-myanmar.below;
    sub virama-myanmar ga-myanmar by ga-myanmar.below;
    sub virama-myanmar gha-myanmar by gha-myanmar.below;
    # ...
  } rlig;

There are various problems with this:

- *It's boring and repetitive*. I mean, we've got a computer right here that is
  really good at doing boring and repetitive tasks for us. We should probably use it.
- *It's error-prone*. How sure are you that you listed all of them? When you took
  away the glyphs that don't form conjuncts, did you also remove the rules from
  the feature file? You now have two things to keep in sync.
- *It obscures the intent*. Make sure that you understand this, because it is one
  of the philosophical keys behind FEZ.

  Because we are manually expressing all the possibilities, we are telling the
  computer not just *what* to do but also explicitly *how* to do it. We had a general
  rule in our head - virama + consonant = subjoined - but we've been forced to convert
  it to a lot of specific rules. In this particular example, that's not too bad
  because they're a nice pattern and you can work out the "what" based on the "how".
  In a moment, we'll see another example where the "what" is completely obscured by
  the "how".

FEZ attempts to allow you to express rules closer to the "what" level. What we
want to do is replace virama + consonant-forming-below-form with the subjoined form.
Here's one way to express it::

  DefineClass @subjoining_consonant = hasglyph(/$/ ".below");

  Feature rlig {
    Substitute virama-myanmar @subjoining_consonant -> @subjoining_consonant.below;
  };

Don't worry if you don't understand the syntax right now! We're only at the start
of the manual, and we'll unpack it in later chapters! But to briefly explain what
this is doing:

- First we define a class ``subjoining_consonant`` which consists of all the glyphs
  for which there is a corresponding glyph in the font with the same name plus
  ``.below``.

- Then we ligate the sequence ``virama-myanmar`` followed by one of those consonants
  with the corresponding ``.below`` glyph.

Now if you add or remove glyphs from the font, you don't need to update your rules,
because your rules are expressing *what* to do, not *how* to do it. The computer
works out the *how*. That's what computers are for.

Here's another way to say it::

  DefineClass @conjunct = /\.below$/;
  DefineClass @subjoining_consonant = @conjunct~below;

  Feature rlig {
    Substitute virama-myanmar @subjoining_consonant -> @conjunct;
  };

- First we define the class of glyphs whose names end in ``.below``.

- Define a class containing the glyphs in ``@conjunct`` but with the ``.below``
  suffix lopped off.

- We ligate ``virama-myanmar`` plus each member of the subjoining class for each
  member of the ``@conjunct`` class.

Here's how *I* would say it::

  Feature rlig {
    Substitute virama-myanmar /.below$/~below -> $2;
  };

- Find all the glyphs that end in ``.below``, lop the ``.below`` off, and substitute
  that with the thing you first thought of.

Finally, here's another way to say it::

  Feature rlig {
    Substitute virama-myanamar ka-myanmar -> ka-myanmar.below;
    Substitute virama-myanamar kha-myanmar -> kha-myanmar.below;
    ...
  };

Of course this rather defeats the point of the language. But it is worth
repeating: you can program FEZ this way if you want to. The fancy stuff is just
there to help you. You don't need to use it if you don't want to. In fact, that's
the point of expressibility - there's more than one way to do it, and you choose
the one that best fits your understanding of the task and the language. As you
get more comfortable with the language, you will be able to take more shortcuts.

One more example before we look at the language in depth. We're still doing Myanmar.
Again we'll start with Adobe feature syntax::

  @w2 = [ka-myanmar gha-myanmar cha-myanmar nnya-myanmar ta-myanmar tha-myanmar
         bha-myanmar ya-myanmar la-myanmar sa-myanmar ha-myanmar a-myanmar];

No rules for now, just a class. But why *those* particular glyphs? Well, they
happen to be the ones that, when following a medial ra, we will later
substitute the medial ra with a wide form of the glyph::

  sub medialRa-myanmar' @w2 by medialRa-myanmar.w2;

But how did that class come about, with those exact glyphs in it? How do we
convince ourselves that we have the right glyphs? What if the font changes - are they
still the right glyphs? Did we forget any?

Here's one way to say that in FEZ::

  DefineClass @w2 = @baseconsonants & (width > 800);

Oh, now I see what you mean! You want all the glyphs which are part of the base
consonants class and additionally have a width of over 800 units. Expressing it
this way isn't going to go wrong; we won't leave out a glyph by mistake, nor do
we need to update the rule when the font changes. We're expressing intent, not
action.

This idea of expressing intent not action reaches its height in *extensibility*.
Extensibility means that you can package up the computation of different rules
into their own "verbs" in the FEZ language. What does this mean? A common task
in Devanagari is to replace the form of the i-matra (ikar) glyph with a
width-specific form based on the width of the base character following it.
In AFDKO, it's something like this::

  feature pres {
    sub iMatra-deva' [ ... width 2 glyphs here ... ] by iMatra-deva.w2;
    sub iMatra-deva' [ ... width 3 glyphs here ... ] by iMatra-deva.w3;
    sub iMatra-deva' [ ... width 4 glyphs here ... ] by iMatra-deva.w4;
  } pres;

And then of course you have to work out which glyphs go in which class. But again,
we have a computer which can work it out for you. Here's how you say it in FEZ::

  LoadPlugin IMatra;

  Feature pres {
    IMatra @consonants : iMatra-deva -> /^iMatra-deva/;
  };

We've extended the language using the ``IMatra`` extension which adds a new verb to
the language called ``IMatra``. Then we use this verb to compute and perform the
substitutions for us. The intent is practically self-describing.

Hopefully I've convinced you that this is a good thing to do. Now let's look at
how the FEZ language works.
