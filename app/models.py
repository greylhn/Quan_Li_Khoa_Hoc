from django.db import models
<<<<<<< HEAD
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.forms import UserCreationForm
=======
from django.contrib.auth.models import AbstractUser
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106

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
<<<<<<< HEAD
# DANH MUC 
class Category (models.Model):
    name = models.CharField(max_length=100, unique=True,verbose_name="Ten danh muc")
    slug = models.SlugField(max_length=100,unique=True)
    description = models.TextField(blank=True,null=True,verbose_name="Mo ta")
    class Meta :
        verbose_name_plural = "Categories"
    def __str__(self):
        return self.name 
=======
#DANH MUC
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True,blank=True)
    parent = models.ForeignKey('self',on_delete=models.CASCADE,null=True,blank=True,related_name='subcategories')
    class Meta :
        verbose_name_plural = "Categories"
    def __str__(self):
        return self.name
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106
# KHOA HOC
class Course(models.Model):
    # tieu de 
    title = models.CharField(max_length=200,verbose_name="Tên Khóa Học")
    # slug 
    slug = models.SlugField(max_length=200,unique=True)
    description = models.TextField(verbose_name="Mô tả chi tiết")
    price = models.DecimalField(max_digits=10,decimal_places=2,default=0.00,verbose_name="Gia (VND)")
    thumbnail = models.ImageField(null=True,blank=True)
<<<<<<< HEAD
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='courses_created',
        limit_choices_to={'role':User.Role.INSTRUCTOR},
        verbose_name="Giang Vien"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        related_name='courses',
        verbose_name="Danh muc"
    )
    is_published = models.BooleanField(default=False,verbose_name="Da xuat Ban")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

# CHUONG HOC 
class Chapter (models.Model) :
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='chapters'
    )
    title = models.CharField(max_length=200,verbose_name="Ten Chuong")
    order = models.PositiveIntegerField(default=1,verbose_name="Thu tu hien thi")
=======
# CAC MOI QUAN HE 
    instructor = models.ForeignKey(
        User,
        on_delete= models.CASCADE,
        related_name='courses_created',
        limit_choices_to={'role':User.Role.INSTRUCTOR},
        verbose_name="Giang Vien",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='courses',
        verbose_name="Danh Muc"
    )
    is_published = models.BooleanField(default=False,verbose_name="Da Xuat Ban")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title
# CHUONG HOC 
class Chapter(models.Model):
    course = models.ForeignKey(Course,on_delete=models.CASCADE,related_name='chapters')
    title = models.CharField(max_length=200,verbose_name="Tên Chương")
    order = models.PositiveIntegerField(default = 1 , verbose_name = "Thu tu hien thi")

    class Meta :
        ordering = ['order']
    def __str__(self):
        return f"{self.course.title} - {self.order}:{self.title}"
# BAI HOC 
class Lesson(models.Model):
    class Lessontype(models.TextChoices):
        VIDEO = 'VIDEO', 'Video'
        ARTICLE = 'ARTICLE', 'Bài đọc'
        DOCUMENT = 'DOCUMENT', 'Tài liệu PDF/File'
    chapter = models.ForeignKey(Chapter,on_delete=models.CASCADE,related_name='lessons')
    title = models.CharField(max_length=200,verbose_name='Ten Bai Hoc')
    lesson_type = models.CharField(max_length=10, choices=Lessontype.choices,default=Lessontype.VIDEO)

    video_url = models.URLField(blank=True,null=True,verbose_name='link bai hoc')
    content = models.TextField(blank=True,null=True,verbose_name='Noi dung van ban')
    attachment = models.FileField(blank=True,null=True,verbose_name="File dinh kem")
    order = models.PositiveIntegerField(default=1 , verbose_name="Thu tu bai hoc")
    is_preview = models.BooleanField(default= False , verbose_name="Cho Phep hoc thu")
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106

    class Meta :
        ordering = ['order']

    def __str__(self):
<<<<<<< HEAD
        return f"{self.course.title}-Chương {self.order}: {self.title}"

# BAI HOC 
class Lesson (models.Model):
    class LessonType(models.TextChoices):
        VIDEO = "VIDEO",'Video',
        ARTICLE = "ARTICLE","Bai doc"
        DOCUMENT = "DOCUMENT","Tai lieu PDF/FILE"
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name="lessons"
    )
    title = models.CharField(max_length=200,verbose_name="Ten bai hoc")
    lesson_type = models.CharField(
        max_length=10,
        choices= LessonType.choices,
        default=LessonType.VIDEO
    )
    video_url = models.URLField(blank=True,null=True,verbose_name="Link VIDEO (...)")
    content = models.TextField(blank=True,null=True,verbose_name="Noi dung van ban")
    attachment = models.FileField(upload_to="lessons/documents/",blank=True,null=True,verbose_name="File dinh kem")
    order = models.PositiveIntegerField(default=1,verbose_name="Thu tu bai hoc")
    is_preview = models.BooleanField(default=False,verbose_name='Cho phep hoc thu')

    class Meta:
        ordering = ['order']
    def __str__(self):
        return f"{self.chapter.title}-Bài {self.order}: {self.title}"
=======
        return f"{self.chapter.title}-Bai {self.order}: {self.title}"
>>>>>>> 8360f940b388aad6f6f9dde40edf97520ced9106
