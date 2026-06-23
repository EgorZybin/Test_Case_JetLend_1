class OrderServiceError(Exception):
    """Base error for order creation domain logic."""

    default_code = 'order_error'
    default_message = 'Unable to create order.'

    def __init__(self, message: str | None = None, code: str | None = None) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class UserNotFoundError(OrderServiceError):
    default_code = 'user_not_found'
    default_message = 'User not found.'


class GoodNotFoundError(OrderServiceError):
    default_code = 'good_not_found'
    default_message = 'Good not found.'


class InvalidOrderItemsError(OrderServiceError):
    default_code = 'invalid_order_items'
    default_message = 'Order must contain at least one item.'


class PromoCodeNotFoundError(OrderServiceError):
    default_code = 'promo_code_not_found'
    default_message = 'Promo code not found.'


class PromoCodeExpiredError(OrderServiceError):
    default_code = 'promo_code_expired'
    default_message = 'Promo code has expired.'


class PromoCodeExhaustedError(OrderServiceError):
    default_code = 'promo_code_exhausted'
    default_message = 'Promo code usage limit reached.'


class PromoCodeAlreadyUsedError(OrderServiceError):
    default_code = 'promo_code_already_used'
    default_message = 'User has already used this promo code.'
