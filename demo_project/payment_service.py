"""Payment processing service coordinating transaction totals."""

from tax_calculator import calculate_vat, apply_discount


class PaymentProcessor:
    def __init__(self, currency: str = "USD"):
        self.currency = currency

    def process_payment(self, user_id: str, amount: float, discount_code: float = 0.0) -> dict:
        discounted = apply_discount(amount, discount_code)
        tax = calculate_vat(discounted)
        total = round(discounted + tax, 2)
        return {
            "user_id": user_id,
            "subtotal": discounted,
            "tax": tax,
            "total_charged": total,
            "status": "APPROVED",
        }

    def refund_transaction(self, transaction_id: str, amount: float) -> dict:
        """[DEAD CODE] Unfinished refund endpoint. 0 callers across the repository."""
        return {
            "transaction_id": transaction_id,
            "refunded_amount": amount,
            "status": "REFUNDED",
        }
