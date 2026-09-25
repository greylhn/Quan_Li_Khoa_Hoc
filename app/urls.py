from django.urls import path
from .import views
urlpatterns = [
    path('', views.home),
    path('login/',views.loginPage,name='login'),
    path('register/',views.registerPage,name='register'),
    path('term/',views.term,name='term'),
<<<<<<< HEAD
    path('courses/',views.courses,name='courses'),
    path('detail-courses/',views.detail_courses,name='detail_courses'),
    path('learning/',views.learning,name='learning'),
    path('teacher/',views.teacher,name='teacher'),
    path('checkout/',views.checkout,name='checkout'),
=======
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106
]
