from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from .models import Course


class CourseAdminAddTests(TestCase):
    def setUp(self):
        user_model_class = get_user_model()
        self.admin = user_model_class.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='test-password',
        )
        self.instructor = user_model_class.objects.create_user(
            username='instructor',
            email='instructor@example.com',
            password='test-password',
            role=user_model_class.Role.INSTRUCTOR,
        )

    def test_admin_can_add_course_without_price(self):
        admin_request = RequestFactory().get('/admin/app/course/add/')
        admin_request.user = self.admin
        course_admin = admin.site._registry[Course]
        course_form_class = course_admin.get_form(admin_request)
        course_form = course_form_class(
            data={
                'title': 'Test Course',
                'slug': 'test-course',
                'description': 'A course description',
                'instructor': str(self.instructor.pk),
            }
        )

        self.assertNotIn('price', course_form.fields)
        self.assertTrue(course_form.is_valid(), course_form.errors)
        course_form.save()
        self.assertTrue(Course.objects.filter(slug='test-course').exists())
