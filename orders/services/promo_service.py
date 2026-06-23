from decimal import Decimal

from django.db.models import F
from django.utils import timezone

from orders.exceptions import (
    PromoCodeAlreadyUsedError,
    PromoCodeExhaustedError,
    PromoCodeExpiredError,
    PromoCodeNotFoundError,
)
from orders.models import Good, PromoCode, PromoCodeUsage, User


class PromoService:
    @staticmethod
    def get_promo_code(code: str) -> PromoCode:
        try:
            return PromoCode.objects.select_related('category').get(code=code)
        except PromoCode.DoesNotExist as exc:
            raise PromoCodeNotFoundError() from exc

    @staticmethod
    def validate_promo_for_user(promo: PromoCode, user: User) -> None:
        if promo.is_expired:
            raise PromoCodeExpiredError()

        if promo.is_exhausted:
            raise PromoCodeExhaustedError()

        if PromoCodeUsage.objects.filter(promo_code=promo, user=user).exists():
            raise PromoCodeAlreadyUsedError()

    @staticmethod
    def is_good_eligible(promo: PromoCode, good: Good) -> bool:
        if good.exclude_from_promotions:
            return False

        if promo.category_id is not None and good.category_id != promo.category_id:
            return False

        return True

    @staticmethod
    def reserve_usage(promo: PromoCode) -> None:
        updated = PromoCode.objects.filter(
            pk=promo.pk,
            times_used__lt=F('max_uses'),
            valid_until__gt=timezone.now(),
        ).update(times_used=F('times_used') + 1)

        if updated == 0:
            promo.refresh_from_db()
            if promo.is_expired:
                raise PromoCodeExpiredError()
            raise PromoCodeExhaustedError()

    @staticmethod
    def item_discount(promo: PromoCode | None, good: Good) -> Decimal:
        if promo is None:
            return Decimal('0')

        if not PromoService.is_good_eligible(promo, good):
            return Decimal('0')

        return promo.discount
