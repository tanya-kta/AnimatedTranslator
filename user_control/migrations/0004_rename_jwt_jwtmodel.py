# Generated by Django 4.2 on 2023-04-28 18:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_control', '0003_jwt'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Jwt',
            new_name='JwtModel',
        ),
    ]
