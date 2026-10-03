from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_rename_is_published_course_ished_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='course',
            name='price',
        ),
    ]
