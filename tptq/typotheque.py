# uv run fontbakery check-profile typotheque '/Users/rafalbuchner/TPTQ-work/repos/managers/specimens/fonts/presentations/Zed Display/Latin/ZedDisplaySuiteVF.ttf' --ghmarkdown report.md --full-lists


PROFILE = {
    "sections": {
        "My single check": ["vendor_ID_is_TPTQ"],
    },
    # "include_profiles": [
    #     "universal",
    # ],
    "check_definitions": ["tptq.checks.vendor_ID_is_TPTQ"],
}
