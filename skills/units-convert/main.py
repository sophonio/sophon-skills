"""Offline unit conversion.

Runs fully local in the alpine Python sandbox: no network, no credentials, no third-party
packages. `params` is injected as a global by the Sophon runtime and carries the tool name and
the tool's call arguments.

Every conversion is pure arithmetic. Each dimension has a base unit and a table mapping each unit
to a multiplicative factor relative to that base (value_in_base = value * factor). Temperature is
special-cased because its conversions have offsets, not just scale factors.
"""

import json

tool_name = params.get("tool", "")

PI = 3.141592653589793

# --- Conversion tables --------------------------------------------------------
# dimension -> { "base": <symbol>, "units": { <symbol>: factor_to_base } }
DIMENSIONS = {
    "length": {  # base: meter
        "base": "m",
        "units": {
            "m": 1.0,
            "km": 1000.0,
            "cm": 0.01,
            "mm": 0.001,
            "mi": 1609.344,
            "yd": 0.9144,
            "ft": 0.3048,
            "in": 0.0254,
            "nmi": 1852.0,
        },
    },
    "mass": {  # base: kilogram
        "base": "kg",
        "units": {
            "kg": 1.0,
            "g": 0.001,
            "mg": 0.000001,
            "lb": 0.45359237,
            "oz": 0.028349523125,
            "st": 6.35029318,
            "t": 1000.0,
        },
    },
    "volume": {  # base: liter
        "base": "l",
        "units": {
            "l": 1.0,
            "ml": 0.001,
            "m3": 1000.0,
            "gal": 3.785411784,      # US gallon
            "qt": 0.946352946,       # US quart
            "pt": 0.473176473,       # US pint
            "cup": 0.2365882365,     # US customary cup
            "floz": 0.0295735295625, # US fluid ounce
        },
    },
    "area": {  # base: square meter
        "base": "m2",
        "units": {
            "m2": 1.0,
            "km2": 1000000.0,
            "cm2": 0.0001,
            "ft2": 0.09290304,
            "in2": 0.00064516,
            "ac": 4046.8564224,      # international acre
            "ha": 10000.0,
        },
    },
    "speed": {  # base: meter per second
        "base": "mps",
        "units": {
            "mps": 1.0,
            "kmh": 1.0 / 3.6,
            "mph": 0.44704,
            "kn": 1852.0 / 3600.0,   # knot
            "fps": 0.3048,
        },
    },
    "time": {  # base: second
        "base": "s",
        "units": {
            "s": 1.0,
            "min": 60.0,
            "h": 3600.0,
            "day": 86400.0,
            "week": 604800.0,
        },
    },
    "data": {  # base: byte
        "base": "B",
        "units": {
            "b": 0.125,              # bit
            "B": 1.0,                # byte
            "KB": 1000.0,
            "MB": 1000000.0,
            "GB": 1000000000.0,
            "TB": 1000000000000.0,
            "KiB": 1024.0,
            "MiB": 1048576.0,
            "GiB": 1073741824.0,
            "TiB": 1099511627776.0,
        },
    },
    "pressure": {  # base: pascal
        "base": "pa",
        "units": {
            "pa": 1.0,
            "kpa": 1000.0,
            "bar": 100000.0,
            "psi": 6894.757293168,
            "atm": 101325.0,
        },
    },
    "energy": {  # base: joule
        "base": "j",
        "units": {
            "j": 1.0,
            "kj": 1000.0,
            "cal": 4.184,
            "kcal": 4184.0,
            "wh": 3600.0,
            "kwh": 3600000.0,
        },
    },
    "angle": {  # base: radian
        "base": "rad",
        "units": {
            "rad": 1.0,
            "deg": PI / 180.0,
            "grad": PI / 200.0,
        },
    },
}

TEMPERATURE_UNITS = ["C", "F", "K"]

