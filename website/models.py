from django.contrib.auth.models import AbstractUser
from django.db import models


class Hotel(models.Model):
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gst_number = models.CharField(max_length=30, blank=True, null=True)              # 🔸 not in basic Django, but needed for Scan2Service
    owner_name = models.CharField(max_length=100, blank=True, null=True)             # 🔸
    hotel_code = models.CharField(max_length=20, blank=True, null=True, unique=True) # 🔸
    logo = models.ImageField(upload_to="hotel_logos/", blank=True, null=True)        # 🔸
    subscription_expires_on = models.DateField(blank=True, null=True)                # 🔸
    notes = models.TextField(blank=True, null=True)                                  # 🔸
    status = models.CharField(
        max_length=20,
        choices=[("ACTIVE","Active"),("PAUSED","Paused"),("DISABLED","Disabled")],
        default="ACTIVE",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.city})" if self.city else self.name


class User(AbstractUser):
    class Roles(models.TextChoices):
        PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Admin"
        HOTEL_ADMIN    = "HOTEL_ADMIN", "Hotel Admin"
        STAFF          = "STAFF", "Staff"
        GUEST          = "GUEST", "Guest"

    role  = models.CharField(max_length=20, choices=Roles.choices, default=Roles.HOTEL_ADMIN)
    hotel = models.ForeignKey(Hotel, null=True, blank=True, on_delete=models.SET_NULL)

    def is_platform_admin(self): return self.role == self.Roles.PLATFORM_ADMIN
    def is_hotel_admin(self):    return self.role == self.Roles.HOTEL_ADMIN
    def is_staff_user(self):     return self.role == self.Roles.STAFF
