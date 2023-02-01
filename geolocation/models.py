from django.conf import settings
from django.db import models
from django.utils import timezone
from geopy.geocoders import Yandex


class Location(models.Model):
    raw_address = models.CharField(
        verbose_name='Адрес доставки',
        max_length=255,
        db_index=True,
        unique=True,
    )
    normalized_address = models.CharField(
        verbose_name='Нормализованый адрес',
        max_length=255,
        db_index=True,
        null=True,
    )
    latitude = models.DecimalField(
        verbose_name='Широта',
        max_digits=8,
        decimal_places=6,
        db_index=True,
        null=True,
    )
    longitude = models.DecimalField(
        verbose_name='Долгота',
        max_digits=8,
        decimal_places=6,
        db_index=True,
        null=True,
    )
    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        editable=False,
        default=timezone.now
    )
    processed = models.BooleanField(
        verbose_name='Обработан',
        default=False,
    )

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def process_coordinates(self):
        geocoder = Yandex(api_key=settings.YANDEX_API_KEY)
        normalized_address, coordinates = geocoder.geocode(self.raw_address)
        self.normalized_address = normalized_address
        self.latitude, self.longitude = coordinates
        self.processed = True
        self.updated_at = timezone.now()
        self.save()
