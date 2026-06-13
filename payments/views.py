import hashlib
import hmac
import io
import json
import uuid
import base64
import logging

import time
import qrcode
from bakong_khqr import KHQR

from django.conf        import settings
from django.http        import JsonResponse
from django.shortcuts   import render, redirect, get_object_or_404
from django.utils       import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
        
from .models import Order, WebhookLog

logger = logging.getLogger(__name__)


def _generate_qr_base64(data: str) -> str:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img    = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def _generate_reference() -> str:
    return f'ORD-{uuid.uuid4().hex[:8].upper()}'



def _build_khqr(order: Order) -> dict:
    khqr = KHQR(settings.BAKONG_TOKEN)
    qr_string = khqr.create_qr(
        bank_account   = settings.KHQR_BANK_ACCOUNT,
        merchant_name  = settings.KHQR_MERCHANT_NAME,
        merchant_city  = settings.KHQR_MERCHANT_CITY,
        amount         = float(order.amount),
        currency       = order.currency,
        store_label    = 'Store',
        phone_number   = settings.KHQR_PHONE_NUMBER,
        bill_number    = f'{order.reference}-{int(time.time())}',  # ← unique every time
        terminal_label = 'POS-01',
        static         = False,
    )
    qr_md5 = khqr.generate_md5(qr_string)
    return {'qr_string': qr_string, 'qr_md5': qr_md5}

