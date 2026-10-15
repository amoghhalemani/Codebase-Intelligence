"""Tax calculation service for e-commerce transactions."""

def calculate_vat(subtotal: float, rate: float = 0.20) -> float:
    """Calculates VAT amount based on subtotal and percentage rate."""
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative")
    return round(subtotal * rate, 2)


def apply_discount(subtotal: float, discount_percent: float) -> float:
    """Applies coupon discount to subtotal."""
    discount = subtotal * (discount_percent / 100.0)
    return max(0.0, subtotal - discount)


def calculate_luxury_tax(price: float) -> float:
    """[DEAD CODE] Abandoned experimental luxury surcharge. 0 callers."""
    if price > 1000.0:
        return price * 0.15
    return 0.0


def convert_to_bitcoin_rate(amount_usd: float) -> float:
    """[DEAD CODE] Deprecated cryptocurrency conversion rate. 0 callers."""
    return amount_usd / 65000.0
