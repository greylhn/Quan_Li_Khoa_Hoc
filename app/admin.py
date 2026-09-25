from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Course, Chapter, Lesson
<<<<<<< HEAD
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
=======

# Đăng ký User Custom
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin bổ sung', {'fields': ('role', 'avatar', 'bio')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')

# Đăng ký Category với tính năng tự tạo slug
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'parent')
    prepopulated_fields = {'slug': ('name',)}

# Đăng ký các model còn lại
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'category', 'price', 'is_published')
    prepopulated_fields = {'slug': ('title',)}

admin.site.register(Chapter)
admin.site.register(Lesson)
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106
