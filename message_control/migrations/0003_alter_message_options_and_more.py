# Generated by Django 4.2 on 2023-05-07 22:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('message_control', '0002_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='message',
            options={'ordering': ('-created_at',)},
        ),
        migrations.AlterModelOptions(
            name='messageattachment',
            options={'ordering': ('-created_at',)},
        ),
    ]
