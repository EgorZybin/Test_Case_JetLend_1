from decimal import Decimal

from rest_framework import serializers

from orders.models import Order


def format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def format_money(value: Decimal):
    quantized = value.quantize(Decimal('0.01'))
    if quantized == quantized.to_integral_value():
        return int(quantized)
    return float(quantized)


class OrderGoodInputSerializer(serializers.Serializer):
    good_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    goods = OrderGoodInputSerializer(many=True, allow_empty=False)
    promo_code = serializers.CharField(max_length=64, required=False, allow_blank=False)


class OrderGoodOutputSerializer(serializers.Serializer):
    good_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def get_price(self, obj) -> int | float:
        return format_money(obj.price)

    def get_discount(self, obj) -> str:
        return format_decimal(obj.discount)

    def get_total(self, obj) -> int | float:
        return format_money(obj.total)


class OrderResponseSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    order_id = serializers.IntegerField(source='id', read_only=True)
    goods = OrderGoodOutputSerializer(source='items', many=True, read_only=True)
    price = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('user_id', 'order_id', 'goods', 'price', 'discount', 'total')

    def get_price(self, obj: Order) -> int | float:
        return format_money(obj.price)

    def get_discount(self, obj: Order) -> str:
        return format_decimal(obj.discount)

    def get_total(self, obj: Order) -> int | float:
        return format_money(obj.total)
