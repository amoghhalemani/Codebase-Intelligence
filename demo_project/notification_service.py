"""Notification and email dispatch service."""

class NotificationService:
    def send_order_confirmation(self, email: str, order_id: str, amount: float) -> bool:
        message = f"Order {order_id} confirmed for total ${amount}"
        print(f"[EMAIL] To: {email} | {message}")
        return True

    def send_payment_failure_alert(self, email: str, error_reason: str) -> bool:
        print(f"[ALERT] To: {email} | Payment failed: {error_reason}")
        return False
