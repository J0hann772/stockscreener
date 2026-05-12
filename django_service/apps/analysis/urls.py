from django.urls import path
from . import views

urlpatterns = [
    path('run/', views.run_analysis, name='analysis_run'),
    path('charts/', views.charts_view, name='analysis_charts'),
    path('api/run/', views.api_run_analysis, name='analysis_api_run'),
    path('api/status/', views.api_status_analysis, name='analysis_api_status'),
    path('api/analyze-single/', views.api_analyze_single, name='analysis_api_analyze_single'),
    path('history/clear/', views.clear_history, name='analysis_clear_history'),
    path('history/<int:pk>/delete/', views.delete_run, name='analysis_delete_run'),
]