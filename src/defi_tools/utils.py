def format_digits(value, n_digits=2) -> str:
    """2.1 -> 2.10 | 2 -> 2.00"""
    n_digits = n_digits or 0
    value = float(value)
    return f"{value:.{n_digits}f}"
    a, *b = value.split(".")
    b = b[0] if b else 0
    b = b.ljust(n_digits, "0")
    return f"{a}.{b}"


def format_to_percent(number: float, n_digits=2, symbol=True):
    """0.0123 -> 1.23%"""
    number = float(number)
    if not number:
        return "-"
    value = number * 100
    value = format_digits(value, n_digits=n_digits)
    symbol = "%" if symbol else ""
    return f"{value}{symbol}"


def reverse_from_percent(string: str):
    """1.23% -> 0.0123"""
    string = string.replace("%", "")
    value = float(string) / 100
    return value


def convert_text_to_digit(string: str):
    """12.345m -> 12345000"""
    multps = {
        "k": 1000,
        "m": 1000000,
        "b": 1000000000,
    }
    digits = "".join([x for x in string if x.isdigit() or x == "."])
    suffix = "".join([x for x in string if x.isalpha()])
    value = float(digits) * multps.get(suffix, 1)
    return value


def compare_values(now, ini, n_digits=2, formatted=False, colored=True):
    now, ini = float(now), float(ini)
    diff = now - ini
    # diff = round(diff, n_digits)
    if formatted:
        color = "[white]"
        plus = ""
        if diff < 0:
            color = "[red]"
        if diff > 0:
            color = "[green]"
            plus = "+"
        diff = format_digits(diff, n_digits=n_digits) if diff else 0
        color = color if colored else ""
        diff = f"{color}({plus}{diff})"
    return diff
