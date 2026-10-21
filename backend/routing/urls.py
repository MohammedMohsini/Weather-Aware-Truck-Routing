from django.urls import path

from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('geocode/', views.geocode, name='geocode'),
    path('analyze/', views.analyze, name='analyze'),
    path('heatmap/', views.heatmap, name='heatmap'),
]
