"""Business rules: stock bags, low stock, supplier reorder, receipt, bill and payment.
Every important operation runs inside a database transaction."""
import re
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import Bag, Master, Product, ReorderRequest, StockTransaction, SupplierPayment

OPEN = ["PENDING", "ACCEPTED", "DISPATCHED", "DELIVERED"]  # a request is "open" until it is received or rejected


def D(v):
    try:
        return Decimal(str(v))
    except Exception:
        raise ValidationError("Enter a valid number.")


def check_master(mtype, code, field="value"):
    """A value such as a status or payment method must exist in the Master table."""
    if not Master.objects.filter(master_type=mtype, master_code=code).exists():
        raise ValidationError({field: f"'{code}' is not a valid {mtype.replace('_', ' ').lower()}."})


# ------------------------------------------------------------------ stock
def total_stock(product):  # derived: sum of the bags that are not empty
    return Bag.objects.filter(product=product).exclude(status="EMPTY").aggregate(s=Sum("current_qty"))["s"] or Decimal(0)


def stock_level(product, total=None):
    total = total_stock(product) if total is None else total
    if total <= product.min_stock / 2:
        return "CRITICAL"
    return "LOW" if total <= product.min_stock else "OK"


def _log(bag, txn_type, qty, before, after, remarks=""):
    return StockTransaction.objects.create(bag=bag, txn_type=txn_type, quantity=qty, qty_before=before,
                                           qty_after=after, remarks=remarks)


def next_bag_code(product):
    prefix = (re.sub("[^A-Z]", "", product.product_name.upper())[:3]).ljust(3, "X")
    n = product.bags.count() + 1
    while product.bags.filter(bag_code=f"{prefix}-{n:03d}").exists():
        n += 1
    return f"{prefix}-{n:03d}"


def activate_next_bag(product):
    """If no bag is ACTIVE, the oldest AVAILABLE bag becomes ACTIVE automatically."""
    if product.bags.filter(status="ACTIVE").exists():
        return
    nxt = product.bags.select_for_update().filter(status="AVAILABLE").order_by("id").first()
    if nxt:
        nxt.status = "ACTIVE"
        nxt.save()
        t = total_stock(product)
        _log(nxt, "BAG_ACTIVATED", 0, t, t, f"{nxt.bag_code} activated")


@transaction.atomic
def add_bag(product, qty, txn_type, remarks=""):
    qty = D(qty)
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    product = Product.objects.select_for_update().get(pk=product.pk)
    before = total_stock(product)
    first = not product.bags.filter(status="ACTIVE").exists()
    bag = Bag.objects.create(product=product, bag_code=next_bag_code(product), initial_qty=qty, current_qty=qty,
                             status="ACTIVE" if first else "AVAILABLE")
    _log(bag, txn_type, qty, before, before + qty, remarks or bag.bag_code)
    if first:
        _log(bag, "BAG_ACTIVATED", 0, before + qty, before + qty, f"{bag.bag_code} activated")
    return bag


@transaction.atomic
def deduct_stock(product, qty, remarks):
    """Takes stock from the ACTIVE bag first. An empty bag becomes EMPTY and the next bag activates."""
    qty = D(qty)
    product = Product.objects.select_for_update().get(pk=product.pk)
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    if total_stock(product) < qty:
        raise ValidationError(f"Stock cannot become negative. Available: {total_stock(product)} {product.unit}.")
    remaining = qty
    while remaining > 0:
        activate_next_bag(product)
        bag = product.bags.select_for_update().filter(status="ACTIVE").first()
        if bag is None:
            raise ValidationError("No active bag found.")
        take = min(bag.current_qty, remaining)
        before = total_stock(product)
        bag.current_qty -= take
        remaining -= take
        if bag.current_qty <= 0:
            bag.status = "EMPTY"
        bag.save()
        _log(bag, "STOCK_ADJUSTMENT", -take, before, before - take, remarks)
        if bag.status == "EMPTY":
            _log(bag, "BAG_EMPTY", 0, before - take, before - take, f"{bag.bag_code} is empty")
    activate_next_bag(product)
    check_low_stock(product)


@transaction.atomic
def adjust_stock(product, qty, reason, remarks):
    """Correction of stock (damage, wastage, expired, count difference...). A reason is compulsory."""
    qty = D(qty)
    if qty == 0:
        raise ValidationError("Quantity cannot be zero.")
    if not (remarks or "").strip():
        raise ValidationError("A reason is required for every stock adjustment.")
    note = f"{reason}: {remarks}"[:255]
    if qty < 0:
        deduct_stock(product, -qty, note)
    else:
        add_bag(product, qty, "STOCK_ADJUSTMENT", note)
        check_low_stock(product)


# ------------------------------------------------------------------ reorder
def check_low_stock(product):
    """Low stock creates a reorder request for the product's supplier (no duplicate open requests)."""
    if not product.is_active or stock_level(product) == "OK":
        return
    if product.supplier and product.reorder_qty > 0 and not product.requests.filter(status__in=OPEN).exists():
        create_reorder(product, product.reorder_qty)


