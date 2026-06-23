from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Category, Good, Order, PromoCode, PromoCodeUsage, User
from orders.services.order_service import OrderService


class OrderServiceTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(email='user@example.com', name='User')
        self.other_user = User.objects.create(email='other@example.com', name='Other')
        self.category = Category.objects.create(name='Electronics')
        self.other_category = Category.objects.create(name='Books')
        self.good = Good.objects.create(
            name='Phone',
            price=Decimal('100.00'),
            category=self.category,
        )
        self.excluded_good = Good.objects.create(
            name='Gift Card',
            price=Decimal('50.00'),
            category=self.category,
            exclude_from_promotions=True,
        )
        self.book = Good.objects.create(
            name='Novel',
            price=Decimal('30.00'),
            category=self.other_category,
        )
        self.promo = PromoCode.objects.create(
            code='SUMMER2025',
            discount=Decimal('0.1'),
            valid_until=timezone.now() + timedelta(days=30),
            max_uses=10,
        )

    def test_create_order_without_promo(self) -> None:
        order = OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [{'good_id': self.good.id, 'quantity': 2}],
            }
        )

        self.assertEqual(order.price, Decimal('200.00'))
        self.assertEqual(order.discount, Decimal('0'))
        self.assertEqual(order.total, Decimal('200.00'))
        item = order.items.get()
        self.assertEqual(item.discount, Decimal('0'))
        self.assertEqual(item.total, Decimal('200.00'))

    def test_create_order_with_promo(self) -> None:
        order = OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [{'good_id': self.good.id, 'quantity': 2}],
                'promo_code': 'SUMMER2025',
            }
        )

        self.assertEqual(order.price, Decimal('200.00'))
        self.assertEqual(order.discount, Decimal('0.1'))
        self.assertEqual(order.total, Decimal('180.00'))
        self.promo.refresh_from_db()
        self.assertEqual(self.promo.times_used, 1)
        self.assertTrue(PromoCodeUsage.objects.filter(promo_code=self.promo, user=self.user).exists())

    def test_promo_not_found(self) -> None:
        with self.assertRaisesMessage(Exception, 'Promo code not found.'):
            OrderService.create_order(
                {
                    'user_id': self.user.id,
                    'goods': [{'good_id': self.good.id, 'quantity': 1}],
                    'promo_code': 'UNKNOWN',
                }
            )

    def test_promo_expired(self) -> None:
        self.promo.valid_until = timezone.now() - timedelta(days=1)
        self.promo.save(update_fields=['valid_until'])

        with self.assertRaisesMessage(Exception, 'Promo code has expired.'):
            OrderService.create_order(
                {
                    'user_id': self.user.id,
                    'goods': [{'good_id': self.good.id, 'quantity': 1}],
                    'promo_code': 'SUMMER2025',
                }
            )

    def test_promo_exhausted(self) -> None:
        self.promo.times_used = self.promo.max_uses
        self.promo.save(update_fields=['times_used'])

        with self.assertRaisesMessage(Exception, 'Promo code usage limit reached.'):
            OrderService.create_order(
                {
                    'user_id': self.user.id,
                    'goods': [{'good_id': self.good.id, 'quantity': 1}],
                    'promo_code': 'SUMMER2025',
                }
            )

    def test_promo_already_used_by_user(self) -> None:
        OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [{'good_id': self.good.id, 'quantity': 1}],
                'promo_code': 'SUMMER2025',
            }
        )

        with self.assertRaisesMessage(Exception, 'User has already used this promo code.'):
            OrderService.create_order(
                {
                    'user_id': self.user.id,
                    'goods': [{'good_id': self.good.id, 'quantity': 1}],
                    'promo_code': 'SUMMER2025',
                }
            )

    def test_promo_category_restriction(self) -> None:
        self.promo.category = self.category
        self.promo.save(update_fields=['category'])

        order = OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [
                    {'good_id': self.good.id, 'quantity': 1},
                    {'good_id': self.book.id, 'quantity': 1},
                ],
                'promo_code': 'SUMMER2025',
            }
        )

        items = {item.good_id: item for item in order.items.all()}
        self.assertEqual(items[self.good.id].discount, Decimal('0.1'))
        self.assertEqual(items[self.good.id].total, Decimal('90.00'))
        self.assertEqual(items[self.book.id].discount, Decimal('0'))
        self.assertEqual(items[self.book.id].total, Decimal('30.00'))
        self.assertEqual(order.price, Decimal('130.00'))
        self.assertEqual(order.discount, Decimal('0.0769'))
        self.assertEqual(order.total, Decimal('120.00'))

    def test_excluded_good_does_not_receive_discount(self) -> None:
        order = OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [
                    {'good_id': self.good.id, 'quantity': 1},
                    {'good_id': self.excluded_good.id, 'quantity': 1},
                ],
                'promo_code': 'SUMMER2025',
            }
        )

        items = {item.good_id: item for item in order.items.all()}
        self.assertEqual(items[self.good.id].total, Decimal('90.00'))
        self.assertEqual(items[self.excluded_good.id].total, Decimal('50.00'))
        self.assertEqual(order.price, Decimal('150.00'))
        self.assertEqual(order.discount, Decimal('0.0667'))
        self.assertEqual(order.total, Decimal('140.00'))

    def test_duplicate_good_ids_are_merged(self) -> None:
        order = OrderService.create_order(
            {
                'user_id': self.user.id,
                'goods': [
                    {'good_id': self.good.id, 'quantity': 1},
                    {'good_id': self.good.id, 'quantity': 2},
                ],
                'promo_code': 'SUMMER2025',
            }
        )

        self.assertEqual(order.items.count(), 1)
        item = order.items.get()
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.total, Decimal('270.00'))


