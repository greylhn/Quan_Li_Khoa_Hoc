from django.urls import path
from .import views
urlpatterns = [
    path('', views.home),
    path('login/',views.loginPage,name='login'),
    path('register/',views.registerPage,name='register'),
    path('term/',views.term,name='term'),
]
