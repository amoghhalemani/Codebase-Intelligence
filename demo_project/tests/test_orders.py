import sys
from pathlib import Path

_DIR = Path(__file__).resolve().parent.parent
if str(_DIR) not in sys.path:
    sys.path.insert(0, str(_DIR))

from order_service import OrderManager
from tax_calculator import calculate_vat


def test_order_checkout_success():
    manager = OrderManager()
    result = manager.checkout("ORD-101", "customer@example.com", 100.0)
    assert result["status"] == "COMPLETED"
    assert result["payment"]["total_charged"] > 0


def test_calculate_vat_standard_rate():
    vat = calculate_vat(100.0, 0.20)
    assert vat == 20.0
