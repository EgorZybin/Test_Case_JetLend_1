from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from orders.models import Category, Good, PromoCode, User


class Command(BaseCommand):
    help = 'Load demo data for local development and manual testing.'

    def handle(self, *args, **options) -> None:
        user, _ = User.objects.get_or_create(
            email='demo@example.com',
            defaults={'name': 'Demo User'},
        )
        category, _ = Category.objects.get_or_create(name='Electronics')
        books, _ = Category.objects.get_or_create(name='Books')

        good, _ = Good.objects.get_or_create(
            name='Smartphone',
            defaults={
                'price': Decimal('100.00'),
                'category': category,
            },
        )
        Good.objects.get_or_create(
            name='Gift Card',
            defaults={
                'price': Decimal('50.00'),
                'category': category,
                'exclude_from_promotions': True,
            },
        )
        Good.objects.get_or_create(
            name='Novel',
            defaults={
                'price': Decimal('30.00'),
                'category': books,
            },
        )

        PromoCode.objects.get_or_create(
            code='SUMMER2025',
            defaults={
                'discount': Decimal('0.1'),
                'valid_until': timezone.now() + timedelta(days=30),
                'max_uses': 100,
            },
        )
        PromoCode.objects.get_or_create(
            code='BOOKS15',
            defaults={
                'discount': Decimal('0.15'),
                'valid_until': timezone.now() + timedelta(days=30),
                'max_uses': 50,
                'category': books,
            },
        )

        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
        self.stdout.write(f'User id: {user.id}')
        self.stdout.write(f'Good id: {good.id}')
