from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.index, name='index'),
    path('regional/', views.regional, name='regional'),
    path('demographics/', views.demographics, name='demographics'),
    path('correlation/', views.correlation, name='correlation'),
    path('patterns/', views.patterns, name='patterns'),
    path('performance/', views.performance, name='performance'),
    path('view_data/', views.view_data, name='view_data'),
]
