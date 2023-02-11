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

    latitude = models.DecimalField(
        verbose_name='Широта',
        max_digits=9,
        decimal_places=6,
        db_index=True,
        null=True,
    )
    longitude = models.DecimalField(
        verbose_name='Долгота',
        max_digits=9,
        decimal_places=6,
        db_index=True,
        null=True,
    )
    updated_at = models.DateTimeField(
        verbose_name='Дата обновления',
        editable=False,
        default=timezone.now
    )

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def process_coordinates(self):
        geocoder = Yandex(api_key=settings.YANDEX_API_KEY)
        try:
            _, coordinates = geocoder.geocode(self.raw_address)
        except TypeError:
            coordinates = None
        if coordinates:
            self.latitude, self.longitude = coordinates
            self.updated_at = timezone.now()
            self.save()

    def __str__(self):
        return f"{self.raw_address} {self.latitude} {self.longitude} {self.updated_at}"
