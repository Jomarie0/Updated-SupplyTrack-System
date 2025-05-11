from django.db import models
from apps.orders.models import Order
from django.utils import timezone

class Delivery(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='deliveries')
    delivery_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Dispatch'),
            ('out_for_delivery', 'Out for Delivery'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('returned', 'Returned'),  # New status
        ],
        default='pending'
    )
    
    delivered_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Delivery for Order: {self.order.order_id} - Status: {self.delivery_status}"

    def save(self, *args, **kwargs):
        # Check if the status is being changed to 'delivered'
        if self.pk:  # If the instance already exists (i.e., it's an update)
            try:
                old_status = Delivery.objects.get(pk=self.pk).delivery_status
                if self.delivery_status == 'delivered' and old_status != 'delivered':
                    self.delivered_at = timezone.now()
                    super().save(*args, **kwargs)  # Save the Delivery instance first
                    from apps.delivery.signals import delivery_confirmed  # Import here
                    delivery_confirmed.send(sender=self.__class__, order=self.order)
                else:
                    super().save(*args, **kwargs)
            except Delivery.DoesNotExist:
                # Handle the case where the Delivery object might have been deleted
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)