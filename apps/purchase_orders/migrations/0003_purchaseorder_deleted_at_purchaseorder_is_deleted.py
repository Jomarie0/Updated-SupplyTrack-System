# Generated by Django 5.2.1 on 2025-05-22 16:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchase_orders', '0002_purchaseorder_received_date_purchaseorder_total_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
    ]
