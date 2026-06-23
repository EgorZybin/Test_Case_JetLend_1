from django.urls import path

from orders.views import CreateOrderView

urlpatterns = [
    path('orders/', CreateOrderView.as_view(), name='create-order'),
]
