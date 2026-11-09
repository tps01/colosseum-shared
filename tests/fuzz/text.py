"""Bounded text-parser properties; runnable without Atheris for seed replay."""

from __future__ import annotations

import math
import sys


def check_input(data: bytes) -> None:
    from colosseum_shared.parsing.text import (
        parse_float,
        parse_float_list,
        parse_key_value_lines,
        strip_response,
    )

    data = data[:512]
    text = data.decode("utf-8", errors="replace")
    assert strip_response(text) == text.strip()
    expected = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            expected[key.strip()] = value.strip()
    assert parse_key_value_lines(text) == expected

    # An independent float conversion oracle checks both success and rejection.
    separator = (",", ";", "|", "")[data[0] % 4] if data else ","
    try:
        expected_values = list(map(float, filter(None, map(str.strip, text.split(separator)))))
    except ValueError:
        try:
            parse_float_list(text, sep=separator)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid float list accepted")
    else:
        actual = parse_float_list(text, sep=separator)
        assert len(actual) == len(expected_values)
        assert all(
            a == b or (math.isnan(a) and math.isnan(b)) for a, b in zip(actual, expected_values)
        )

    # Construct valid numeric tokens, with prose that cannot contain a number.
    flags = data[0] if data else 0
    magnitude = int.from_bytes(data[1:5], "little")
    exponent = int.from_bytes(data[5:7], "little") % 801 - 400
    mantissa = (str(magnitude), f"{magnitude}.", f".{magnitude}", f"{magnitude}.{magnitude}")[
        flags % 4
    ]
    token = ("-" if flags & 4 else "+") + mantissa
    if flags & 8:
        token += ("E" if flags & 16 else "e") + str(exponent)
    assert parse_float("reading: " + token + " V; ignored 999") == float(token)
    try:
        parse_float("no numeric value")
    except ValueError:
        pass
    else:
        raise AssertionError("Missing number accepted")


def main() -> None:
    import atheris

    with atheris.instrument_imports(include=["colosseum_shared"]):
        import colosseum_shared.parsing.text  # noqa: F401
    atheris.Setup(sys.argv, atheris.instrument_func(check_input))
    atheris.Fuzz()


if __name__ == "__main__":
    main()
