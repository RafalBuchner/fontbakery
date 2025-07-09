from fontbakery.prelude import check, Message, PASS, FAIL
from fontbakery.status import Status
from fontTools.ttLib import TTFont
from typing import Generator


@check(
    id="vendor_ID_is_TPTQ",
    rationale="check vendor id",
    severity=FAIL,
    description="checks if vendor id in os2 table is equal to TPTQ",
)
def vendor_ID_is_TPTQ(
    ttFont: TTFont,
) -> Generator[tuple[Status, Message], None, None]:
    os2 = ttFont.get("OS/2")
    if not os2:
        yield FAIL, Message("missing-os2", "Required OS/2 table is missing")

    vendor_id = os2.achVendID.strip()  # type: ignore
    if vendor_id == "TPTQ":
        yield PASS, Message("valid-vendor-id", f"Vendor ID is correctly set to 'TPTQ'")
    else:
        yield FAIL, Message(
            "wrong-vendor-id", f"Vendor ID is '{vendor_id}', but should be 'TPTQ'"
        )
