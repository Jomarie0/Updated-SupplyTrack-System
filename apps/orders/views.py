from django.shortcuts import render, redirect
from .models import Product, Order
from .forms import OrderForm
from apps.inventory.models import Product
from apps.orders.models import Order

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import random
import string
from django.utils import timezone

from django.utils.timezone import now
from django.db.models.functions import TruncMonth
from django.db.models import Sum
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
from datetime import timedelta
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from apps.inventory.models import DemandCheckLog
from django.contrib import messages



def generate_unique_order_id():
    from .models import Order
    while True:
        order_id = 'ORD' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Order.objects.filter(order_id=order_id).exists():
            return order_id

def order_list(request):
    form = OrderForm()

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        if order_id:
            try:
                existing_order = Order.objects.get(order_id=order_id)
                form = OrderForm(request.POST, instance=existing_order)
            except Order.DoesNotExist:
                form = OrderForm(request.POST)
        else:
            form = OrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)
            if not order.order_id:
                order.order_id = generate_unique_order_id()
            messages.success(request, f"Order {order.order_id}, {order.product}, {order.quantity}, {order.total_price} successfully added!")
            order.save()
            # messages.success(request, f"Delivery created for Order {order.order_id}.")

            return redirect('orders:order_list')



    orders = Order.objects.filter(is_deleted=False)

    context = {
        'orders': orders,
        'form': form,
        'products': Product.objects.filter(is_deleted=False)

    }
    return render(request, 'orders/orders_list.html', context)

def archived_orders(request):
    archived = Order.objects.filter(is_deleted=True)
    return render(request, 'orders/archived_orders.html', {'archived_orders': archived})

# @csrf_exempt
# def delete_orders(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             order_ids_to_delete = data.get('ids', [])
#             Order.objects.filter(order_id__in=order_ids_to_delete).delete()
#             return JsonResponse({'success': True})
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)})
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def delete_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids_to_delete = data.get('ids', [])
            for order in Order.objects.filter(order_id__in=order_ids_to_delete):
                order.delete()  # calls soft delete
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def permanently_delete_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids = data.get('ids', [])
            Order.objects.filter(order_id__in=order_ids, is_deleted=True).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@csrf_exempt
def restore_orders(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_ids = data.get('ids', [])
            for order in Order.objects.filter(order_id__in=order_ids, is_deleted=True):
                order.restore()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# API's dine





#  restock notif naman dine

# def restock_notifications_api(request):
#     logs = DemandCheckLog.objects.filter(restock_needed=True).order_by('-created_at')[:5]  # limit recent 5 notifications
#     data = [{
#         'product_name': log.product.name,
#         'forecasted_quantity': log.forecasted_quantity,
#         'current_stock': log.current_stock,
#         'logged_at': log.created_at.strftime("%Y-%m-%d %H:%M"),
#     } for log in logs]

#     return JsonResponse(data, safe=False)
