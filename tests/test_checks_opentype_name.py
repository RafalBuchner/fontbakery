import os

from fontTools.ttLib import TTFont

from conftest import check_id
from fontbakery.constants import (
    NameID,
    PlatformID,
    WindowsEncodingID,
    WindowsLanguageID,
    MacintoshEncodingID,
    MacintoshLanguageID,
)
from fontbakery.message import Message
from fontbakery.status import INFO, WARN, PASS, FAIL, SKIP
from fontbakery.result import Subresult
from fontbakery.codetesting import (
    assert_PASS,
    assert_results_contain,
    portable_path,
    TEST_FILE,
)


@check_id("opentype/name/empty_records")
def test_check_name_empty_records(check):
    font_path = TEST_FILE("source-sans-pro/OTF/SourceSansPro-Regular.otf")
    test_font = TTFont(font_path)

    assert_PASS(check(test_font), "with a font with fully populated name records.")

    test_font["name"].names[3].string = b""
    assert_results_contain(
        check(test_font), FAIL, "empty-record", "with a completely empty string."
    )

    test_font["name"].names[3].string = b" "
    assert_results_contain(
        check(test_font),
        FAIL,
        "empty-record",
        "with a string that only has whitespace.",
    )


@check_id("opentype/monospace")
def test_check_monospace(check):
    """Checking correctness of monospaced metadata."""

    import string
    from fontbakery.constants import PANOSE_Proportion, IsFixedWidth

    # This check has a large number of code-paths
    # We'll make sure to test them all here.
    #
    # --------------------------------------------
    # Starting with non-monospaced code-paths:
    # --------------------------------------------

    # Our reference Mada Regular is a non-monospace font
    # know to have good metadata for this check.
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))
    assert_results_contain(
        check(ttFont), PASS, "good", "with a good non-monospace font..."
    )

    # We'll mark it as monospaced on the post table and make sure it fails:
    ttFont["post"].isFixedPitch = 42  # *any* non-zero value means monospaced
    assert_results_contain(
        check(ttFont),
        FAIL,
        "bad-post-isFixedPitch",
        "with a non-monospaced font with bad post.isFixedPitch value ...",
    )

    # restore good value:
    ttFont["post"].isFixedPitch = IsFixedWidth.NOT_MONOSPACED

    # Now we mark it as monospaced on the OS/2 table and it should also fail:
    original_proportion = ttFont["OS/2"].panose.bProportion
    ttFont["OS/2"].panose.bProportion = PANOSE_Proportion.MONOSPACED
    assert_results_contain(
        check(ttFont),
        FAIL,
        "bad-panose",
        "with a non-monospaced font with bad"
        " OS/2.panose.bProportion value (MONOSPACED) ...",
    )

    # restore good value
    ttFont["OS/2"].panose.bProportion = original_proportion

    # Now we try with very little ASCII characters in the font
    cmap = ttFont["cmap"]
    for subtable in list(cmap.tables):
        # Remove A-Z, a-z from cmap
        for code in list(map(ord, string.ascii_letters)):
            if subtable.cmap.get(code):
                del subtable.cmap[code]
    assert_results_contain(
        check(ttFont), PASS, "good", "with a good non-monospace font..."
    )

    # --------------------------------------------
    # And now we test the monospaced code-paths:
    # --------------------------------------------

    print("Test PASS with a good monospaced font...")
    # Our reference OverpassMono Regular is know to be
    # a monospaced font with good metadata here.
    ttFont = TTFont(TEST_FILE("overpassmono/OverpassMono-Regular.ttf"))

    subresult = check(ttFont)[-1]
    # WARN is emitted when there's at least one outlier.
    # I don't see a good reason to be picky and also test that one separately here...
    assert (subresult.status == WARN and subresult.message.code == "mono-outliers") or (
        subresult.status == PASS and subresult.message.code == "mono-good"
    )

    # Mark it as a non-monospaced on the post table and it should
    # result in a WARN, if we find outliers
    ttFont["post"].isFixedPitch = IsFixedWidth.NOT_MONOSPACED
    assert_results_contain(
        check(ttFont),
        WARN,
        "mono-outliers",
        "with a monospaced font containing a few width outliers...",
    )

    # or a FAIL otherwise:
    for g in ttFont["hmtx"].metrics:  # fake it!
        ttFont["hmtx"].metrics[g] = (123, 456)  # (adv, lsb)
    assert_results_contain(
        check(ttFont),
        FAIL,
        "mono-bad-post-isFixedPitch",
        "with a monospaced font with bad post.isFixedPitch value ...",
    )

    # restore original testing font:
    ttFont = TTFont(TEST_FILE("overpassmono/OverpassMono-Regular.ttf"))
    ttFont["post"].isFixedPitch = IsFixedWidth.NOT_MONOSPACED

    # There are several bad panose proportion values for a monospaced font.
    # Only PANOSE_Proportion.MONOSPACED would be valid.
    # So we'll try all the bad ones here to make sure all of them emit a FAIL:
    bad_monospaced_panose_values = [
        PANOSE_Proportion.ANY,
        PANOSE_Proportion.NO_FIT,
        PANOSE_Proportion.OLD_STYLE,
        PANOSE_Proportion.MODERN,
        PANOSE_Proportion.EVEN_WIDTH,
        PANOSE_Proportion.EXTENDED,
        PANOSE_Proportion.CONDENSED,
        PANOSE_Proportion.VERY_EXTENDED,
        PANOSE_Proportion.VERY_CONDENSED,
    ]
    for bad_value in bad_monospaced_panose_values:
        ttFont["OS/2"].panose.bProportion = bad_value
        # again, we search the expected FAIL because
        # we may algo get an outliers WARN here:
        assert_results_contain(
            check(ttFont),
            FAIL,
            "mono-bad-panose",
            f"Test FAIL with a monospaced font with bad"
            f" OS/2.panose.bProportion value ({bad_value}) ...",
        )

    # restore good values
    ttFont["post"].isFixedPitch = 1
    ttFont["OS/2"].panose.bProportion = PANOSE_Proportion.MONOSPACED

    # Now we try with very little ASCII characters in the font
    cmap = ttFont["cmap"]
    for subtable in list(cmap.tables):
        # Remove A-Z, a-z from cmap
        for code in list(map(ord, string.ascii_letters)):
            if subtable.cmap.get(code):
                del subtable.cmap[code]

    subresult = check(ttFont)[-1]
    status, message = subresult.status, subresult.message
    # WARN is emitted when there's at least one outlier.
    # I don't see a good reason to be picky and also test that one separately here...
    assert (status == WARN and message.code == "mono-outliers") or (
        status == PASS and message.code == "mono-good"
    )

    # Confirm the check yields FAIL if the font doesn't have a required table
    del ttFont["OS/2"]
    assert_results_contain(check(ttFont), FAIL, "lacks-table")

    # --------------------------------------------
    # And now we test a CFF font:
    # --------------------------------------------
    ttFont = TTFont(TEST_FILE("source-sans-pro/OTF/SourceSansPro-Regular.otf"))
    assert_results_contain(
        check(ttFont), PASS, "good", "with a good non-monospace font..."
    )


