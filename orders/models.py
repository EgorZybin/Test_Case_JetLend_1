from decimal import Decimal

from django.db import models
from django.utils import timezone


class User(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'users'

    def __str__(self) -> str:
        return self.email


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self) -> str:
        return self.name


class Good(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='goods')
    exclude_from_promotions = models.BooleanField(default=False)

    class Meta:
        db_table = 'goods'

    def __str__(self) -> str:
        return self.name


class PromoCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    discount = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text='Fractional discount, e.g. 0.1 for 10%.',
    )
    valid_until = models.DateTimeField()
    max_uses = models.PositiveIntegerField()
    times_used = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='promo_codes',
        help_text='When set, promo applies only to goods from this category.',
    )

    class Meta:
        db_table = 'promo_codes'

    def __str__(self) -> str:
        return self.code

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.valid_until

    @property
    def is_exhausted(self) -> bool:
        return self.times_used >= self.max_uses


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='orders',
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Order #{self.pk}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    good = models.ForeignKey(Good, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0'))
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self) -> str:
        return f'{self.good_id} x{self.quantity}'


class PromoCodeUsage(models.Model):
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promo_usages')
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='promo_usage')
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'promo_code_usages'
        constraints = [
            models.UniqueConstraint(
                fields=['promo_code', 'user'],
                name='unique_promo_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.promo_code.code} by user {self.user_id}'
