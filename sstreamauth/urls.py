from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.Main.as_view(), name='auth.main'),
    path('join/', views.Create.as_view(), name='auth:create'),
    path('login/', views.Login.as_view(), name='auth.login'),
    # path('captcha/', include('captcha.urls')),
    path(
        'redirect/<path:path>/',
        views.Redirect.as_view(),
        name='auth.redirect'
    )
]
