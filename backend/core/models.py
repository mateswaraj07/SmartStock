"""The 8 tables of SmartStock (see the ER diagram):
Master, ShopOwner, Supplier, Product, Bag, ReorderRequest, SupplierPayment, StockTransaction."""
from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.db.models import Sum

QTY = dict(max_digits=12, decimal_places=3)
MONEY = dict(max_digits=12, decimal_places=2)


class Master(models.Model):
    """Code table. Holds every list of allowed values: product category, unit,
    bag status, request status, payment method and stock transaction type."""
    master_type = models.CharField(max_length=30, db_index=True)
    master_code = models.CharField(max_length=30)
    master_value = models.CharField(max_length=80)

    class Meta:
        unique_together = ("master_type", "master_code")

    def __str__(self):
        return f"{self.master_type}: {self.master_value}"


class ShopOwner(models.Model):
    """The shop owner. The shop details are attributes of the owner (no separate Shop table)."""
    owner_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    password = models.CharField(max_length=128)  # stored as a hash
    shop_name = models.CharField(max_length=120)
    shop_address = models.CharField(max_length=255)
    city = models.CharField(max_length=60, blank=True)


class Supplier(models.Model):
    company_name = models.CharField(max_length=120)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=128)  # stored as a hash


class Product(models.Model):
    owner = models.ForeignKey(ShopOwner, on_delete=models.CASCADE, related_name="products")      # SELLS
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")  # SUPPLIES
    category = models.ForeignKey(Master, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")          # CATEGORISES
    product_name = models.CharField(max_length=120)
    selling_price = models.DecimalField(**MONEY)
    cost_price = models.DecimalField(**MONEY, default=0)     # rate paid to the supplier
    unit = models.CharField(max_length=10, default="KG")      # value from Master (UNIT)
    min_stock = models.DecimalField(**QTY, default=0)
    reorder_qty = models.DecimalField(**QTY, default=0)
    is_active = models.BooleanField(default=True)             # deactivate, never delete (keeps history)

    class Meta:
        unique_together = ("owner", "product_name")


class Bag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="bags")                # STORED_IN
    bag_code = models.CharField(max_length=20)                # e.g. SUG-001
    initial_qty = models.DecimalField(**QTY)
    current_qty = models.DecimalField(**QTY)
    status = models.CharField(max_length=10, default="AVAILABLE", db_index=True)  # Master (BAG_STATUS)

    class Meta:
        unique_together = ("product", "bag_code")


class ReorderRequest(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="requests")            # RESTOCKED_BY
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, default="PENDING", db_index=True)  # Master (REQUEST_STATUS)
    requested_qty = models.DecimalField(**QTY)
    supplied_qty = models.DecimalField(**QTY, null=True, blank=True)   # what the supplier says it delivered
    received_qty = models.DecimalField(**QTY, null=True, blank=True)   # what the owner actually received
    unit_rate = models.DecimalField(**MONEY, default=0)                # rate quoted by the supplier

    @property
    def request_no(self):
        return f"REQ-{self.id:03d}"

    @property
    def bill_amount(self):  # derived: received quantity x rate
        return ((self.received_qty or Decimal(0)) * self.unit_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)

    @property
    def amount_paid(self):  # derived: sum of its payments
        return self.payments.aggregate(s=Sum("amount_paid"))["s"] or Decimal("0.00")

    @property
    def due_amount(self):
        return self.bill_amount - self.amount_paid

    @property
    def payment_status(self):  # derived
        if self.status != "RECEIVED" or self.bill_amount <= 0:
            return "NOT_BILLED"
        paid = self.amount_paid
        return "PAID" if paid >= self.bill_amount else ("PARTIAL" if paid > 0 else "UNPAID")


class SupplierPayment(models.Model):
    request = models.ForeignKey(ReorderRequest, on_delete=models.PROTECT, related_name="payments")     # PAID_BY
    payment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    payment_method = models.CharField(max_length=15)          # Master (PAYMENT_METHOD)
    amount_paid = models.DecimalField(**MONEY)
    reference_no = models.CharField(max_length=60, blank=True)
    balance_remaining = models.DecimalField(**MONEY)          # bill still unpaid after this payment
    supplier_confirmed = models.BooleanField(default=False)   # supplier acknowledges the money

    class Meta:
        ordering = ["-id"]

    @property
    def payment_no(self):
        return f"PAY-{self.id:03d}"


class StockTransaction(models.Model):
    """Ledger of every stock change. Rows are never edited or deleted."""
    bag = models.ForeignKey(Bag, on_delete=models.PROTECT, related_name="transactions")                # LOGGED_IN
    txn_date = models.DateTimeField(auto_now_add=True, db_index=True)
    txn_type = models.CharField(max_length=20, db_index=True)  # Master (TXN_TYPE)
    quantity = models.DecimalField(**QTY)                      # + added, - removed
    qty_before = models.DecimalField(**QTY)                    # product stock before
    qty_after = models.DecimalField(**QTY)                     # product stock after
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-id"]
