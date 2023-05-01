from django.contrib import admin
from .models import CustomUser, JwtModel

admin.site.register((CustomUser, JwtModel))
