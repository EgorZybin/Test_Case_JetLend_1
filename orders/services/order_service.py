from decimal import Decimal
from typing import TypedDict

from django.db import transaction

from orders.exceptions import GoodNotFoundError, InvalidOrderItemsError, UserNotFoundError
from orders.models import Good, Order, OrderItem, PromoCodeUsage, User
from orders.services.promo_service import PromoService


class OrderGoodInput(TypedDict):
    good_id: int
    quantity: int


class OrderCreateInput(TypedDict, total=False):
    user_id: int
    goods: list[OrderGoodInput]
    promo_code: str


class OrderService:
    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        return value.quantize(Decimal('0.01'))

    @staticmethod
    def _calculate_line_total(unit_price: Decimal, quantity: int, discount: Decimal) -> Decimal:
        subtotal = unit_price * quantity
        return OrderService._quantize_money(subtotal * (Decimal('1') - discount))

    @staticmethod
    def _calculate_effective_discount(order_price: Decimal, order_total: Decimal) -> Decimal:
        if order_price == 0:
            return Decimal('0')

        return ((order_price - order_total) / order_price).quantize(Decimal('0.0001'))

    @classmethod
    @transaction.atomic
    def create_order(cls, data: OrderCreateInput) -> Order:
        goods_data = data.get('goods') or []
        if not goods_data:
            raise InvalidOrderItemsError()

        aggregated_goods: dict[int, int] = {}
        for item in goods_data:
            good_id = item['good_id']
            aggregated_goods[good_id] = aggregated_goods.get(good_id, 0) + item['quantity']
        goods_data = [{'good_id': gid, 'quantity': qty} for gid, qty in aggregated_goods.items()]

        try:
            user = User.objects.get(pk=data['user_id'])
        except User.DoesNotExist as exc:
            raise UserNotFoundError() from exc

        promo = None
        promo_code_value = data.get('promo_code')
        if promo_code_value:
            promo = PromoService.get_promo_code(promo_code_value)
            PromoService.validate_promo_for_user(promo, user)
            PromoService.reserve_usage(promo)

        good_ids = [item['good_id'] for item in goods_data]
        goods_by_id = Good.objects.select_related('category').in_bulk(good_ids)
        if len(goods_by_id) != len(set(good_ids)):
            missing = set(good_ids) - set(goods_by_id)
            raise GoodNotFoundError(f'Goods not found: {sorted(missing)}')

        order_price = Decimal('0')
        order_total = Decimal('0')
        line_items: list[tuple[Good, int, Decimal, Decimal, Decimal]] = []

        for item in goods_data:
            good = goods_by_id[item['good_id']]
            quantity = item['quantity']
            unit_price = good.price
            discount = PromoService.item_discount(promo, good)
            line_subtotal = unit_price * quantity
            line_total = cls._calculate_line_total(unit_price, quantity, discount)

            order_price += line_subtotal
            order_total += line_total
            line_items.append((good, quantity, unit_price, discount, line_total))

        order_discount = cls._calculate_effective_discount(order_price, order_total)

        order = Order.objects.create(
            user=user,
            promo_code=promo,
            price=cls._quantize_money(order_price),
            discount=order_discount,
            total=cls._quantize_money(order_total),
        )

        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    good=good,
                    quantity=quantity,
                    price=unit_price,
                    discount=discount,
                    total=line_total,
                )
                for good, quantity, unit_price, discount, line_total in line_items
            ]
        )

        if promo:
            PromoCodeUsage.objects.create(promo_code=promo, user=user, order=order)

        return order
