import os
import json


def calculate_tax(amount: float) -> float:
    return amount * 0.18


def format_invoice(amount: float) -> str:
    tax = calculate_tax(amount)
    return json.dumps({"amount": amount, "tax": tax})


class InvoiceService:
    def create_invoice(self, amount: float) -> str:
        return format_invoice(amount)


def unused_helper():
    return os.getcwd()
