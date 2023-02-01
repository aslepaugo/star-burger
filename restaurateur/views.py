from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from geopy import distance
from geopy.exc import GeopyError

from foodcartapp.models import Order, Product, Restaurant
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


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.total_price().not_done().order_by('status', '-registered_at')
    restaurants = []
    for order in orders:
        if order.restaurant:
            restaurants.append([])
            continue

        suitable_restaurants = Restaurant.objects.suitable_for_order(order)
        distances = [-1] * len(suitable_restaurants)

        client_location, _ = Location.objects.get_or_create(raw_address=order.address)
        try:
            if not client_location.processed:
                client_location.process_coordinates()
        except (GeopyError, TypeError):
            restaurants.append(list(zip(suitable_restaurants, distances)),)
            continue
        client_coordinates = (client_location.latitude, client_location.longitude)

        for index, restaurant in enumerate(suitable_restaurants):
            restaurant_location, _ = Location.objects.get_or_create(raw_address=restaurant.address)
            try:
                if not restaurant_location.processed:
                    restaurant_location.process_coordinates()
            except (GeopyError, TypeError):
                continue

            restaurant_coordinates = (restaurant_location.latitude, restaurant_location.longitude)
            delivery_distance = distance.distance(client_coordinates, restaurant_coordinates).km
            distances[index] = delivery_distance

        restaurants.append(
            sorted(
                tuple(zip(suitable_restaurants, distances)),
                key=lambda item: float(item[1])
            )
        )
    orders_with_restaurants = list(zip(orders, restaurants))

    return render(request, template_name='order_items.html', context={
        'order_items': orders_with_restaurants,
    })
