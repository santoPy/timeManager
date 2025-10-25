from django.urls import path
from . import views

app_name = 'timemanager'

urlpatterns = [
    path('', views.index, name='index'),
    path('calculate/', views.calculate_time, name='calculate'),
]
