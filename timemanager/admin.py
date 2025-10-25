from django.contrib import admin
from .models import AttendanceRecord

class AttendanceRecordAdmin(admin.ModelAdmin):
    pass

admin.site.register(AttendanceRecord, AttendanceRecordAdmin)