"""Core order management workflow orchestrating checkout, payment, and notifications."""

from payment_service import PaymentProcessor
from notification_service import NotificationService


class OrderManager:
    def __init__(self):
        self.payment_processor = PaymentProcessor()
        self.notifier = NotificationService()

    def checkout(self, order_id: str, customer_email: str, raw_amount: float) -> dict:
        """Executes full checkout: charges card and notifies user."""
        payment_result = self.payment_processor.process_payment(
            user_id=customer_email,
            amount=raw_amount,
            discount_code=10.0,
        )

        self.notifier.send_order_confirmation(
            email=customer_email,
            order_id=order_id,
            amount=payment_result["total_charged"],
        )

        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "payment": payment_result,
        }