@check_id("opentype/name/match_familyname_fullfont")
def test_check_name_match_familyname_fullfont(check):
    """Does full font name begin with the font family name?"""

    # Our reference Mada Regular is known to be good
    ttFont = TTFont(TEST_FILE("mada/Mada-Regular.ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont))

    EXPECTED_NAME_STRING = "Mada"
    BAD_PREFIX = "bad-prefix"
    name_table = ttFont["name"]
    platform_id = 3
    encoding_id = 1
    language_id = 0x0409
    family_name_id = NameID.FONT_FAMILY_NAME
    full_name_id = NameID.FULL_FONT_NAME

    # Alter the font's full_name string and re-run the check.
    # 1. Retrieve the existing name strings and assert that they're the expected ones.
    family_name = name_table.getName(
        family_name_id, platform_id, encoding_id, language_id
    ).toUnicode()
    assert family_name == EXPECTED_NAME_STRING

    full_name_before = name_table.getName(
        full_name_id, platform_id, encoding_id, language_id
    ).toUnicode()
    assert full_name_before == EXPECTED_NAME_STRING

    # 2. Prefix the full_name string, and update the font's name record.
    name_table.setName(
        f"{BAD_PREFIX}{full_name_before}",
        full_name_id,
        platform_id,
        encoding_id,
        language_id,
    )

    # 3. Retrieve the updated name string, and assert that it's the expected one.
    full_name_after = name_table.getName(
        full_name_id, platform_id, encoding_id, language_id
    ).toUnicode()
    assert full_name_after != family_name
    assert full_name_after == f"{BAD_PREFIX}{EXPECTED_NAME_STRING}"
    assert full_name_after.startswith(BAD_PREFIX)

    # 4. Now re-run the check. It should yield FAIL because the full_name string
    # no longer starts with the family_name string.
    msg = assert_results_contain(check(ttFont), FAIL, "mismatch-font-names")
    assert msg == (
        f"On the 'name' table, the full font name {full_name_after!r}"
        f" does not begin with the font family name {family_name!r}"
        f" in platformID {platform_id},"
        f" encodingID {encoding_id},"
        f" languageID {language_id}({language_id:04X}),"
        f" and nameID {family_name_id}."
    )

    # Remove the modified full name record and re-run the check.
    # It should yield FAIL because the name table won't contain a full name string
    # to compare with the family name string.
    name_table.removeNames(full_name_id, platform_id, encoding_id, language_id)
    msg = assert_results_contain(check(ttFont), FAIL, "missing-font-names")
    assert msg == (
        f"The font's 'name' table lacks a pair of records with"
        f" nameID {NameID.FULL_FONT_NAME} (Full name),"
        f" and at least one of"
        f" nameID {NameID.FONT_FAMILY_NAME} (Font Family name),"
        f" {NameID.TYPOGRAPHIC_FAMILY_NAME} (Typographic Family name),"
        f" or {NameID.WWS_FAMILY_NAME} (WWS Family name)."
    )

    # Run the check on a CJK font. The font's 'name' table contains
    # English-US (1033/0x0409) and Japanese (1041/0x0411) records. It should PASS.
    ttFont = TTFont(TEST_FILE("cjk/SourceHanSans-Regular.otf"))
    assert_PASS(check(ttFont))

    name_table = ttFont["name"]
    decode_error_msg_prefix = (
        f"On the 'name' table, the name record"
        f" for platformID {platform_id},"
        f" encodingID {encoding_id},"
        f" languageID {language_id}({language_id:04X}),"
    )

    # Replace the English full name string with data that can't be 'utf_16_be'-decoded.
    # This will cause a UnicodeDecodeError which will yield a FAIL.
    name_table.setName(
        "\xff".encode("utf_7"), full_name_id, platform_id, encoding_id, language_id
    )
    msg = assert_results_contain(
        check(ttFont), FAIL, f"cannot-decode-nameid-{full_name_id}"
    )
    assert msg == (
        f"{decode_error_msg_prefix} and nameID {full_name_id} failed to be decoded."
    )

    # This time replace the family name string instead.
    # This should still trigger a UnicodeDecodeError.
    name_table = ttFont["name"]
    name_table.setName(
        "\xff".encode("utf_7"), family_name_id, platform_id, encoding_id, language_id
    )
    msg = assert_results_contain(
        check(ttFont), FAIL, f"cannot-decode-nameid-{family_name_id}"
    )
    assert msg == (
        f"{decode_error_msg_prefix} and nameID {family_name_id} failed to be decoded."
    )


def assert_name_table_check_result(
    ttFont, index, name, check, value, expected_result, expected_keyword=None
):
    backup = name.string
    # set value
    ttFont["name"].names[index].string = value.encode(name.getEncoding())
    # run check
    subresults = check(ttFont)
    if subresults == []:
        subresult = Subresult(PASS, Message("ok", "All looks good!"))
    else:
        subresult = subresults[-1]

    status, message = subresult.status, subresult.message
    # restore value
    ttFont["name"].names[index].string = backup
    assert status == expected_result
    if expected_keyword:
        assert message.code == expected_keyword


@check_id("opentype/family_naming_recommendations")
def test_check_family_naming_recommendations(check):
    """Font follows the family naming recommendations ?"""

    # Our reference Mada Medium is known to be good
    ttFont = TTFont(TEST_FILE("mada/Mada-Medium.ttf"))

    # So it must PASS the check:
    assert_PASS(check(ttFont), "with a good font...")

    # We'll test rule violations in all entries one-by-one
    for index, name in enumerate(ttFont["name"].names):
        # and we'll test all INFO/PASS code-paths for each of the rules:
        def name_test(value, expected, keyword=None):
            assert_name_table_check_result(
                ttFont, index, name, check, value, expected, keyword
            )  # pylint: disable=cell-var-from-loop

        if name.nameID == NameID.POSTSCRIPT_NAME:
            print("== NameID.POST_SCRIPT_NAME ==")

            print("Test PASS: A name with a single hyphen is OK...")
            # A single hypen in the name is OK:
            name_test("Big-Bang", PASS)

            print("Test INFO: Exceeds max length (63)...")
            name_test("A" * 64, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 63, PASS)

        elif name.nameID == NameID.FULL_FONT_NAME:
            print("== NameID.FULL_FONT_NAME ==")

            print("Test INFO: Exceeds max length (63)...")
            name_test("A" * 64, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 63, PASS)

        elif name.nameID == NameID.FONT_FAMILY_NAME:
            print("== NameID.FONT_FAMILY_NAME ==")

            print("Test INFO: Exceeds max length (31)...")
            name_test("A" * 32, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 31, PASS)

        elif name.nameID == NameID.FONT_SUBFAMILY_NAME:
            print("== NameID.FONT_SUBFAMILY_NAME ==")

            print("Test INFO: Exceeds max length (31)...")
            name_test("A" * 32, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 31, PASS)

        elif name.nameID == NameID.TYPOGRAPHIC_FAMILY_NAME:
            print("== NameID.TYPOGRAPHIC_FAMILY_NAME ==")

            print("Test INFO: Exceeds max length (31)...")
            name_test("A" * 32, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 31, PASS)

        elif name.nameID == NameID.TYPOGRAPHIC_SUBFAMILY_NAME:
            print("== NameID.FONT_TYPOGRAPHIC_SUBFAMILY_NAME ==")

            print("Test INFO: Exceeds max length (31)...")
            name_test("A" * 32, INFO, "bad-entries")

            print("Test PASS: Does not exceed max length...")
            name_test("A" * 31, PASS)


@check_id("opentype/name/postscript_vs_cff")
def test_check_name_postscript_vs_cff(check):
    # Test a font that has matching names. Check should PASS.
    ttFont = TTFont(TEST_FILE("source-sans-pro/OTF/SourceSansPro-Bold.otf"))
    assert_PASS(check(ttFont))

    # Change the name-table string. Check should FAIL.
    other_name = "SomeOtherFontName"
    ttFont["name"].setName(
        other_name,
        NameID.POSTSCRIPT_NAME,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    msg = assert_results_contain(check(ttFont), FAIL, "ps-cff-name-mismatch")
    assert msg == (
        f"Name table PostScript name '{other_name}' does not match"
        " CFF table FontName 'SourceSansPro-Bold'."
    )

    # Change the CFF-table name. Check should FAIL.
    ttFont["CFF "].cff.fontNames = ["name1", "name2"]
    msg = assert_results_contain(check(ttFont), FAIL, "cff-name-error")
    assert msg == "Unexpected number of font names in CFF table."

    # Now test with a TrueType font.
    # The test should be skipped due to an unfulfilled condition.
    ttFont = TTFont(TEST_FILE("source-sans-pro/TTF/SourceSansPro-Bold.ttf"))
    msg = assert_results_contain(check(ttFont), SKIP, "unfulfilled-conditions")
    assert "Unfulfilled Conditions: is_cff" in msg

    # Now test with a CFF2 font.
    # The test should be skipped due to an unfulfilled condition.
    ttFont = TTFont(TEST_FILE("source-sans-pro/VAR/SourceSansVariable-Italic.otf"))
    msg = assert_results_contain(check(ttFont), SKIP, "unfulfilled-conditions")
    assert "Unfulfilled Conditions: is_cff" in msg


@check_id("opentype/name/postscript_name_consistency")
def test_check_name_postscript_name_consistency(check):
    base_path = portable_path("data/test/source-sans-pro/TTF")
    font_path = os.path.join(base_path, "SourceSansPro-Regular.ttf")
    test_font = TTFont(font_path)

    # SourceSansPro-Regular only has one name ID 6 entry (for Windows),
    # let's add another one for Mac that matches the Windows entry:
    test_font["name"].setName(
        "SourceSansPro-Regular",
        NameID.POSTSCRIPT_NAME,
        PlatformID.MACINTOSH,
        MacintoshEncodingID.ROMAN,
        MacintoshLanguageID.ENGLISH,
    )
    assert_PASS(check(test_font))

    # ...now let's change the Mac name ID 6 entry to something else:
    test_font["name"].setName(
        "YetAnotherFontName",
        NameID.POSTSCRIPT_NAME,
        PlatformID.MACINTOSH,
        MacintoshEncodingID.ROMAN,
        MacintoshLanguageID.ENGLISH,
    )
    assert_results_contain(check(test_font), FAIL, "inconsistency")


@check_id("opentype/family/max_4_fonts_per_family_name")
def test_check_family_max_4_fonts_per_family_name(check):
    base_path = portable_path("data/test/source-sans-pro/OTF")

    font_names = [
        "SourceSansPro-Black.otf",
        "SourceSansPro-BlackItalic.otf",
        "SourceSansPro-Bold.otf",
        "SourceSansPro-BoldItalic.otf",
        "SourceSansPro-ExtraLight.otf",
        "SourceSansPro-ExtraLightItalic.otf",
        "SourceSansPro-Italic.otf",
        "SourceSansPro-Light.otf",
        "SourceSansPro-LightItalic.otf",
        "SourceSansPro-Regular.otf",
        "SourceSansPro-Semibold.otf",
        "SourceSansPro-SemiboldItalic.otf",
    ]

    font_paths = [os.path.join(base_path, n) for n in font_names]

    test_fonts = [TTFont(x) for x in font_paths]

    # try fonts with correct family name grouping
    assert_PASS(check(test_fonts))

    # now set 5 of the fonts to have the same family name
    for font in test_fonts[:5]:
        name_records = font["name"].names
        for name_record in name_records:
            if name_record.nameID == 1:
                # print(repr(name_record.string))
                name_record.string = "foobar".encode("utf-16be")

    assert_results_contain(check(test_fonts), FAIL, "too-many")


@check_id("opentype/family/consistent_family_name")
def test_check_consistent_font_family_name(check):
    base_path = portable_path("data/test/source-sans-pro/OTF")

    font_names = [
        "SourceSansPro-Black.otf",
        "SourceSansPro-BlackItalic.otf",
        "SourceSansPro-Bold.otf",
        "SourceSansPro-BoldItalic.otf",
        "SourceSansPro-ExtraLight.otf",
        "SourceSansPro-ExtraLightItalic.otf",
        "SourceSansPro-Italic.otf",
        "SourceSansPro-Light.otf",
        "SourceSansPro-LightItalic.otf",
        "SourceSansPro-Regular.otf",
        "SourceSansPro-Semibold.otf",
        "SourceSansPro-SemiboldItalic.otf",
    ]

    font_paths = [os.path.join(base_path, n) for n in font_names]

    test_fonts = [TTFont(x) for x in font_paths]

    # try fonts with consistent family names
    assert_PASS(check(test_fonts))

    # now set 5 of the fonts to have different family names
    for i in range(1, 6):
        if i in [1, 2, 3]:
            target_nameID = 1
        elif i in [4, 5]:
            target_nameID = 16
        name_records = test_fonts[i]["name"].names
        wrong_name = f"wrong-name-{9 % i}"
        for name_record in name_records:
            if name_record.nameID == target_nameID:
                name_record.string = wrong_name.encode("utf-16be")

    msg = assert_results_contain(check(test_fonts), FAIL, "inconsistent-family-name")
    assert "4 different Font Family names were found" in msg
    assert "'Source Sans Pro' was found" in msg
    assert "'wrong-name-1' was found" in msg


@check_id("opentype/postscript_name")
def test_check_name_postscript(check):
    # Test a font that has OK psname. Check should PASS.
    ttFont = TTFont(TEST_FILE("source-sans-pro/OTF/SourceSansPro-Bold.otf"))
    assert_PASS(check(ttFont))

    # Now change it to a string with illegal characters. Should FAIL.
    bad_ps_name = "(illegal) characters".encode("utf-16-be")
    ttFont["name"].setName(
        bad_ps_name,
        NameID.POSTSCRIPT_NAME,
        PlatformID.WINDOWS,
        WindowsEncodingID.UNICODE_BMP,
        WindowsLanguageID.ENGLISH_USA,
    )
    msg = assert_results_contain(check(ttFont), FAIL, "bad-psname-entries")
    assert "PostScript name does not follow requirements" in msg
    assert "May contain only a-zA-Z0-9 characters and a hyphen." in msg
