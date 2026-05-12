from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [

    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('howto/', TemplateView.as_view(template_name='howto.html'), name='howto'),
    path('auth/', include('apps.users.urls')),
    path('tickers/', include('apps.tickers.urls')),
    path('strategies/', include('apps.strategies.urls')),
    path('analysis/', include('apps.analysis.urls')),
]