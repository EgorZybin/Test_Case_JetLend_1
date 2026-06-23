from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.exceptions import OrderServiceError
from orders.serializers import CreateOrderSerializer, OrderResponseSerializer
from orders.services.order_service import OrderService


class CreateOrderView(APIView):
    def post(self, request: Request) -> Response:
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.create_order(serializer.validated_data)
        except OrderServiceError as exc:
            return Response({'error': exc.message, 'code': exc.code}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrderResponseSerializer(order).data, status=status.HTTP_201_CREATED)
