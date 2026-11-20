"""REST API. Views stay thin: the business rules live in services.py."""
import re
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import services
from .auth import make_token
from .models import Bag, Master, Product, ReorderRequest, ShopOwner, StockTransaction, Supplier, SupplierPayment
from .permissions import IsOwner, IsSupplier
from .serializers import (BagSerializer, MasterSerializer, PaymentSerializer, ProductSerializer, RequestSerializer, TxnSerializer)


# ---------------------------------------------------------------- login / registration
def _profile(role, o):
    if role == "OWNER":
        return {"role": role, "id": o.id, "name": o.owner_name, "email": o.email, "phone": o.phone,
                "shop_name": o.shop_name, "shop_address": o.shop_address, "city": o.city}
    return {"role": role, "id": o.id, "name": o.company_name, "email": o.email, "phone": o.phone,
            "contact_person": o.contact_person, "address": o.address}


def _check_new_account(d):
    email = (d.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise ValidationError({"email": "Enter a valid email."})
    if ShopOwner.objects.filter(email=email).exists() or Supplier.objects.filter(email=email).exists():
        raise ValidationError({"email": "This email is already registered."})
    pw = d.get("password") or ""
    if len(pw) < 8 or not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        raise ValidationError({"password": "Use at least 8 characters with letters and digits."})
    phone = d.get("phone") or ""
    if phone and not phone.replace("+", "").isdigit():
        raise ValidationError({"phone": "Digits only."})
    return email, make_password(pw)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_owner(request):
    d = request.data
    email, pw = _check_new_account(d)
    if not d.get("owner_name") or not d.get("shop_name") or not d.get("shop_address"):
        raise ValidationError("Owner name, shop name and shop address are required.")
    o = ShopOwner.objects.create(owner_name=d["owner_name"], email=email, password=pw, phone=d.get("phone", ""),
                                 shop_name=d["shop_name"], shop_address=d["shop_address"], city=d.get("city", ""))
    return Response(_profile("OWNER", o), status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_supplier(request):
    d = request.data
    email, pw = _check_new_account(d)
    if not d.get("company_name"):
        raise ValidationError("Company name is required.")
    s = Supplier.objects.create(company_name=d["company_name"], email=email, password=pw, phone=d.get("phone", ""),
                                contact_person=d.get("contact_person", ""), address=d.get("address", ""))
    return Response(_profile("SUPPLIER", s), status=201)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    role = request.data.get("role")
    model = {"OWNER": ShopOwner, "SUPPLIER": Supplier}.get(role)
    email = (request.data.get("email") or "").strip().lower()
    obj = model.objects.filter(email=email).first() if model else None
    if obj is None or not check_password(request.data.get("password") or "", obj.password):
        return Response({"detail": "Invalid email, password or role."}, status=401)
    return Response({"token": make_token(role, obj), "user": _profile(role, obj)})


@api_view(["GET"])
def me(request):
    return Response(_profile(request.user.role, request.user.obj))


# ---------------------------------------------------------------- master (code table)
@api_view(["GET", "POST"])
def masters(request):
    if request.method == "POST":  # the owner may add new product categories
        if request.user.role != "OWNER":
            raise PermissionDenied()
        value = (request.data.get("master_value") or "").strip()
        if not value:
            raise ValidationError({"master_value": "Enter the category name."})
        code = re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")[:30]
        m, _ = Master.objects.get_or_create(master_type="PRODUCT_CATEGORY", master_code=code, defaults={"master_value": value})
        return Response(MasterSerializer(m).data, status=201)
    qs = Master.objects.all()
    if request.GET.get("type"):
        qs = qs.filter(master_type=request.GET["type"])
    return Response(MasterSerializer(qs.order_by("master_type", "master_value"), many=True).data)


@api_view(["GET"])
@permission_classes([IsOwner])
def supplier_list(request):
    return Response([{"id": s.id, "company_name": s.company_name} for s in Supplier.objects.order_by("company_name")])


# ---------------------------------------------------------------- products and stock (owner)
class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwner]
    serializer_class = ProductSerializer

    def get_queryset(self):
        qs = Product.objects.filter(owner=self.request.user.obj).select_related("category", "supplier")
        q = self.request.GET.get("search")
        if q:
            qs = qs.filter(Q(product_name__icontains=q) | Q(bags__bag_code__icontains=q)).distinct()
        return qs.order_by("product_name")

    def perform_create(self, ser):
        owner = self.request.user.obj
        if Product.objects.filter(owner=owner, product_name__iexact=ser.validated_data["product_name"]).exists():
            raise ValidationError({"product_name": "You already have a product with this name."})
        ser.save(owner=owner)

    def destroy(self, request, *args, **kwargs):
        p = self.get_object()  # history is kept: only deactivate
        p.is_active = False
        p.save()
        return Response({"detail": "Product deactivated."})


@api_view(["GET", "POST"])
@permission_classes([IsOwner])
def bags(request):
    owner = request.user.obj
    if request.method == "POST":  # opening stock = a new bag, logged in the ledger
        p = get_object_or_404(Product, pk=request.data.get("product"), owner=owner)
        bag = services.add_bag(p, request.data.get("quantity"), "STOCK_ADJUSTMENT", "Opening stock")
        return Response(BagSerializer(bag).data, status=201)
    qs = Bag.objects.filter(product__owner=owner).select_related("product").order_by("product__product_name", "id")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    return Response(BagSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsOwner])