def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    if not signature:
        return False
    secret   = settings.KHQR_WEBHOOK_SECRET.encode()
    expected = hmac.new(secret, body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@require_http_methods(['GET', 'POST'])
def checkout(request):
    products = [
        {'name': 'Organic Rice 5kg', 'price': 0.10},
    ]
    total = sum(p['price'] for p in products)

    if request.method == 'POST':
        order = Order.objects.create(
            reference = _generate_reference(),
            amount    = total,
            currency  = 'USD',
            status    = Order.STATUS_PENDING,
        )
        try:
            khqr_data             = _build_khqr(order)
            order.qr_string       = khqr_data['qr_string']
            order.qr_md5          = khqr_data['qr_md5']
            order.qr_image_base64 = _generate_qr_base64(order.qr_string)
        except Exception as e:
            logger.error('KHQR generation failed for %s: %s', order.reference, e)

        order.save()
        return redirect('payments:payment_page', reference=order.reference)

    return render(request, 'payments/checkout.html', {'products': products, 'total': total})


@require_http_methods(['GET'])
def payment_page(request, reference):
    order = get_object_or_404(Order, reference=reference)
    if order.is_paid:
        return redirect('payments:payment_success', reference=reference)
    if order.status == Order.STATUS_FAILED:
        return redirect('payments:payment_failed', reference=reference)
    return render(request, 'payments/payment.html', {'order': order, 'debug': settings.DEBUG})


@require_http_methods(['GET'])
def payment_status(request, reference):
    order = get_object_or_404(Order, reference=reference)

    def success_response():
        from django.urls import reverse
        return JsonResponse({
            'status':       order.status,
            'is_paid':      True,
            'redirect_url': request.build_absolute_uri(
                reverse('payments:payment_success', args=[order.reference])
            ),
            'reference': order.reference,
        })

    def pending_response():
        return JsonResponse({'status': order.status, 'is_paid': False, 'redirect_url': None, 'reference': order.reference})

    if order.is_paid:
        return success_response()

    age = (timezone.now() - order.created_at).total_seconds()
    if age > 600:
        return pending_response()

    if age < 10:
        return pending_response()

    if order.qr_md5 and settings.BAKONG_TOKEN:
        try:
            khqr = KHQR(settings.BAKONG_TOKEN)

            # ── KEY FIX: check if this MD5 was paid AFTER the order was created ──
            from bakong_khqr.response import ResponseCode
            result = khqr.check_transaction(order.qr_md5)

            if result and result.get('responseCode') == ResponseCode.SUCCESS:
                transaction_time = result.get('data', {}).get('createdDateMs')
                if transaction_time:
                    import datetime
                    tx_time = datetime.datetime.fromtimestamp(transaction_time / 1000, tz=datetime.timezone.utc)
                    # Only confirm if the transaction happened AFTER the order was created
                    if tx_time > order.created_at:
                        order.status  = Order.STATUS_PAID
                        order.paid_at = timezone.now()
                        order.save()
                        logger.info('Order %s marked PAID — tx time %s after order time %s', reference, tx_time, order.created_at)
                        return success_response()
                    else:
                        logger.warning('Order %s rejected — tx time %s is BEFORE order created %s', reference, tx_time, order.created_at)
                        return pending_response()

        except Exception as e:
            logger.error('Bakong check failed for %s: %s', reference, e)
            # fallback to basic check_payment
            try:
                is_paid = KHQR(settings.BAKONG_TOKEN).check_payment(order.qr_md5)
                if is_paid:
                    order.status  = Order.STATUS_PAID
                    order.paid_at = timezone.now()
                    order.save()
                    return success_response()
            except Exception as e2:
                logger.error('Bakong fallback failed for %s: %s', reference, e2)

    return pending_response()


@require_http_methods(['GET'])
def payment_success(request, reference):
    order = get_object_or_404(Order, reference=reference)
    return render(request, 'payments/success.html', {'order': order})


@require_http_methods(['GET'])
def payment_failed(request, reference):
    order = get_object_or_404(Order, reference=reference)
    return render(request, 'payments/failed.html', {'order': order})


@csrf_exempt
@require_http_methods(['POST'])
def khqr_webhook(request):
    body      = request.body
    signature = request.headers.get('X-KHQR-Signature', '')
    ip        = _get_client_ip(request)
    is_valid  = _verify_webhook_signature(body, signature)

    if not is_valid:
        WebhookLog.objects.create(raw_body=body.decode('utf-8', errors='replace'), signature=signature, signature_valid=False, ip_address=ip)
        return JsonResponse({'error': 'Invalid signature'}, status=403)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    reference = payload.get('reference') or payload.get('order_id')
    status    = payload.get('status')

    if not reference or not status:
        return JsonResponse({'error': 'Missing reference or status'}, status=400)

    try:
        order = Order.objects.get(reference=reference)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    if status == 'paid' and not order.is_paid:
        order.status          = Order.STATUS_PAID
        order.paid_at         = timezone.now()
        order.webhook_payload = payload
        order.save()
    elif status == 'failed':
        order.status          = Order.STATUS_FAILED
        order.webhook_payload = payload
        order.save()

    WebhookLog.objects.create(order=order, raw_body=body.decode('utf-8', errors='replace'), signature=signature, signature_valid=True, payload=payload, ip_address=ip)
    return JsonResponse({'ok': True, 'reference': reference})


@require_http_methods(['GET'])
def dev_simulate_payment(request, reference):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in DEBUG mode'}, status=403)
    order = get_object_or_404(Order, reference=reference)
    if order.is_paid:
        return JsonResponse({'ok': False, 'message': 'Already paid'})
    order.status          = Order.STATUS_PAID
    order.paid_at         = timezone.now()
    order.webhook_payload = {'reference': reference, 'status': 'paid', 'simulated': True}
    order.save()
    WebhookLog.objects.create(order=order, raw_body=json.dumps({'reference': reference, 'status': 'paid', 'simulated': True}), signature='simulated', signature_valid=True, payload={'reference': reference, 'status': 'paid', 'simulated': True})
    return JsonResponse({'ok': True, 'message': f'Order {reference} marked as paid (simulated)'})


@require_http_methods(['GET'])
def dev_expire_payment(request, reference):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in DEBUG mode'}, status=403)
    order            = get_object_or_404(Order, reference=reference)
    order.status     = Order.STATUS_EXPIRED
    order.expired_at = timezone.now()
    order.save()
    return JsonResponse({'ok': True, 'message': f'Order {reference} marked as expired'})


@require_http_methods(['GET'])
def dev_webhook_logs(request):
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in DEBUG mode'}, status=403)
    logs = WebhookLog.objects.select_related('order').order_by('-created_at')[:20]
    return JsonResponse({
        'count': logs.count(),
        'logs': [{'id': str(log.id), 'order_reference': log.order.reference if log.order else None, 'signature_valid': log.signature_valid, 'payload': log.payload, 'ip_address': log.ip_address, 'created_at': log.created_at.isoformat()} for log in logs],
    })