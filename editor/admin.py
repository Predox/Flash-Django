from django.contrib import admin
from .models import Preset, ProcessedImage, IALog

@admin.register(Preset)
class PresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'user')

@admin.register(ProcessedImage)
class ProcessedImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'operation', 'created_at')

@admin.register(IALog)
class IALogAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'image', 'status', 'elapsed_ms', 'created_at')
