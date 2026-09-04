
from django.contrib import admin
from django.urls import path
from main import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = [

    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/redirect/', views.post_login_redirect, name='post_login_redirect'),
    path('search/', views.start_search, name='start_search'),
    path('cars/', views.car_list, name='car_list'),
    path('cars/<int:pk>/', views.car_detail, name='car_details'),
    path('cars/available/', views.available_cars, name='available_cars'),
    path('branches/dashboard/', views.dashboard, name='dashboard'),
    path('cars/<int:pk>/reserve/', views.rezervation, name='rezervation'),
    path('reservations/<int:pk>/teslim/', views.checkout, name='checkout'),
    path('reservations/<int:pk>/iade/', views.checkin, name='checkin'),
    path('branches/reservations/', views.branch_reservations, name='branch_reservations'),
    path('reservations/mine/', views.my_reservations, name='my_reservations'),
    path('reservations/<int:pk>/iptal/', views.cancel_reservation, name='cancel_reservation'),
    path('cars/transfer/', views.transfer_car, name='transfer_car'),
]
#geliştirme ortamında yüklenen medya dosyalarını tarayıcıda görüntülüyor
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

