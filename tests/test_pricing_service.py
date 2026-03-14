import unittest

from src.models import CartItem
from src.pricing import PricingService, PricingError


class TestPricingService(unittest.TestCase):

    def setUp(self):
        self.ps = PricingService()

    # ── subtotal_cents ──

    def test_subtotal_un_item(self):
        items = [CartItem("ABC", 1000, 2)]
        self.assertEqual(self.ps.subtotal_cents(items), 2000)

    def test_subtotal_varios_items(self):
        items = [
            CartItem("A", 1000, 2),
            CartItem("B", 500, 3),
        ]
        self.assertEqual(self.ps.subtotal_cents(items), 3500)

    def test_subtotal_carrito_vacio(self):
        self.assertEqual(self.ps.subtotal_cents([]), 0)

    def test_subtotal_qty_cero_error(self):
        with self.assertRaises(PricingError):
            self.ps.subtotal_cents([CartItem("A", 1000, 0)])

    def test_subtotal_qty_negativa_error(self):
        with self.assertRaises(PricingError):
            self.ps.subtotal_cents([CartItem("A", 1000, -5)])

    def test_subtotal_precio_negativo_error(self):
        with self.assertRaises(PricingError):
            self.ps.subtotal_cents([CartItem("A", -100, 1)])

    # ── apply_coupon ──

    def test_coupon_none_no_descuento(self):
        self.assertEqual(self.ps.apply_coupon(10000, None), 10000)

    def test_coupon_vacio_no_descuento(self):
        self.assertEqual(self.ps.apply_coupon(10000, ""), 10000)

    def test_coupon_espacios_no_descuento(self):
        self.assertEqual(self.ps.apply_coupon(10000, "   "), 10000)

    def test_coupon_save10(self):
        # 10% de 10000 = 1000 de descuento
        self.assertEqual(self.ps.apply_coupon(10000, "SAVE10"), 9000)

    def test_coupon_save10_minusculas(self):
        self.assertEqual(self.ps.apply_coupon(10000, "save10"), 9000)

    def test_coupon_clp2000(self):
        self.assertEqual(self.ps.apply_coupon(10000, "CLP2000"), 8000)

    def test_coupon_clp2000_subtotal_bajo(self):
        # si el subtotal es menor al descuento, queda en 0
        self.assertEqual(self.ps.apply_coupon(1500, "CLP2000"), 0)

    def test_coupon_invalido_error(self):
        with self.assertRaises(PricingError):
            self.ps.apply_coupon(10000, "NOEXISTE")

    # ── tax_cents ──

    def test_tax_chile(self):
        self.assertEqual(self.ps.tax_cents(10000, "CL"), 1900)

    def test_tax_eu(self):
        self.assertEqual(self.ps.tax_cents(10000, "EU"), 2100)

    def test_tax_us(self):
        self.assertEqual(self.ps.tax_cents(10000, "US"), 0)

    def test_tax_pais_no_soportado(self):
        with self.assertRaises(PricingError):
            self.ps.tax_cents(10000, "JP")

    # ── shipping_cents ──

    def test_envio_cl_gratis_sobre_umbral(self):
        self.assertEqual(self.ps.shipping_cents(20000, "CL"), 0)

    def test_envio_cl_cobrado_bajo_umbral(self):
        self.assertEqual(self.ps.shipping_cents(19999, "CL"), 2500)

    def test_envio_us(self):
        self.assertEqual(self.ps.shipping_cents(10000, "US"), 5000)

    def test_envio_eu(self):
        self.assertEqual(self.ps.shipping_cents(10000, "EU"), 5000)

    def test_envio_pais_no_soportado(self):
        with self.assertRaises(PricingError):
            self.ps.shipping_cents(10000, "AR")

    # ── total_cents (integra todo) ──

    def test_total_sin_cupon_cl(self):
        items = [CartItem("X", 10000, 3)]
        # subtotal=30000, sin cupon, CL: tax 19%=5700, envio gratis
        self.assertEqual(self.ps.total_cents(items, None, "CL"), 35700)

    def test_total_con_cupon_us(self):
        items = [CartItem("X", 5000, 2)]
        # subtotal=10000, SAVE10 -> 9000, US: tax 0, envio 5000
        self.assertEqual(self.ps.total_cents(items, "SAVE10", "US"), 14000)
