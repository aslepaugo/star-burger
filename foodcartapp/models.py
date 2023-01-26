from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from enum import Enum, auto
from phonenumber_field.modelfields import PhoneNumberField


class OrderStatus(Enum):
    NEW = auto()
    PREPARE = auto()
    DELIVERY = auto()
    DONE = auto()
    CANCELED = auto()


class OrderPaymentMethod(Enum):
    CASH = auto()
    CARD = auto()


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f'{self.restaurant.name} - {self.product.name}'


class OrderQuerySet(models.query.QuerySet):
    def total_price(self):
        return self.annotate(total = models.Sum(models.F('orders__quantity') * models.F('orders__price')))

    def not_done(self):
        return self.exclude(status__in=[OrderStatus.DONE.value, OrderStatus.CANCELED.value])


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        (OrderStatus.NEW.value, 'Новый'),
        (OrderStatus.PREPARE.value, 'Готовится'),
        (OrderStatus.DELIVERY.value, 'Доставляется'),
        (OrderStatus.DONE.value, 'Выполнен'),
        (OrderStatus.CANCELED.value, 'Отменен'),
    ]
    ORDER_PAYMENT_METHOD_CHOICE = [
        (OrderPaymentMethod.CASH.value, 'Наличные'),
        (OrderPaymentMethod.CARD.value, 'Картой'),
    ]

    firstname = models.CharField(max_length=255, verbose_name='Имя')
    lastname = models.CharField(max_length=255, verbose_name='Фамилия', db_index=True)
    phonenumber = PhoneNumberField(verbose_name='Телефон', db_index=True)
    address = models.CharField(max_length=255, verbose_name='Адрес')
    status = models.PositiveSmallIntegerField(
        verbose_name='Статус',
        choices=ORDER_STATUS_CHOICES,
        default=OrderStatus.NEW.value,
        db_index=True,
    )
    payment_method = models.PositiveSmallIntegerField(
        verbose_name='Способ оплаты',
        choices=ORDER_PAYMENT_METHOD_CHOICE,
        default=OrderPaymentMethod.CASH.value,
        db_index=True,
    )
    comment = models.TextField(verbose_name='Комментарий', blank=True)
    registered_at = models.DateTimeField(
        verbose_name='Дата регистрации',
        default=timezone.now,
        db_index=True,
    )
    called_at = models.DateTimeField(
        verbose_name='Дата звонка',
        blank=True,
        null=True,
        db_index=True,
    )
    delivered_at = models.DateTimeField(
        verbose_name='Дата доставки',
        blank=True,
        null=True,
        db_index=True,
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.firstname} {self.lastname}, {self.address}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='orders', verbose_name='заказ', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='products', verbose_name='продукт', on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(verbose_name='количество')
    price = models.DecimalField(verbose_name='цена', max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = 'продукт в заказе'
        verbose_name_plural = 'продукты в заказе'

    def __str__(self):
        return f'{self.product} {self.order}'
