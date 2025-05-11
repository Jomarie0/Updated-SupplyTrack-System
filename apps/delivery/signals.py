from django.dispatch import Signal, receiver
from django.db.models.signals import post_save, pre_save
from .models import Delivery
from apps.orders.models import Order
import logging

delivery_confirmed = Signal()
logger = logging.getLogger(__name__)
_previous_delivery_status = {}

@receiver(pre_save, sender=Delivery)
def store_initial_delivery_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _previous_delivery_status[instance.pk] = Delivery.objects.get(pk=instance.pk).delivery_status
        except Delivery.DoesNotExist:
            pass

@receiver(post_save, sender=Delivery)
def update_order_status_on_delivery_change(sender, instance, **kwargs):
    delivery_status = instance.delivery_status
    previous_status = _previous_delivery_status.pop(instance.pk, None)
    order = instance.order

    if previous_status != delivery_status:
        if delivery_status == 'failed':
            if order.status == 'Completed':
                order.status = 'Delivery Failed'
                order.save()
                logger.info(f"Order {order.order_id} status updated to Delivery Failed due to failed delivery.")
            elif order.status != 'Delivery Failed':
                order.status = 'Delivery Failed' # Update even if not 'Completed' initially
                order.save()
                logger.info(f"Order {order.order_id} status updated to Delivery Failed.")
        elif delivery_status == 'returned':
            if order.status in ['Completed', 'Delivery Failed']:
                order.status = 'Returned'
                order.save()
                logger.info(f"Order {order.order_id} status updated to Returned.")
        elif delivery_status == 'pending' and order.status == 'Completed':
            order.status = 'Pending'
            order.save()
            logger.info(f"Order {order.order_id} status updated to Pending due to delivery status change.")
        elif delivery_status == 'out_for_delivery' and order.status != 'Completed':
            order.status = 'Out for Delivery'
            order.save()
            logger.info(f"Order {order.order_id} status updated to Out for Delivery.")
        elif delivery_status == 'delivered' and order.status != 'Completed':
            order.status = 'Completed'
            order.save()
            logger.info(f"Order {order.order_id} status updated to Completed due to delivery status change.")