# --- Alias tables -------------------------------------------------------------
# alias (as typed) -> canonical symbol used in the tables above.
ALIAS_PAIRS = [
    # length
    ("m", "m"), ("meter", "m"), ("meters", "m"), ("metre", "m"), ("metres", "m"),
    ("km", "km"), ("kilometer", "km"), ("kilometers", "km"), ("kilometre", "km"), ("kilometres", "km"),
    ("cm", "cm"), ("centimeter", "cm"), ("centimeters", "cm"), ("centimetre", "cm"), ("centimetres", "cm"),
    ("mm", "mm"), ("millimeter", "mm"), ("millimeters", "mm"), ("millimetre", "mm"), ("millimetres", "mm"),
    ("mi", "mi"), ("mile", "mi"), ("miles", "mi"),
    ("yd", "yd"), ("yard", "yd"), ("yards", "yd"),
    ("ft", "ft"), ("foot", "ft"), ("feet", "ft"),
    ("in", "in"), ("inch", "in"), ("inches", "in"),
    ("nmi", "nmi"), ("nauticalmile", "nmi"), ("nauticalmiles", "nmi"),
    # mass
    ("kg", "kg"), ("kilogram", "kg"), ("kilograms", "kg"), ("kilo", "kg"), ("kilos", "kg"),
    ("g", "g"), ("gram", "g"), ("grams", "g"), ("gramme", "g"), ("grammes", "g"),
    ("mg", "mg"), ("milligram", "mg"), ("milligrams", "mg"),
    ("lb", "lb"), ("lbs", "lb"), ("pound", "lb"), ("pounds", "lb"),
    ("oz", "oz"), ("ounce", "oz"), ("ounces", "oz"),
    ("st", "st"), ("stone", "st"), ("stones", "st"),
    ("t", "t"), ("tonne", "t"), ("tonnes", "t"), ("ton", "t"), ("tons", "t"), ("metricton", "t"),
    # volume
    ("l", "l"), ("liter", "l"), ("liters", "l"), ("litre", "l"), ("litres", "l"),
    ("ml", "ml"), ("milliliter", "ml"), ("milliliters", "ml"), ("millilitre", "ml"), ("millilitres", "ml"),
    ("m3", "m3"), ("m^3", "m3"), ("cubicmeter", "m3"), ("cubicmeters", "m3"), ("cubicmetre", "m3"),
    ("gal", "gal"), ("gallon", "gal"), ("gallons", "gal"),
    ("qt", "qt"), ("quart", "qt"), ("quarts", "qt"),
    ("pt", "pt"), ("pint", "pt"), ("pints", "pt"),
    ("cup", "cup"), ("cups", "cup"),
    ("floz", "floz"), ("fluidounce", "floz"), ("fluidounces", "floz"), ("fl-oz", "floz"),
    # area
    ("m2", "m2"), ("m^2", "m2"), ("sqm", "m2"), ("squaremeter", "m2"), ("squaremeters", "m2"),
    ("km2", "km2"), ("km^2", "km2"), ("sqkm", "km2"),
    ("cm2", "cm2"), ("cm^2", "cm2"), ("sqcm", "cm2"),
    ("ft2", "ft2"), ("ft^2", "ft2"), ("sqft", "ft2"), ("squarefoot", "ft2"), ("squarefeet", "ft2"),
    ("in2", "in2"), ("in^2", "in2"), ("sqin", "in2"),
    ("ac", "ac"), ("acre", "ac"), ("acres", "ac"),
    ("ha", "ha"), ("hectare", "ha"), ("hectares", "ha"),
    # speed
    ("mps", "mps"), ("m/s", "mps"), ("meterspersecond", "mps"),
    ("kmh", "kmh"), ("km/h", "kmh"), ("kph", "kmh"), ("kmph", "kmh"),
    ("mph", "mph"), ("mi/h", "mph"), ("milesperhour", "mph"),
    ("kn", "kn"), ("knot", "kn"), ("knots", "kn"), ("kt", "kn"), ("kts", "kn"),
    ("fps", "fps"), ("ft/s", "fps"), ("feetpersecond", "fps"),
    # time
    ("s", "s"), ("sec", "s"), ("secs", "s"), ("second", "s"), ("seconds", "s"),
    ("min", "min"), ("mins", "min"), ("minute", "min"), ("minutes", "min"),
    ("h", "h"), ("hr", "h"), ("hrs", "h"), ("hour", "h"), ("hours", "h"),
    ("day", "day"), ("days", "day"), ("d", "day"),
    ("week", "week"), ("weeks", "week"), ("wk", "week"), ("wks", "week"),
    # data
    ("b", "b"), ("bit", "b"), ("bits", "b"),
    ("B", "B"), ("byte", "B"), ("bytes", "B"),
    ("KB", "KB"), ("kilobyte", "KB"), ("kilobytes", "KB"),
    ("MB", "MB"), ("megabyte", "MB"), ("megabytes", "MB"),
    ("GB", "GB"), ("gigabyte", "GB"), ("gigabytes", "GB"),
    ("TB", "TB"), ("terabyte", "TB"), ("terabytes", "TB"),
    ("KiB", "KiB"), ("kibibyte", "KiB"), ("kibibytes", "KiB"),
    ("MiB", "MiB"), ("mebibyte", "MiB"), ("mebibytes", "MiB"),
    ("GiB", "GiB"), ("gibibyte", "GiB"), ("gibibytes", "GiB"),
    ("TiB", "TiB"), ("tebibyte", "TiB"), ("tebibytes", "TiB"),
    # pressure
    ("pa", "pa"), ("pascal", "pa"), ("pascals", "pa"),
    ("kpa", "kpa"), ("kilopascal", "kpa"), ("kilopascals", "kpa"),
    ("bar", "bar"), ("bars", "bar"),
    ("psi", "psi"),
    ("atm", "atm"), ("atmosphere", "atm"), ("atmospheres", "atm"),
    # energy
    ("j", "j"), ("joule", "j"), ("joules", "j"),
    ("kj", "kj"), ("kilojoule", "kj"), ("kilojoules", "kj"),
    ("cal", "cal"), ("calorie", "cal"), ("calories", "cal"),
    ("kcal", "kcal"), ("kilocalorie", "kcal"), ("kilocalories", "kcal"),
    ("wh", "wh"), ("watthour", "wh"), ("watthours", "wh"),
    ("kwh", "kwh"), ("kilowatthour", "kwh"), ("kilowatthours", "kwh"),
    # angle
    ("rad", "rad"), ("radian", "rad"), ("radians", "rad"),
    ("deg", "deg"), ("degree", "deg"), ("degrees", "deg"),
    ("grad", "grad"), ("gradian", "grad"), ("gradians", "grad"), ("gon", "grad"),
    # temperature
    ("C", "C"), ("celsius", "C"), ("centigrade", "C"),
    ("F", "F"), ("fahrenheit", "F"),
    ("K", "K"), ("kelvin", "K"),
]