def stock_adjust(request):
    p = get_object_or_404(Product, pk=request.data.get("product"), owner=request.user.obj)
    services.adjust_stock(p, request.data.get("quantity"), request.data.get("reason", "OTHER"), request.data.get("remarks"))
    return Response({"detail": "Stock adjusted."})


@api_view(["GET"])
@permission_classes([IsOwner])
def stock_history(request):
    qs = StockTransaction.objects.filter(bag__product__owner=request.user.obj).select_related("bag__product")
    if request.GET.get("product"):
        qs = qs.filter(bag__product_id=request.GET["product"])
    if request.GET.get("type"):
        qs = qs.filter(txn_type=request.GET["type"])
    return Response(TxnSerializer(qs[:300], many=True).data)


# ---------------------------------------------------------------- reorder requests (owner and supplier)
def _requests_for(user):
    if user.role == "OWNER":
        return ReorderRequest.objects.filter(product__owner=user.obj)
    return ReorderRequest.objects.filter(product__supplier=user.obj)


@api_view(["GET", "POST"])
def reorders(request):
    user = request.user
    if request.method == "POST":
        if user.role != "OWNER":
            raise PermissionDenied()
        p = get_object_or_404(Product, pk=request.data.get("product"), owner=user.obj)
        r = services.create_reorder(p, request.data.get("quantity") or p.reorder_qty)
        return Response(RequestSerializer(r).data, status=201)
    qs = _requests_for(user).select_related("product__owner", "product__supplier")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    q = request.GET.get("search")
    if q:
        digits = re.sub(r"\D", "", q)
        cond = Q(product__product_name__icontains=q) | Q(product__owner__shop_name__icontains=q)
        if digits:
            cond |= Q(id=int(digits))
        qs = qs.filter(cond)
    return Response(RequestSerializer(qs.order_by("-id"), many=True).data)


@api_view(["POST"])
@permission_classes([IsSupplier])
def reorder_supplier_action(request, pk, action):
    req = get_object_or_404(ReorderRequest, pk=pk, product__supplier=request.user.obj)
    services.supplier_action(req, action, request.data.get("supplied_qty"), request.data.get("unit_rate"))
    return Response({"detail": f"Request {action} done."})


@api_view(["POST"])
@permission_classes([IsOwner])
def reorder_receive(request, pk):
    req = get_object_or_404(ReorderRequest, pk=pk, product__owner=request.user.obj)
    services.receive_request(req, request.data.get("received_qty"))
    return Response({"detail": "Stock received and added."})


@api_view(["GET"])
@permission_classes([IsOwner])
def restocked(request):
    """Restocked Items: received requests with the stock before and after."""
    out = []
    for r in _requests_for(request.user).filter(status="RECEIVED").select_related("product__supplier", "product__owner").order_by("-id"):
        t = StockTransaction.objects.filter(txn_type="STOCK_RECEIVED", remarks=r.request_no, bag__product=r.product).first()
        d = RequestSerializer(r).data
        d.update({"qty_before": t.qty_before if t else None, "qty_after": t.qty_after if t else None, "received_on": t.txn_date if t else None})
        out.append(d)
    return Response(out)


