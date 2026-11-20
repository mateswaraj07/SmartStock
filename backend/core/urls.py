from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/owner/", views.register_owner),
    path("auth/register/supplier/", views.register_supplier),
    path("auth/login/", views.login),
    path("auth/me/", views.me),
    path("masters/", views.masters),
    path("suppliers/", views.supplier_list),
    path("bags/", views.bags),
    path("stock/adjust/", views.stock_adjust),
    path("stock-history/", views.stock_history),
    path("reorders/", views.reorders),
    path("reorders/<int:pk>/receive/", views.reorder_receive),
    path("reorders/<int:pk>/pay/", views.reorder_pay),
    path("reorders/<int:pk>/<str:action>/", views.reorder_supplier_action),
    path("restocked/", views.restocked),
    path("payments/", views.payments),
    path("payments/summary/", views.payments_summary),
    path("payments/<int:pk>/confirm/", views.payment_confirm),
    path("alerts/", views.alerts),
    path("reports/dashboard/", views.dashboard),
    path("reports/<str:kind>/", views.report),
    path("search/", views.search),
]
