from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.01")
DEFAULT_VAT_RATE = Decimal("0.10")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_line_total(unit_price: Decimal, quantity: Decimal) -> Decimal:
    return quantize_money(unit_price * quantity)


def calculate_totals(line_totals: list[Decimal], vat_rate: Decimal = DEFAULT_VAT_RATE) -> tuple[Decimal, Decimal, Decimal]:
    subtotal = quantize_money(sum(line_totals, Decimal("0")))
    vat_amount = quantize_money(subtotal * vat_rate)
    total_amount = quantize_money(subtotal + vat_amount)
    return subtotal, vat_amount, total_amount