# ---------------------------------------------------------------- supplier payments
@api_view(["POST"])
@permission_classes([IsOwner])
def reorder_pay(request, pk):
    req = get_object_or_404(ReorderRequest, pk=pk, product__owner=request.user.obj)
    pay = services.pay_supplier(req, request.data.get("amount"), request.data.get("payment_method", "CASH"), request.data.get("reference_no", ""))
    return Response(PaymentSerializer(pay).data, status=201)


def _payments_for(user):
    if user.role == "OWNER":
        return SupplierPayment.objects.filter(request__product__owner=user.obj)
    return SupplierPayment.objects.filter(request__product__supplier=user.obj)


@api_view(["GET"])
def payments(request):
    qs = _payments_for(request.user).select_related("request__product__owner", "request__product__supplier")
    return Response(PaymentSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsSupplier])
def payment_confirm(request, pk):
    pay = get_object_or_404(SupplierPayment, pk=pk, request__product__supplier=request.user.obj)
    services.confirm_payment(pay)
    return Response({"detail": "Payment confirmed."})


@api_view(["GET"])
def payments_summary(request):
    """Owner: what the shop owes each supplier. Supplier: what each shop owes."""
    user = request.user
    key = "product__supplier__company_name" if user.role == "OWNER" else "product__owner__shop_name"
    rows, billed, paid = [], Decimal(0), Decimal(0)
    per = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for r in _requests_for(user).filter(status="RECEIVED").select_related("product__owner", "product__supplier"):
        if r.bill_amount <= 0:
            continue
        name = r.product.supplier.company_name if user.role == "OWNER" else r.product.owner.shop_name
        per[name][0] += r.bill_amount
        per[name][1] += r.amount_paid
        billed += r.bill_amount
        paid += r.amount_paid
    for name, (b, p) in per.items():
        rows.append({"name": name, "billed": b, "paid": p, "due": b - p})
    return Response({"billed": billed, "paid": paid, "due": billed - paid,
                     "unconfirmed": _payments_for(user).filter(supplier_confirmed=False).count(), "by_party": rows})


# ---------------------------------------------------------------- alerts, dashboard, reports, search
@api_view(["GET"])
def alerts(request):
    user = request.user
    items = services.owner_alerts(user.obj) if user.role == "OWNER" else services.supplier_alerts(user.obj)
    return Response({"count": len(items), "results": items})


def _local_date(dt):
    return timezone.localtime(dt).date()


@api_view(["GET"])
@permission_classes([IsOwner])
def dashboard(request):
    owner = request.user.obj
    days = {"7": 7, "30": 30}.get(request.GET.get("days"), 30)
    start = timezone.localdate() - timedelta(days=days - 1)
    prods = list(owner.products.filter(is_active=True))
    low = [p for p in prods if services.stock_level(p) != "OK"]
    reqs = list(ReorderRequest.objects.filter(product__owner=owner).select_related("product__supplier"))
    received = [r for r in reqs if r.status == "RECEIVED" and r.bill_amount > 0]
    billed = sum((r.bill_amount for r in received), Decimal(0))
    paid = sum((r.amount_paid for r in received), Decimal(0))
    recv, pay = defaultdict(Decimal), defaultdict(Decimal)
    for t in StockTransaction.objects.filter(bag__product__owner=owner, txn_type="STOCK_RECEIVED"):
        if _local_date(t.txn_date) >= start:
            recv[_local_date(t.txn_date)] += t.quantity
    for p in SupplierPayment.objects.filter(request__product__owner=owner):
        if _local_date(p.payment_date) >= start:
            pay[_local_date(p.payment_date)] += p.amount_paid
    series = []
    for i in range(days):
        d = start + timedelta(days=i)
        series.append({"date": d.strftime("%d %b"), "received_qty": recv[d], "paid": pay[d]})
    per = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for r in received:
        per[r.product.supplier.company_name][0] += r.bill_amount
        per[r.product.supplier.company_name][1] += r.amount_paid
    return Response({
        "cards": {"total_products": len(prods), "low_stock": len(low), "open_requests": sum(1 for r in reqs if r.status in services.OPEN),
                  "awaiting_receipt": sum(1 for r in reqs if r.status == "DELIVERED"), "billed": billed, "paid": paid, "due": billed - paid},
        "series": series,
        "suppliers": [{"name": n, "billed": b, "paid": p} for n, (b, p) in per.items()],
        "low_stock_products": [{"id": p.id, "name": p.product_name, "stock": services.total_stock(p), "min": p.min_stock, "unit": p.unit,
                                "level": services.stock_level(p)} for p in low]})