class CreateOrderAPITestCase(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(email='api@example.com', name='API User')
        self.category = Category.objects.create(name='Default')
        self.good = Good.objects.create(
            name='Laptop',
            price=Decimal('100.00'),
            category=self.category,
        )
        PromoCode.objects.create(
            code='SUMMER2025',
            discount=Decimal('0.1'),
            valid_until=timezone.now() + timedelta(days=30),
            max_uses=10,
        )

    def test_create_order_success(self) -> None:
        response = self.client.post(
            '/api/orders/',
            {
                'user_id': self.user.id,
                'goods': [{'good_id': self.good.id, 'quantity': 2}],
                'promo_code': 'SUMMER2025',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data,
            {
                'user_id': self.user.id,
                'order_id': Order.objects.get().id,
                'goods': [
                    {
                        'good_id': self.good.id,
                        'quantity': 2,
                        'price': 100,
                        'discount': '0.1',
                        'total': 180,
                    }
                ],
                'price': 200,
                'discount': '0.1',
                'total': 180,
            },
        )

    def test_validation_error_for_empty_goods(self) -> None:
        response = self.client.post(
            '/api/orders/',
            {'user_id': self.user.id, 'goods': []},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('goods', response.data)

    def test_domain_error_for_unknown_user(self) -> None:
        response = self.client.post(
            '/api/orders/',
            {
                'user_id': 999,
                'goods': [{'good_id': self.good.id, 'quantity': 1}],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['code'], 'user_not_found')

    def test_order_discount_reflects_effective_rate_for_partial_promo(self) -> None:
        excluded = Good.objects.create(
            name='Gift Card',
            price=Decimal('50.00'),
            category=self.category,
            exclude_from_promotions=True,
        )

        response = self.client.post(
            '/api/orders/',
            {
                'user_id': self.user.id,
                'goods': [
                    {'good_id': self.good.id, 'quantity': 1},
                    {'good_id': excluded.id, 'quantity': 1},
                ],
                'promo_code': 'SUMMER2025',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['price'], 150)
        self.assertEqual(response.data['total'], 140)
        self.assertEqual(response.data['discount'], '0.0667')
        self.assertEqual(response.data['goods'][0]['discount'], '0.1')
        self.assertEqual(response.data['goods'][1]['discount'], '0')
