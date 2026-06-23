from django.contrib import admin

from orders.models import Category, Good, Order, OrderItem, PromoCode, PromoCodeUsage, User

admin.site.register(User)
admin.site.register(Category)
admin.site.register(Good)
admin.site.register(PromoCode)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(PromoCodeUsage)