def _report_rows(kind, user):
    if kind == "stock":
        rows = []
        for p in user.obj.products.all():
            act = p.bags.filter(status="ACTIVE").first()
            rows.append([p.product_name, p.category.master_value if p.category else "", services.total_stock(p), p.unit, p.min_stock,
                         services.stock_level(p), act.bag_code if act else "", p.bags.filter(status="EMPTY").count(),
                         p.supplier.company_name if p.supplier else ""])
        return ["Product", "Category", "Stock", "Unit", "Minimum", "Level", "Active bag", "Empty bags", "Supplier"], rows
    if kind == "movement":
        qs = StockTransaction.objects.filter(bag__product__owner=user.obj).select_related("bag__product")
        return ["Date", "Product", "Bag", "Type", "Quantity", "Before", "After", "Remarks"], [
            [timezone.localtime(t.txn_date).strftime("%Y-%m-%d %H:%M"), t.bag.product.product_name, t.bag.bag_code, t.txn_type,
             t.quantity, t.qty_before, t.qty_after, t.remarks] for t in qs]
    if kind == "requests":
        qs = _requests_for(user).select_related("product__supplier", "product__owner")
        return ["Request", "Date", "Product", "Supplier", "Requested", "Supplied", "Received", "Rate", "Bill", "Paid", "Due", "Status", "Payment"], [
            [r.request_no, timezone.localtime(r.request_date).strftime("%Y-%m-%d"), r.product.product_name, r.product.supplier.company_name,
             r.requested_qty, r.supplied_qty, r.received_qty, r.unit_rate, r.bill_amount, r.amount_paid, r.due_amount, r.status,
             r.payment_status] for r in qs]
    if kind == "payments":
        qs = _payments_for(user).select_related("request__product__supplier")
        return ["Payment", "Date", "Supplier", "Request", "Product", "Amount", "Method", "Reference", "Balance after", "Supplier confirmed"], [
            [p.payment_no, timezone.localtime(p.payment_date).strftime("%Y-%m-%d"), p.request.product.supplier.company_name,
             p.request.request_no, p.request.product.product_name, p.amount_paid, p.payment_method, p.reference_no,
             p.balance_remaining, "Yes" if p.supplier_confirmed else "No"] for p in qs]
    raise ValidationError("Unknown report.")


@api_view(["GET"])
@permission_classes([IsOwner])
def report(request, kind):
    headers, rows = _report_rows(kind, request.user)
    if request.GET.get("format") == "csv":
        import csv
        from django.http import HttpResponse
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{kind}-report.csv"'
        w = csv.writer(resp)
        w.writerow(headers)
        w.writerows(rows)
        return resp
    return Response({"headers": headers, "rows": rows})


@api_view(["GET"])
def search(request):
    q, user = (request.GET.get("q") or "").strip(), request.user
    if len(q) < 2:
        return Response({})
    reqs = _requests_for(user).filter(Q(product__product_name__icontains=q) | Q(product__owner__shop_name__icontains=q))
    digits = re.sub(r"\D", "", q)
    if digits:
        reqs = _requests_for(user).filter(Q(id=int(digits)) | Q(product__product_name__icontains=q))
    out = {"Requests": [f"{r.request_no} · {r.product.product_name} · {r.status}" for r in reqs.select_related("product")[:8]]}
    if user.role == "OWNER":
        o = user.obj
        out["Products"] = [p.product_name for p in o.products.filter(product_name__icontains=q)[:8]]
        out["Bags"] = [f"{b.bag_code} · {b.status} · {b.current_qty}" for b in Bag.objects.filter(product__owner=o, bag_code__icontains=q)[:8]]
        out["Suppliers"] = [s.company_name for s in Supplier.objects.filter(company_name__icontains=q)[:8]]
    return Response(out)
