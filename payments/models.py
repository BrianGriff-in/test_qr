from django.db import models
import uuid


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PAID    = 'paid'
    STATUS_FAILED  = 'failed'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID,    'Paid'),
        (STATUS_FAILED,  'Failed'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference       = models.CharField(max_length=50, unique=True)
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    currency        = models.CharField(max_length=10, default='USD')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    qr_string       = models.TextField(blank=True)
    qr_md5          = models.CharField(max_length=64, blank=True)
    qr_image_base64 = models.TextField(blank=True)
    webhook_payload = models.JSONField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    paid_at         = models.DateTimeField(null=True, blank=True)
    expired_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.reference} — {self.get_status_display()} — ${self.amount}'

    @property
    def is_paid(self):
        return self.status == self.STATUS_PAID

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_expired(self):
        return self.status == self.STATUS_EXPIRED


class WebhookLog(models.Model):
    order           = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_logs')
    raw_body        = models.TextField()
    signature       = models.CharField(max_length=255, blank=True)
    signature_valid = models.BooleanField(default=False)
    payload         = models.JSONField(null=True, blank=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'valid' if self.signature_valid else 'invalid'
        return f'WebhookLog [{status}] — {self.created_at:%Y-%m-%d %H:%M:%S}'