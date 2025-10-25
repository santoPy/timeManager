from django.db import models

# Create your models here.
from django.db import models

# Optional: For future database storage of attendance records
class AttendanceRecord(models.Model):
    employee_code = models.CharField(max_length=50)
    employee_name = models.CharField(max_length=200)
    office_date = models.DateField()
    event_date = models.DateTimeField()
    description = models.CharField(max_length=200)
    entry_status = models.CharField(max_length=50)

    class Meta:
        ordering = ['event_date']

    def __str__(self):
        return f"{self.employee_code} - {self.event_date}"