# Map a canonical symbol to its dimension (temperature included).
SYMBOL_TO_DIM = {}
for _dim, _spec in DIMENSIONS.items():
    for _sym in _spec["units"]:
        SYMBOL_TO_DIM[_sym] = _dim
for _sym in TEMPERATURE_UNITS:
    SYMBOL_TO_DIM[_sym] = "temperature"

# Exact-case alias map (needed to distinguish e.g. bit "b" from byte "B").
ALIASES_EXACT = {}
for _alias, _canon in ALIAS_PAIRS:
    ALIASES_EXACT[_alias] = _canon

# Case-insensitive alias map, skipping any lowercased key that is ambiguous
# (maps to more than one canonical symbol, e.g. "b" -> b/B).
_lower_seen = {}
for _alias, _canon in ALIAS_PAIRS:
    _low = _alias.lower()
    if _low in _lower_seen and _lower_seen[_low] != _canon:
        _lower_seen[_low] = None  # mark ambiguous
    elif _low not in _lower_seen:
        _lower_seen[_low] = _canon
ALIASES_LOWER = {k: v for k, v in _lower_seen.items() if v is not None}


def resolve_symbol(unit):
    """Return the canonical symbol for a user-supplied unit string, or None."""
    if not isinstance(unit, str):
        return None
    u = unit.strip()
    if u == "":
        return None
    if u in ALIASES_EXACT:
        return ALIASES_EXACT[u]
    low = u.lower()
    if low in ALIASES_LOWER:
        return ALIASES_LOWER[low]
    return None


