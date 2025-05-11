import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from apps.inventory.models import Product, StockMovement
from apps.delivery.signals import delivery_confirmed  # Import the signal
from apps.delivery.models import Delivery

logger = logging.getLogger(__name__)
_previous_order_status = {}

@receiver(pre_save, sender=Order)
def store_initial_order_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _previous_order_status[instance.pk] = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Order)
def update_inventory_on_order_change(sender, instance, created, **kwargs):
    product = instance.product
    quantity = instance.quantity
    current_status = instance.status

    if not created:
        previous_status = _previous_order_status.pop(instance.pk, None)

        if previous_status != current_status:
            if current_status == "Completed" and previous_status != "Completed":
                # Logic: Order became 'Completed' from a non-'Completed' state.
                # Action: Decrease stock.
                product.stock_quantity -= quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='OUT',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} marked as Completed. Stock decreased.")

            elif current_status == "Canceled" and previous_status == "Completed":
                # Logic: Order changed from 'Completed' to 'Canceled'.
                # Action: Increase stock.
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} marked as Canceled from Completed. Stock increased.")

            elif current_status == "Canceled" and previous_status != "Completed":
                # Logic: Order became 'Canceled' from a non-'Completed' state.
                # Action: No stock change (stock was not decreased yet).
                logger.info(f"Order {instance.order_id} marked as Canceled from {previous_status} (no stock change).")

            elif previous_status == "Completed" and current_status == "Pending":
                # Logic: Order changed from 'Completed' back to 'Pending'.
                # Action: Increase stock (as it was decreased on completion).
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} changed from Completed to Pending. Stock increased.")

            elif previous_status == "Completed" and current_status not in ["Completed", "Failed", "Returned", "Delivery Failed"]:
                # Logic: Order changed from 'Completed' to another intermediate status.
                # Action: Increase stock (as it was decreased on completion).
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} changed from Completed to {current_status}. Stock increased.")

            elif current_status in ["Failed", "Returned", "Delivery Failed"] and previous_status == "Completed":
                # Logic: Order went from 'Completed' to a final/failure state after completion.
                # Action: Increase stock (as the product was not successfully sold).
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} marked as {current_status} from Completed. Stock increased.")

            elif current_status in ["Failed", "Returned"] and previous_status == "Delivery Failed":
                # Logic: Order went from 'Delivery Failed' to 'Failed' or 'Returned'.
                # Action: Increase stock (as the product was not successfully sold).
                product.stock_quantity += quantity
                product.save()
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                )
                logger.info(f"Order {instance.order_id} marked as {current_status} from Delivery Failed. Stock increased.")

            elif current_status in ["Failed", "Returned", "Delivery Failed"] and previous_status not in ["Completed", "Delivery Failed"]:
                # Logic: Order reached a final/failure state without being 'Completed'.
                # Action: No stock change (stock was not decreased).
                logger.info(f"Order {instance.order_id} marked as {current_status} from {previous_status} (no stock change).")

            elif current_status == "Pending" and previous_status != "Completed":
                # Logic: Order is in 'Pending' state and wasn't 'Completed' before.
                # Action: No stock change (stock is decreased only on completion).
                logger.info(f"Order {instance.order_id} is now Pending from {previous_status} (no stock change).")

            elif current_status == "Out for Delivery" and previous_status != "Completed":
                # Logic: Order is 'Out for Delivery' and wasn't 'Completed' before.
                # Action: No stock change (stock is decreased only on completion).
                logger.info(f"Order {instance.order_id} is now Out for Delivery from {previous_status} (no stock change).")


@receiver(delivery_confirmed, sender='apps.delivery.models.Delivery')
def order_delivery_confirmed(sender, order, **kwargs):
    logger.info("order_delivery_confirmed signal receiver CALLED!")
    logger.info(f"Delivery confirmed for Order: {order.order_id}. Updating order status to 'Completed'.")
    order.status = 'Completed'
    order.save()
    logger.info(f"Order: {order.order_id} status AFTER SAVE: {order.status}")  # Added this
    logger.info(f"Order: {order.order_id} status updated to 'Completed'. Post-save signal will now handle inventory.")

@receiver(post_save, sender=Order)
def create_delivery_on_order_creation(sender, instance, created, **kwargs):
    if created:
        Delivery.objects.create(order=instance)
        logger.info(f"Delivery record created for new Order: {instance.order_id}")
