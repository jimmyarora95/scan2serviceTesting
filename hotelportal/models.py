from django.db import models
from website.models import Hotel

from django.core.exceptions import ValidationError   # 4.1A — Catalog models


from django.utils import timezone
from decimal import Decimal




class Room(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)       # e.g., "101"
    floor  = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    current_stay = models.ForeignKey("Stay", null=True, blank=True, on_delete=models.SET_NULL, related_name="current_room")

    class Meta:
        unique_together = ("hotel","number")

    def __str__(self):
        return f"{self.hotel.name} - Room {self.number}"

class Stay(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    room  = models.ForeignKey(Room, on_delete=models.CASCADE)
    guest_name = models.CharField(max_length=120)
    phone      = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        choices=[("CHECKED_IN","Checked In"),("CHECKED_OUT","Checked Out")],
        default="CHECKED_IN"
    )
    check_in_at  = models.DateTimeField(auto_now_add=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    running_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 🔸 not in basic Django, but needed for Scan2Service

    def __str__(self):
        return f"Stay {self.id} — {self.hotel.name} / Room {self.room.number}"
    



# ----------------------------
# 4.1A — Catalog models
# ----------------------------


class Category(models.Model):
    KIND_CHOICES = (
        ("FOOD", "Food"),
        ("SERVICE", "Service"),
    )
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="SERVICE", db_index=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    position = models.PositiveIntegerField(default=0, help_text="Ordering within same parent/kind")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (
            ("hotel", "name", "parent"),
        )
        ordering = ("position", "name")

    def __str__(self):
        path = f"{self.parent.name} / {self.name}" if self.parent else self.name
        return f"[{self.kind}] {path}"

    def clean(self):
        # Disallow parent-child across different kinds
        if self.parent and self.parent.kind != self.kind:
            raise ValidationError("Parent and child categories must be the same kind.")


class ImageAsset(models.Model):
    # Reusable photo library for items
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=120)
    file = models.ImageField(upload_to="item_photos/")  # MEDIA_ROOT/item_photos/...
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("hotel", "name"),)
        ordering = ("name",)

    def __str__(self):
        return self.name


class Item(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 0 allowed (free services)
    unit = models.CharField(max_length=20, blank=True, help_text="e.g., plate, item, kg")
    description = models.TextField(blank=True)
    image = models.ForeignKey(ImageAsset, null=True, blank=True, on_delete=models.SET_NULL)
    is_available = models.BooleanField(default=True, db_index=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("hotel", "category", "name"),)
        indexes = [
            models.Index(fields=["hotel", "is_available"]),
            models.Index(fields=["hotel", "category", "is_available"]),
        ]
        ordering = ("position", "name")

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def clean(self):
        # Safety: item.hotel must match category.hotel
        if self.category and self.hotel_id != self.category.hotel_id:
            raise ValidationError("Item.hotel must match Item.category.hotel")


# 4.4A — Cart models
class Cart(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, db_index=True)
    room  = models.ForeignKey(Room,  on_delete=models.CASCADE, db_index=True)
    stay  = models.ForeignKey("Stay", on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=12, default="DRAFT")  # DRAFT → (Day 5: SUBMITTED→REQUEST)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("hotel", "room", "stay", "status"),)

    def __str__(self):
        return f"Cart #{self.id} — {self.hotel.name} R{self.room.number} ({self.status})"


class CartItem(models.Model):
    cart  = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    item  = models.ForeignKey(Item, on_delete=models.PROTECT)  # don’t lose line items if catalog changes
    qty   = models.PositiveIntegerField(default=1)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)  # freeze price at add-time

    class Meta:
        unique_together = (("cart", "item"),)







# 5.1 — Requests (Orders & Services)



# 5.x — Request model (FOOD + SERVICE)
class Request(models.Model):
    KIND_CHOICES = (
        ("FOOD", "Food"),
        ("SERVICE", "Service"),
    )
    STATUS_CHOICES = (
        ("NEW", "New"),
        ("ACCEPTED", "Accepted"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, db_index=True)
    room  = models.ForeignKey(Room,  on_delete=models.PROTECT, db_index=True)
    # Day-7 we’ll enforce non-null; for now allow null to match Cart
    stay  = models.ForeignKey("Stay", on_delete=models.PROTECT, null=True, blank=True, db_index=True)

    kind   = models.CharField(max_length=10, choices=KIND_CHOICES)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="NEW")

    # When kind=SERVICE, we tie the request to the exact service Item to prevent duplicates
    service_item = models.ForeignKey(
        "Item",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="service_requests",
        help_text="Only set when kind=SERVICE",
    )

    # money — start simple; taxes/service charges later
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # lifecycle timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    note = models.CharField(max_length=200, blank=True)  # optional small note

    class Meta:
        indexes = [
            models.Index(fields=["hotel", "status", "updated_at"]),
            models.Index(fields=["hotel", "created_at"]),
            models.Index(fields=["hotel", "kind", "status"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        base = f"{self.get_kind_display()} #{self.id} — R{self.room.number} — {self.get_status_display()}"
        return base

    # small guard: keep hotel consistent
    def clean(self):
        if self.room and self.room.hotel_id != self.hotel_id:
            raise ValidationError("Request.hotel must match Request.room.hotel")
        if self.stay and self.stay.hotel_id != self.hotel_id:
            raise ValidationError("Request.hotel must match Request.stay.hotel")
        # service-specific rules
        if self.kind == "SERVICE" and not self.service_item:
            raise ValidationError("Service requests must reference a service item.")
        if self.service_item and self.kind != "SERVICE":
            raise ValidationError("service_item may only be set for SERVICE kind.")
        if self.service_item and self.service_item.hotel_id != self.hotel_id:
            raise ValidationError("Request.hotel must match Request.service_item.hotel")

    # convenience transitions (called from views)
    def mark_accepted(self):
        self.status = "ACCEPTED"
        self.accepted_at = timezone.now()

    def mark_completed(self):
        self.status = "COMPLETED"
        self.completed_at = timezone.now()

    def mark_cancelled(self):
        self.status = "CANCELLED"
        self.cancelled_at = timezone.now()


class RequestLine(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="lines")
    item    = models.ForeignKey(Item, on_delete=models.PROTECT)
    name_snapshot  = models.CharField(max_length=120)
    price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    qty            = models.PositiveIntegerField(default=1)
    line_total     = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = (("request", "item"),)
        indexes = [
            models.Index(fields=["request"]),
        ]

    def __str__(self):
        return f"{self.name_snapshot} × {self.qty} (₹{self.price_snapshot})"