def create_reorder(product, qty):
    if product.requests.filter(status__in=OPEN).exists():
        raise ValidationError("An open reorder request already exists for this product.")
    if not product.supplier:
        raise ValidationError("Assign a supplier to this product first.")
    qty = D(qty)
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return ReorderRequest.objects.create(product=product, requested_qty=qty, unit_rate=product.cost_price)


@transaction.atomic
def supplier_action(req, action, supplied_qty=None, unit_rate=None):
    flow = {"accept": ("PENDING", "ACCEPTED"), "reject": ("PENDING", "REJECTED"),
            "dispatch": ("ACCEPTED", "DISPATCHED"), "deliver": ("DISPATCHED", "DELIVERED")}
    if action not in flow:
        raise ValidationError("Unknown action.")
    need, new = flow[action]
    if req.status != need:
        raise ValidationError(f"The request must be {need} to {action} it.")
    if action == "accept" and unit_rate not in (None, ""):
        rate = D(unit_rate)
        if rate < 0:
            raise ValidationError("Rate cannot be negative.")
        req.unit_rate = rate  # the supplier quotes its rate
    if action == "deliver":
        qty = D(supplied_qty)
        if qty <= 0:
            raise ValidationError("Enter the supplied quantity.")
        req.supplied_qty = qty
    req.status = new
    req.save()  # NOTE: the shop's stock is NOT changed here; only the owner can do that


@transaction.atomic
def receive_request(req, qty):
    """The owner enters the quantity actually received: stock increases and the bill is created."""
    req = ReorderRequest.objects.select_for_update().get(pk=req.pk)
    if req.status != "DELIVERED":
        raise ValidationError("Only delivered requests can be confirmed as received.")
    qty = D(qty)
    add_bag(req.product, qty, "STOCK_RECEIVED", req.request_no)
    req.status, req.received_qty = "RECEIVED", qty
    req.save()


# ------------------------------------------------------------------ payment
@transaction.atomic
def pay_supplier(req, amount, method, reference=""):
    """The owner pays all or part of the supplier bill. balance_remaining is saved on every payment."""
    req = ReorderRequest.objects.select_for_update().get(pk=req.pk)
    if req.status != "RECEIVED" or req.bill_amount <= 0:
        raise ValidationError("Only received requests that have a bill can be paid.")
    amount = D(amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if amount <= 0:
        raise ValidationError("Enter an amount greater than zero.")
    due = req.due_amount
    if amount > due:
        raise ValidationError(f"The amount is more than the balance due (Rs. {due}).")
    check_master("PAYMENT_METHOD", method, "payment_method")
    if method != "CASH" and not (reference or "").strip():
        raise ValidationError("Enter the UPI / bank / cheque reference number.")
    return SupplierPayment.objects.create(request=req, payment_method=method, amount_paid=amount,
                                          reference_no=reference or "", balance_remaining=due - amount)


@transaction.atomic
def confirm_payment(pay):
    if pay.supplier_confirmed:
        raise ValidationError("This payment is already confirmed.")
    pay.supplier_confirmed = True
    pay.save()


# ------------------------------------------------------------------ alerts (replace a notification table)
def owner_alerts(owner):
    out = []
    for p in owner.products.filter(is_active=True):
        lvl = stock_level(p)
        if lvl != "OK":
            out.append({"type": lvl, "title": "CRITICAL STOCK" if lvl == "CRITICAL" else "LOW STOCK",
                        "message": f"{p.product_name}: {total_stock(p)} {p.unit} left (minimum {p.min_stock})."})
    for r in ReorderRequest.objects.filter(product__owner=owner).select_related("product"):
        if r.status == "DELIVERED":
            out.append({"type": "ACTION", "title": "Confirm received stock",
                        "message": f"{r.request_no}: supplier delivered {r.supplied_qty} {r.product.unit} of {r.product.product_name}."})
        elif r.status in ("ACCEPTED", "DISPATCHED", "REJECTED"):
            out.append({"type": "INFO", "title": f"Supplier {r.status.lower()}", "message": f"{r.request_no} ({r.product.product_name}) is {r.status}."})
        elif r.status == "RECEIVED" and r.due_amount > 0:
            out.append({"type": "PAYMENT", "title": "Payment due", "message": f"{r.request_no}: Rs. {r.due_amount} is still to be paid."})
    return out


def supplier_alerts(supplier):
    out = []
    for r in ReorderRequest.objects.filter(product__supplier=supplier).select_related("product", "product__owner"):
        shop = r.product.owner.shop_name
        if r.status == "PENDING":
            out.append({"type": "ACTION", "title": "New reorder request", "message": f"{r.request_no}: {shop} needs {r.requested_qty} {r.product.unit} of {r.product.product_name}."})
        elif r.status == "RECEIVED" and r.due_amount > 0:
            out.append({"type": "PAYMENT", "title": "Payment pending", "message": f"{r.request_no}: {shop} still owes Rs. {r.due_amount}."})
    for p in SupplierPayment.objects.filter(request__product__supplier=supplier, supplier_confirmed=False).select_related("request__product__owner"):
        out.append({"type": "ACTION", "title": "Confirm payment received", "message": f"{p.payment_no}: Rs. {p.amount_paid} from {p.request.product.owner.shop_name}."})
    return out
