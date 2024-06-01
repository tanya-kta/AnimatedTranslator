from django.contrib import admin
from .models import CustomUser, JwtModel, Favorite

admin.site.register((CustomUser, JwtModel, Favorite))
