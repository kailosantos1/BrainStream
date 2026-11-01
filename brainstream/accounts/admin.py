from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Estudante


@admin.register(Estudante)
class EstudanteAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'nome', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'nome')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados pessoais', {'fields': ('nome',)}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'nome', 'password1', 'password2')}),
    )
