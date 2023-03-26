from django.urls import path

from . import views

urlpatterns = [
    path('trigger/', views.ReportTriggerView.as_view(), name='trigger'),
    path('get_report/', views.ReportView.as_view(), name='get_report'),
]
