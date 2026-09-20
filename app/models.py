from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.forms import UserCreationForm

# Create your models here.
# 3 vai tro trong he thong 
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Quan Tri Vien' # admin
        INSTRUCTOR = 'INSTRUCTOR' , 'Giang Vien'
        STUDENT = 'STUDENT' , 'Hoc Sinh'
    role = models.CharField(max_length=20,choices=Role.choices,default=Role.STUDENT)
    avatar = models.ImageField(null = True,blank=True)
    bio = models.TextField(blank=True,null=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return f"{self.username}{self.get_role_display()}"
# KHOA HOC
class Course(models.Model):
    # tieu de 
    title = models.CharField(max_length=200,verbose_name="Tên Khóa Học")
    # slug 
    slug = models.SlugField(max_length=200,unique=True)
    description = models.TextField(verbose_name="Mô tả chi tiết")
    price = models.DecimalField(max_digits=10,decimal_places=2,default=0.00,verbose_name="Gia (VND)")
    thumbnail = models.ImageField(null=True,blank=True)