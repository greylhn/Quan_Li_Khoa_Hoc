from django.urls import path
from .import views
urlpatterns = [
    path('', views.home,name="home"),
    path('register/',views.registerPage,name='register'),
    path('login/',views.loginPage,name='login'),
    path('logout/', views.logoutPage, name='logout'),
    path('term/',views.term,name='term'),
    path('courses/',views.courses,name='courses'),
    path('detail-courses/',views.detail_courses,name='detail_courses'),
    path('learning/',views.learning,name='learning'),
    path('teacher/',views.teacher,name='teacher'),
    path('checkout/',views.checkout,name='checkout'),
]
