from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('',                                        views.checkout,              name='checkout'),
    path('payment/<str:reference>/',                views.payment_page,          name='payment_page'),
    path('payment/success/<str:reference>/',        views.payment_success,       name='payment_success'),
    path('payment/failed/<str:reference>/',         views.payment_failed,        name='payment_failed'),
    path('api/payment/status/<str:reference>/',     views.payment_status,        name='payment_status'),
    path('webhooks/khqr/',                          views.khqr_webhook,          name='khqr_webhook'),
    path('dev/simulate/<str:reference>/',           views.dev_simulate_payment,  name='simulate_payment'),
    path('dev/expire/<str:reference>/',             views.dev_expire_payment,    name='dev_expire'),
    path('dev/webhook-logs/',                       views.dev_webhook_logs,      name='dev_webhook_logs'),
    path('dev/check-transaction/<str:reference>/', views.dev_check_transaction, name='dev_check_transaction'),
    path('dev/bakong-methods/', views.dev_bakong_methods, name='dev_bakong_methods'),
]