def to_number(value):
    if isinstance(value, bool):
        raise ValueError("'value' must be a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            raise ValueError(f"'value' is not a number: {value!r}")
    raise ValueError("'value' must be a number")


def clean(x):
    """Round away tiny floating-point noise while preserving magnitude."""
    r = round(x, 12)
    # Present whole numbers as ints for readability.
    if r == int(r) and abs(r) < 1e15:
        return int(r)
    return r


# --- Temperature --------------------------------------------------------------

def temp_to_celsius(value, unit):
    if unit == "C":
        return value
    if unit == "F":
        return (value - 32.0) * 5.0 / 9.0
    if unit == "K":
        return value - 273.15
    raise ValueError(f"unknown temperature unit: {unit}")


def celsius_to_temp(celsius, unit):
    if unit == "C":
        return celsius
    if unit == "F":
        return celsius * 9.0 / 5.0 + 32.0
    if unit == "K":
        return celsius + 273.15
    raise ValueError(f"unknown temperature unit: {unit}")


# --- Tool handlers ------------------------------------------------------------

def convert():
    raw_from = params.get("from")
    raw_to = params.get("to")
    if not isinstance(raw_from, str) or raw_from.strip() == "":
        raise ValueError("missing 'from' unit")
    if not isinstance(raw_to, str) or raw_to.strip() == "":
        raise ValueError("missing 'to' unit")
    if "value" not in params:
        raise ValueError("missing 'value'")

    value = to_number(params.get("value"))

    from_sym = resolve_symbol(raw_from)
    to_sym = resolve_symbol(raw_to)
    if from_sym is None:
        raise ValueError(f"unknown unit: {raw_from}")
    if to_sym is None:
        raise ValueError(f"unknown unit: {raw_to}")

    from_dim = SYMBOL_TO_DIM[from_sym]
    to_dim = SYMBOL_TO_DIM[to_sym]

    if from_dim != to_dim:
        print(json.dumps({"error": f"incompatible units: {raw_from} and {raw_to}"}))
        return

    if from_dim == "temperature":
        celsius = temp_to_celsius(value, from_sym)
        result = celsius_to_temp(celsius, to_sym)
    else:
        units = DIMENSIONS[from_dim]["units"]
        base_value = value * units[from_sym]
        result = base_value / units[to_sym]

    print(json.dumps({
        "value": clean(value),
        "from": from_sym,
        "to": to_sym,
        "dimension": from_dim,
        "result": clean(result),
    }))


def list_units():
    category = params.get("category")
    if category not in (None, ""):
        cat = str(category).strip().lower()
        if cat == "temperature":
            print(json.dumps({"category": "temperature", "units": list(TEMPERATURE_UNITS)}))
            return
        if cat not in DIMENSIONS:
            valid = sorted(list(DIMENSIONS.keys()) + ["temperature"])
            raise ValueError(f"unknown category: {category}. Valid categories: {', '.join(valid)}")
        print(json.dumps({
            "category": cat,
            "base": DIMENSIONS[cat]["base"],
            "units": list(DIMENSIONS[cat]["units"].keys()),
        }))
        return

    grouped = {}
    for dim, spec in DIMENSIONS.items():
        grouped[dim] = list(spec["units"].keys())
    grouped["temperature"] = list(TEMPERATURE_UNITS)
    print(json.dumps({"dimensions": grouped}))


HANDLERS = {
    "units.convert": convert,
    "units.list_units": list_units,
}

try:
    handler = HANDLERS.get(tool_name)
    if handler is None:
        print(json.dumps({"error": f"Unknown tool: {tool_name}"}))
    else:
        handler()
except ValueError as e:
    print(json.dumps({"error": str(e)}))
except Exception as e:  # noqa: BLE001
    print(json.dumps({"error": f"Unexpected error: {type(e).__name__}: {e}"}))
