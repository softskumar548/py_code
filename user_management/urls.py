from django.urls import path
from .views import home, login_view, custom_logout, dashboard, superuser_dashboard, public_feedback_page, create_agent, create_client, view_agent, view_client, edit_agent, edit_client, agent_dashboard, client_dashboard, thank_you_page

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', custom_logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('superuser-dashboard/', superuser_dashboard, name='superuser_dashboard'),
    path('agent-dashboard/', agent_dashboard, name='agent_dashboard'),
    path('client-dashboard/', client_dashboard, name='client_dashboard'),
    path('create-agent/', create_agent, name='create_agent'),
    path('create-client/', create_client, name='create_client'),
    path('view-agent/<int:agent_id>/', view_agent, name='view_agent'),
    path('view-client/<int:client_id>/', view_client, name='view_client'),
    path('edit-agent/<int:agent_id>/', edit_agent, name='edit_agent'),
    path('edit-client/<int:client_id>/', edit_client, name='edit_client'),
    path('<slug:unique_url_path>/', public_feedback_page, name='public_feedback_page'),
    path('thank-you/<slug:unique_url_path>/', thank_you_page, name='thank_you_page'),
]
