from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from geopy import distance

from foodcartapp.models import (Order, OrderItem, OrderStatus, Product,
                                Restaurant, RestaurantMenuItem)
from geolocation.models import Location


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })









def serialize_order(order, total, restaurants):
    return {
        'id': order.id,
        'status': order.get_status_display(),
        'payment_method': order.get_payment_method_display(),
        'lastname': order.lastname,
        'firstname': order.firstname,
        'phonenumber': order.phonenumber,
        'address': order.address,
        'comment': order.comment,
        'total': total,
        'restaurant': order.cooking_restaurant.name if order.cooking_restaurant else '',
        'restaurants': restaurants,
    }


def get_order_item_restaurants(restaurants_menu_items, order_item):
    if order_item.order.cooking_restaurant:
        return set()
    
    return  {
        restaurants_menu_item.restaurant
        for restaurants_menu_item in restaurants_menu_items
        if restaurants_menu_item.product.id == order_item.product.id
    }



def get_order_restaurants(order_address, restaurants, locations):
    order_coordinates = (locations.get(order_address)['latitude'], locations.get(order_address)['longitude'])
    if not order_coordinates[0] or not order_coordinates[1]:
        return []
    restaurants_with_distance = []
    for restaurnt in restaurants:
        restaurant_coordinates = (locations.get(restaurnt.address)['latitude'], locations.get(restaurnt.address)['longitude'])
        restaurants_with_distance.append(
            (restaurnt.name,
            (distance.distance(restaurant_coordinates, order_coordinates).km))
        )
    restaurants_with_distance.sort(key=lambda x: x[1])
    return [
        f'{restaurant_name} - {round(restaurant_distance, 2)} км'
        for restaurant_name, restaurant_distance in restaurants_with_distance
    ]


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    
    order_items = (
        OrderItem.objects
        .prefetch_related(Prefetch('order', queryset=Order.objects.total_price()), 'product', )
        .exclude(order__status__in=[OrderStatus.DONE.value, OrderStatus.CANCELED.value])
        .order_by('order__status', 'order__registered_at')
    )
    restaurant_menu_items = (
        RestaurantMenuItem.objects
        .filter(availability=True)
        .prefetch_related('restaurant', 'product')
    )

    restaurants_addresses = {restaurant_menu_item.restaurant.address for restaurant_menu_item in restaurant_menu_items}
    orders_addresses = {order_item.order.address for order_item in order_items}
    addresses = restaurants_addresses | orders_addresses
    locations = Location.objects.filter(raw_address__in=addresses)
    diff_addresses = addresses.difference({location.raw_address for location in locations})
    for address in diff_addresses:
        location = Location.objects.create(raw_address=address)
        location.process_coordinates()  
    if diff_addresses:
        locations = Location.objects.filter(raw_address__in=addresses)
    location_dict = {}
    for location in locations:
        location_dict[location.raw_address] = {
            'latitude': location.latitude,
            'longitude': location.longitude,
        }

    orders = []
    order = None
    order_restaurants = None
    for order_item in order_items:
        if not order or order_item.order.id != order.id:
            if order:
                restaurants_definitions = get_order_restaurants(order.address, order_restaurants, location_dict)
                orders.append(serialize_order(order, order_item.order.total, restaurants_definitions))
            order = order_item.order
            order_restaurants = get_order_item_restaurants(restaurant_menu_items, order_item)
        else:
            order_restaurants = order_restaurants & get_order_item_restaurants(restaurant_menu_items, order_item)

    if order:
        restaurants_definitions = get_order_restaurants(order.address, order_restaurants, location_dict)
        orders.append(serialize_order(order, order_item.order.total, restaurants_definitions))
    
    return render(request, template_name='order_items.html', context={'order_items': orders})
