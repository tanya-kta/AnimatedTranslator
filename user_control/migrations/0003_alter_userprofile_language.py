# Generated by Django 4.2 on 2023-05-05 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_control', '0002_userprofile_language_alter_userprofile_about_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='language',
            field=models.CharField(max_length=100),
        ),
    ]
