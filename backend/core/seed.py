"""The MASTER (code) table: every list of allowed values lives here.
It is filled automatically after `migrate`, so the app works on a fresh database."""
from .models import Master

MASTER_DATA = {
    "PRODUCT_CATEGORY": [("GROCERY", "Grocery"), ("OIL", "Oil"), ("BEVERAGES", "Beverages"), ("SNACKS", "Snacks")],
    "UNIT": [("KG", "KG"), ("LITRE", "Litre"), ("PACK", "Pack"), ("PCS", "Pieces")],
    "BAG_STATUS": [("AVAILABLE", "Available"), ("ACTIVE", "Active"), ("EMPTY", "Empty")],
    "REQUEST_STATUS": [("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected"),
                       ("DISPATCHED", "Dispatched"), ("DELIVERED", "Delivered"), ("RECEIVED", "Received")],
    "PAYMENT_METHOD": [("CASH", "Cash"), ("UPI", "UPI"), ("BANK_TRANSFER", "Bank transfer"), ("CHEQUE", "Cheque")],
    "TXN_TYPE": [("STOCK_RECEIVED", "Stock received"), ("STOCK_ADJUSTMENT", "Stock adjustment"),
                 ("BAG_ACTIVATED", "Bag activated"), ("BAG_EMPTY", "Bag empty")],
}


def seed_master():
    for mtype, items in MASTER_DATA.items():
        for code, value in items:
            Master.objects.get_or_create(master_type=mtype, master_code=code, defaults={"master_value": value})
