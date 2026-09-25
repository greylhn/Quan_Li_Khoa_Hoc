from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Course, Chapter, Lesson
from .models import*
# Register your models here.
admin.site.register(Category)
admin.site.register(Course)
admin.site.register(Chapter)
admin.site.register(Lesson)

@admin.register(User)
class CustomUserAdmin(UserAdmin) :
    #Hien thi cac cot trong danh sach user
    list_display = ('username','email' ,'first_name','last_name','role','is_staff')
    list_filter = ('role','is_staff','is_superuser')

    filedsets = UserAdmin.fieldsets + (
        ('Thong tin bo sung', {'fileld' : ('role' , 'avatar' , 'bio')})
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
            ('Thông tin bổ sung', {
                'fields': ('email', 'role', 'avatar', 'bio'),
            }),
        )