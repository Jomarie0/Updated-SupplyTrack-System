from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product
from .forms import ProductForm, StockMovementForm
from django.http import JsonResponse
from apps.orders.models import Order  # adjust if needed
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models.functions import TruncMonth
from django.db.models import Sum, Count
from django.utils.timezone import now
# from .utils.forecasting import forecast_stock_demand_from_orders



# @login_required
# def admin_dashboard(request):
#     return render(request, "inventory/admin/admin_dashboard.html")

@login_required
def manager_dashboard(request):
    return render(request, "inventory/manager/manager_dashboard.html")

@login_required
def staff_dashboard(request):
    return render(request, "inventory/admin/admin_dashboard.html")


@login_required
def inventory_list(request):
    products = Product.objects.filter(is_deleted=False)

    movement_form = StockMovementForm()

    if request.method == 'POST':
        product_id = request.POST.get('product_id')  # This is the custom product ID

        # Check if a product exists with that custom product_id
        try:
            product = Product.objects.get(product_id=product_id)
            form = ProductForm(request.POST, instance=product)  # Update
        except Product.DoesNotExist:
            form = ProductForm(request.POST)  # Create new

        if form.is_valid():
            form.save()
            return redirect('inventory:inventory_list')
    else:
        form = ProductForm()  # Empty form for GET

    context = {
        'products': products,
        'form': form,
        'movement_form': movement_form,
    }
    return render(request, 'inventory/inventory_list/inventory_list.html', context)

@login_required
def archive_list(request):
    archived_products = Product.objects.filter(is_deleted=True)
    return render(request, 'inventory/inventory_list/archive_list.html', {'products': archived_products})

@csrf_exempt
def delete_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for product in Product.objects.filter(id__in=ids):
                product.delete()  # Triggers the custom delete (soft delete)
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def permanently_delete_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            Product.objects.filter(id__in=ids, is_deleted=True).delete()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)

@csrf_exempt
def restore_products(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if ids:
            for product in Product.objects.filter(id__in=ids, is_deleted=True):
                product.restore()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'no ids provided'}, status=400)
    return JsonResponse({'status': 'invalid method'}, status=405)


# ---------------------- D A S H  B O A R D ------------------------- #

def dashboard(request):
    # STOCK DATA
    products = list(Product.objects.values_list('name', flat=True))
    stock_quantities = list(Product.objects.values_list('stock_quantity', flat=True))
    product_names = Product.objects.values_list('name', flat=True).distinct()

    # SALES DATA
    sales_by_month = (
        Order.objects
        .filter(is_deleted=False, status="Completed")
        .annotate(month=TruncMonth('order_date'))
        .values('month')
        .annotate(total_sales=Sum('total_price'))
        .order_by('month')
    )

    months = [entry['month'].strftime('%b') for entry in sales_by_month]
    sales_totals = [float(entry['total_sales']) for entry in sales_by_month]

    # ORDER STATUS DATA
    order_status_counts = (
        Order.objects
        .filter(is_deleted=False)
        .values('status')
        .annotate(count=Count('id'))
    )
    status_labels = [entry['status'] for entry in order_status_counts]
    status_counts = [entry['count'] for entry in order_status_counts]

    context = {
        'products_json': json.dumps(products),
        'stock_quantities_json': json.dumps(stock_quantities),
        'months_json': json.dumps(months),
        'sales_totals_json': json.dumps(sales_totals),
        'status_labels_json': json.dumps(status_labels),
        'status_counts_json': json.dumps(status_counts),
        'product_names': product_names
    }
    return render(request, 'inventory/admin/admin_dashboard.html', context)
# forecasting area dine
# def stock_forecast_view(request, product_id):
#     graph, error = forecast_stock_demand_from_orders(product_id)
#     return render(request, 'inventory/reports/forecast.html', {
#         'graph': graph,
#         'error': error,
#         'product_id': product_id,
#     })