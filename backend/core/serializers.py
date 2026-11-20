from rest_framework import serializers

from . import services
from .models import Bag, Master, Product, ReorderRequest, StockTransaction, SupplierPayment


class MasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Master
        fields = ["id", "master_type", "master_code", "master_value"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.master_value", read_only=True, default="")
    supplier_name = serializers.CharField(source="supplier.company_name", read_only=True, default="")
    total_stock = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "product_name", "category", "category_name", "selling_price", "cost_price", "unit", "min_stock",
                  "reorder_qty", "supplier", "supplier_name", "is_active", "total_stock", "stock_status"]

    def get_total_stock(self, p):
        return services.total_stock(p)

    def get_stock_status(self, p):
        return services.stock_level(p)

    def validate_unit(self, v):
        services.check_master("UNIT", v, "unit")
        return v

    def validate_category(self, v):
        if v is not None and v.master_type != "PRODUCT_CATEGORY":
            raise serializers.ValidationError("Choose a product category.")
        return v

    def validate(self, d):
        if d.get("selling_price") is not None and d["selling_price"] <= 0:
            raise serializers.ValidationError({"selling_price": "Price must be greater than zero."})
        for f in ("cost_price", "min_stock", "reorder_qty"):
            if d.get(f) is not None and d[f] < 0:
                raise serializers.ValidationError({f: "Cannot be negative."})
        return d


class BagSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    unit = serializers.CharField(source="product.unit", read_only=True)

    class Meta:
        model = Bag
        fields = ["id", "bag_code", "product", "product_name", "unit", "initial_qty", "current_qty", "status"]


class TxnSerializer(serializers.ModelSerializer):
    bag_code = serializers.CharField(source="bag.bag_code")
    product_name = serializers.CharField(source="bag.product.product_name")
    unit = serializers.CharField(source="bag.product.unit")

    class Meta:
        model = StockTransaction
        fields = ["id", "txn_date", "txn_type", "bag_code", "product_name", "unit", "quantity", "qty_before", "qty_after", "remarks"]


class RequestSerializer(serializers.ModelSerializer):
    request_no = serializers.CharField(read_only=True)
    product_name = serializers.CharField(source="product.product_name")
    unit = serializers.CharField(source="product.unit")
    shop_name = serializers.CharField(source="product.owner.shop_name")
    supplier_name = serializers.CharField(source="product.supplier.company_name", default="")
    bill_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    due_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payment_status = serializers.CharField(read_only=True)

    class Meta:
        model = ReorderRequest
        fields = ["id", "request_no", "product", "product_name", "unit", "shop_name", "supplier_name", "request_date", "status",
                  "requested_qty", "supplied_qty", "received_qty", "unit_rate", "bill_amount", "amount_paid", "due_amount", "payment_status"]


class PaymentSerializer(serializers.ModelSerializer):
    payment_no = serializers.CharField(read_only=True)
    request_no = serializers.CharField(source="request.request_no")
    product_name = serializers.CharField(source="request.product.product_name")
    shop_name = serializers.CharField(source="request.product.owner.shop_name")
    supplier_name = serializers.CharField(source="request.product.supplier.company_name")

    class Meta:
        model = SupplierPayment
        fields = ["id", "payment_no", "request", "request_no", "product_name", "shop_name", "supplier_name", "payment_date",
                  "payment_method", "amount_paid", "reference_no", "balance_remaining", "supplier_confirmed"]
