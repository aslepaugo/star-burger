from django.contrib import admin

from geolocation.models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = [
        'processed',
        'raw_address',
        'normalized_address',
        'latitude',
        'longitude',
        'updated_at',
    ]
