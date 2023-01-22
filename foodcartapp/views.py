import json

from django.http import JsonResponse
from django.templatetags.static import static
from phonenumbers import is_valid_number, parse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order, OrderItem, Product


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def validate_field(data: dict, name: str, field_type: type) -> str | None:
    try:
        if data[name] is None:
            return f"{name} can't be empty"
        if not isinstance(data[name], field_type):
            return f'for {name} expected field type {field_type}'
        if not data[name]:
            return f"{name} can't be empty"
    except KeyError:
        return f'{name} is a required field'


@api_view(['POST'])
def register_order(request):
    order_data = request.data
    if not order_data:
        return Response(['Empty request'], status=400)
    errors = []
    error = validate_field(order_data, 'firstname', str)
    if error:
        errors.append(error)
    error = validate_field(order_data, 'lastname', str)
    if error:
        errors.append(error)
    error = validate_field(order_data, 'phonenumber', str)
    if error:
        errors.append(error)
    elif not is_valid_number(parse(order_data['phonenumber'])):
        errors.append('phone number is not valid')
    error = validate_field(order_data, 'address', str)
    if error:
        errors.append(error)
    error = validate_field(order_data, 'products', list)
    if error:
        errors.append(error)
    else:
        order_ids = set(item['product'] for item in order_data['products'])
        db_ids = Product.objects.all().values_list('id', flat=True)
        err_ids = order_ids.difference(db_ids)
        for err_id in err_ids:
            errors.append(f'products:  {err_id}')
    if errors:
        return Response(errors, status=400)
    new_order = Order.objects.create(
        first_name = order_data['firstname'],
        last_name = order_data['lastname'],
        phone_number = order_data['phonenumber'],
        address = order_data['address']
    )
    for item in order_data['products']:
        OrderItem.objects.create(
            order=new_order,
            product=Product.objects.get(pk=item['product']),
            quantity=item['quantity'],
        )
    return Response({})