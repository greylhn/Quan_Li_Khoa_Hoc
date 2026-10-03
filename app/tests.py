from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .models import Course


class CourseAdminAddTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )
        self.instructor = user_model.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='test-password',
            role=user_model.Role.INSTRUCTOR,
        )

    def test_admin_can_add_course_without_price(self):
        request = RequestFactory().get('/admin/app/course/add/')
        request.user = self.admin
        course_admin = admin.site._registry[Course]
        form_class = course_admin.get_form(request)
        form = form_class(
            data={
                'title': 'Test Course',
                'slug': 'test-course',
                'description': 'A course description',
                'instructor': str(self.instructor.pk),
            }
        )

        self.assertNotIn('price', form.fields)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertTrue(Course.objects.filter(slug='test-course').exists())
