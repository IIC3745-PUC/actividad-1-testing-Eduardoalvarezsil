import unittest
from unittest.mock import Mock

from src.models import CartItem
from src.pricing import PricingService, PricingError
from src.checkout import CheckoutService, ChargeResult


class TestCheckoutService(unittest.TestCase):

    def setUp(self):
        self.mock_payments = Mock()
        self.mock_email = Mock()
        self.mock_fraud = Mock()
        self.mock_repo = Mock()
        self.mock_pricing = Mock(spec=PricingService)

        self.service = CheckoutService(
            payments=self.mock_payments,
            email=self.mock_email,
            fraud=self.mock_fraud,
            repo=self.mock_repo,
            pricing=self.mock_pricing,
        )

    def _setup_happy_path(self, amount=10000, fraud_score=10, charge_id="ch_123"):
        """Configura los mocks para un flujo exitoso."""
        self.mock_pricing.total_cents.return_value = amount
        self.mock_fraud.score.return_value = fraud_score
        self.mock_payments.charge.return_value = ChargeResult(
            ok=True, charge_id=charge_id
        )

    # ── Validacion de usuario ──

    def test_user_vacio(self):
        result = self.service.checkout("", [], "tok", "CL")
        self.assertEqual(result, "INVALID_USER")

    def test_user_solo_espacios(self):
        result = self.service.checkout("   ", [], "tok", "CL")
        self.assertEqual(result, "INVALID_USER")

    # ── Error de pricing ──

    def test_pricing_error_retorna_invalid_cart(self):
        self.mock_pricing.total_cents.side_effect = PricingError("qty must be > 0")
        result = self.service.checkout("user1", [CartItem("A", 100, -1)], "tok", "CL")
        self.assertTrue(result.startswith("INVALID_CART:"))
        self.assertIn("qty must be > 0", result)

    # ── Fraude ──

    def test_fraude_score_alto_rechaza(self):
        self.mock_pricing.total_cents.return_value = 50000
        self.mock_fraud.score.return_value = 80

        result = self.service.checkout("user1", [CartItem("A", 100, 1)], "tok", "CL")
        self.assertEqual(result, "REJECTED_FRAUD")

    def test_fraude_score_bajo_continua(self):
        self._setup_happy_path(fraud_score=79)
        result = self.service.checkout("user1", [CartItem("A", 100, 1)], "tok", "CL")
        self.assertTrue(result.startswith("OK:"))

    # ── Pago ──

    def test_pago_fallido(self):
        self.mock_pricing.total_cents.return_value = 10000
        self.mock_fraud.score.return_value = 20
        self.mock_payments.charge.return_value = ChargeResult(
            ok=False, reason="declined"
        )

        result = self.service.checkout("user1", [CartItem("A", 100, 1)], "tok", "CL")
        self.assertEqual(result, "PAYMENT_FAILED:declined")

    # ── Checkout exitoso ──

    def test_checkout_exitoso_guarda_orden_y_envia_recibo(self):
        self._setup_happy_path(amount=30000, charge_id="ch_abc")
        items = [CartItem("X", 10000, 3)]

        result = self.service.checkout(
            "user1", items, "tok_999", "CL", coupon_code="SAVE10"
        )
        self.assertTrue(result.startswith("OK:"))
        order_id = result.split(":")[1]

        # Se guardo la orden correctamente
        self.mock_repo.save.assert_called_once()
        orden = self.mock_repo.save.call_args[0][0]
        self.assertEqual(orden.user_id, "user1")
        self.assertEqual(orden.total_cents, 30000)
        self.assertEqual(orden.payment_charge_id, "ch_abc")
        self.assertEqual(orden.coupon_code, "SAVE10")
        self.assertEqual(orden.country, "CL")

        # Se envio el recibo por email
        self.mock_email.send_receipt.assert_called_once_with("user1", order_id, 30000)

    def test_charge_id_none_usa_unknown(self):
        self._setup_happy_path(charge_id=None)
        result = self.service.checkout("user1", [CartItem("A", 100, 1)], "tok", "CL")
        self.assertTrue(result.startswith("OK:"))

        orden = self.mock_repo.save.call_args[0][0]
        self.assertEqual(orden.payment_charge_id, "UNKNOWN")

    # ── PricingService por defecto ──

    def test_pricing_service_por_defecto(self):
        service = CheckoutService(
            payments=self.mock_payments,
            email=self.mock_email,
            fraud=self.mock_fraud,
            repo=self.mock_repo,
        )
        self.assertIsInstance(service.pricing, PricingService)
