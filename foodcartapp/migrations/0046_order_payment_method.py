# Generated by Django 3.2.15 on 2023-01-26 07:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0045_auto_20230126_0816'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Наличные'), (2, 'Картой')], db_index=True, default=1, verbose_name='Способ оплаты'),
        ),
    ]
