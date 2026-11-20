"""python manage.py load_demo
Creates 2 shop owners, 3 suppliers, products, bags and a complete restock + payment story.
It uses the same services as the app, so the data is consistent."""
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction

from core import services
from core.models import Master, Product, ReorderRequest, ShopOwner, Supplier
from core.seed import seed_master

PASSWORD = "Demo@12345"
# name, category, selling price, cost price, unit, minimum, reorder qty, supplier index, bag sizes
PRODUCTS = [
    ("Sugar", "GROCERY", 45, 36, "KG", 20, 50, 0, [30, 30, 30]),
    ("Rice", "GROCERY", 60, 48, "KG", 20, 50, 0, [25, 25]),
    ("Wheat", "GROCERY", 38, 30, "KG", 20, 40, 2, [25, 25]),
    ("Dal", "GROCERY", 120, 96, "KG", 15, 30, 2, [20, 20]),
    ("Salt", "GROCERY", 20, 16, "KG", 10, 25, 0, [25]),
    ("Cooking Oil", "OIL", 150, 120, "LITRE", 15, 30, 1, [20, 20]),
    ("Tea", "BEVERAGES", 90, 72, "PACK", 10, 20, 1, [30]),
    ("Biscuits", "SNACKS", 10, 8, "PACK", 20, 60, 1, [100]),
]


class Command(BaseCommand):
    help = "Load demo data"

    @transaction.atomic
    def handle(self, *args, **opts):
        seed_master()
        if ShopOwner.objects.exists():
            self.stdout.write("Demo data already loaded.")
            return
        pw = make_password(PASSWORD)
        suppliers = [Supplier.objects.create(company_name=n, contact_person=n.split()[0], email=f"supplier{i + 1}@demo.com", phone=f"98000000{i + 1}",
                                             address="Pune", password=pw)
                     for i, n in enumerate(["ABC Wholesale", "PQR Distributors", "Maharashtra Grocery Suppliers"])]
        owners = []
        for i, (shop, city) in enumerate([("Smart Mart", "Pune"), ("Shree Ganesh General Store", "Aurangabad")]):
            o = ShopOwner.objects.create(owner_name=f"Owner {i + 1}", email=f"owner{i + 1}@demo.com", phone=f"97000000{i + 1}", password=pw,
                                         shop_name=shop, shop_address=f"Main Road, {city}", city=city)
            owners.append(o)
            for (name, cat, price, cost, unit, mn, ro, si, bags) in PRODUCTS:
                p = Product.objects.create(owner=o, supplier=suppliers[si], category=Master.objects.get(master_type="PRODUCT_CATEGORY", master_code=cat),
                                           product_name=name, selling_price=price, cost_price=cost, unit=unit, min_stock=mn, reorder_qty=ro)
                for q in bags:
                    services.add_bag(p, q, "STOCK_ADJUSTMENT", "Opening stock")

        smart = owners[0]
        P = lambda owner, name: Product.objects.get(owner=owner, product_name=name)

        def supply(req, rate, supplied):
            services.supplier_action(req, "accept", unit_rate=rate)
            services.supplier_action(req, "dispatch")
            services.supplier_action(req, "deliver", supplied_qty=supplied)

        # 1) Rice: received in full, part paid in cash, supplier confirmed
        r = services.create_reorder(P(smart, "Rice"), 50)
        supply(r, 48, 50)
        services.receive_request(r, 50)
        services.confirm_payment(services.pay_supplier(r, 1000, "CASH"))
        # 2) Wheat: received less than requested, fully paid by UPI
        r = services.create_reorder(P(smart, "Wheat"), 40)
        supply(r, 30, 40)
        services.receive_request(r, 38)
        r.refresh_from_db()
        services.pay_supplier(r, r.bill_amount, "UPI", "UPI-4455667788")
        # 3) Dal: delivered by the supplier, waiting for the owner to confirm what was received
        r = services.create_reorder(P(smart, "Dal"), 30)
        supply(r, 96, 30)
        # 4) Sugar falls below the minimum, so the system creates a request by itself
        services.adjust_stock(P(smart, "Sugar"), -72, "COUNT_DIFFERENCE", "Stock count after festival rush")
        # 5) Salt at the second shop falls below the minimum
        services.adjust_stock(P(owners[1], "Salt"), -17, "DAMAGE", "Water damage in storage")
        self.stdout.write(self.style.SUCCESS(f"Demo data loaded. Every demo password is: {PASSWORD}"))
