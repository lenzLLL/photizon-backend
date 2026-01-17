from django.db import models, transaction, IntegrityError
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.apps import apps
import uuid
# -----------------------------------------------------
# Church Model (défini en premier pour éviter les erreurs)
# -----------------------------------------------------

class Church(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "En attente"),
        ("APPROVED", "Approuvée"),
        ("REJECTED", "Rejetée"),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        indexes = [
        models.Index(fields=["status"]),
        models.Index(fields=["country", "city"]),
        models.Index(fields=["is_public"]),
       ]
    # Identification
    code = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
        default=1
    )
    title = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(blank=True,max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    lang = models.CharField(default="fr")

    # Description & branding
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=20, default="#1A73E8")
    secondary_color = models.CharField(max_length=20, default="#FFFFFF")

    # Contact info
    email = models.EmailField(blank=True, null=True)
    # Support up to four phone numbers for an eglise
    phone_number_1 = models.CharField(max_length=20, blank=True, null=True)
    phone_number_2 = models.CharField(max_length=20, blank=True, null=True)
    phone_number_3 = models.CharField(max_length=20, blank=True, null=True)
    phone_number_4 = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    whatsapp_phone = models.TextField(max_length=500, blank=True, null=True)
    doc_url = models.URLField(max_length=500, default="")

    # Social media
    tiktok_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    youtube_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)

    # Location
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    longitude = models.FloatField(default=0.0)
    latitude = models.FloatField(default=0.0)

    # Stats
    members_count = models.PositiveIntegerField(default=0)
    admins_count = models.PositiveIntegerField(default=0)
    profile_views = models.PositiveIntegerField(default=0)

    # Seats & operations
    seats = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    look_actuality = models.BooleanField(default=False)

    # Subscription SaaS
    is_active_subscription = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    # Later FK added from User model
    # owner = ...
    parent = models.ForeignKey(
    "self",
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name="sub_churches"
    )
    
    @property
    def phone_number(self):
        """Backward-compatible single phone_number property: first non-empty number."""
        for n in (self.phone_number_1, self.phone_number_2, self.phone_number_3, self.phone_number_4):
            if n:
                return n
        return None

    def phone_numbers(self):
        """Return a list of phone numbers (non-empty)."""
        return [n for n in (self.phone_number_1, self.phone_number_2, self.phone_number_3, self.phone_number_4) if n]
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        if not self.code:
            # Get all churches with code, sort descending, take first
            existing = Church.objects.filter(code__isnull=False).values_list('code', flat=True).order_by('-code')
            
            if existing:
                max_code = existing[0]
                self.code = max_code + 1
            else:
                self.code = 1
        
        # Save with retry logic for conflicts
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
                return  # Success!
            except IntegrityError:
                if attempt == max_attempts - 1:
                    raise
                # Retry with next code
                if not self.code:
                    existing = Church.objects.filter(code__isnull=False).values_list('code', flat=True).order_by('-code')
                    self.code = (existing[0] + 1) if existing else 1
                else:
                    self.code = self.code + 1
    def __str__(self):
        return self.title


# -----------------------------------------------------
# User Manager
# -----------------------------------------------------

class UserManager(BaseUserManager):
    def create_user(self, phone_number, **extra_fields):
        if not phone_number:
            raise ValueError("Le numéro de téléphone doit être fourni")

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_unusable_password()   # pas de mot de passe pour OTP WhatsApp
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(phone_number, **extra_fields)


# -----------------------------------------------------
# User Model
# -----------------------------------------------------

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=50, unique=True, db_index=True)
    picture_url = models.URLField(blank=True, null=True)
    ROLE_CHOICES = [
        ("SADMIN", "Sadmin"),
        ("USER", "User"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="USER", db_index=True)

    # un user peut appartenir à une église → ForeignKey
    current_church = models.ForeignKey(
        Church,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members"
    )
    longitude = models.FloatField(default=0.0)
    latitude = models.FloatField(default=0.0)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=250, blank=True)
    email = models.CharField(max_length=250, blank=True,unique=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # indispensable pour l'admin Django
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []
    objects = UserManager()
    def __str__(self):
        return f"{self.phone_number} ({self.role})"


# -----------------------------------------------------
# Ajout du owner *après* la définition du User
# -----------------------------------------------------

Church.add_to_class(
    "owner",
    models.ForeignKey(
        User,
            on_delete=models.SET_NULL,
        related_name="owners_church",
        null=True,
        blank=True
    )
)

class Content(models.Model):
    TYPE_CHOICES = [
        ("ARTICLE", "Article"),
        ("AUDIO", "Audio"),
        ("EVENT", "Event"),
        ("VIDEO", "Video"),
        ("POST", "Short"),
        ("BOOK","Book")
    ]

    DELIVERY_CHOICES = [
        ("DIGITAL", "Numérique"),
        ("PHYSICAL", "Physique"),
    ]

    church = models.ForeignKey("Church", on_delete=models.CASCADE)
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default="DIGITAL")
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
     
    title = models.CharField(max_length=250)
    phone = models.CharField(max_length=250,null=True, blank=True)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True, null=True)

    # For media (optional fields depending on type)
    audio_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    file = models.URLField(blank=True, null=True)

    # Event-specific fields
    start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    end_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=250, blank=True)
    is_paid = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="XAF")
    # Flexibility
    metadata = models.JSONField(default=dict)

    # Event/ticketing fields
    capacity = models.PositiveIntegerField(null=True, blank=True)
    tickets_sold = models.PositiveIntegerField(default=0)
    allow_ticket_sales = models.BooleanField(default=False)

    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True)

    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    published = models.BooleanField(default=True)

    # Ticket tiers stored directly on Content (prix et quantités par type)
    # Exemple: classic, vip, premium
    has_ticket_tiers = models.BooleanField(default=False)
    classic_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    classic_quantity = models.PositiveIntegerField(null=True, blank=True)
    vip_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vip_quantity = models.PositiveIntegerField(null=True, blank=True)
    premium_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    premium_quantity = models.PositiveIntegerField(null=True, blank=True)


    # dans class Content
   
    def save(self, *args, **kwargs):
        # auto-generate slug if missing
        if not self.slug and self.title:
            self.slug = slugify(self.title)[:120]

        # validate ticket counts vs capacity
        # existing tickets_sold vs capacity check
        if self.capacity is not None and self.tickets_sold is not None:
            if self.tickets_sold > self.capacity:
                raise ValidationError("tickets_sold cannot exceed capacity")

        # If ticket tiers are used, ensure their total quantity does not exceed overall capacity
        if getattr(self, "has_ticket_tiers", False) and self.capacity is not None:
            total_tier_qty = 0
            for f in ("classic_quantity", "vip_quantity", "premium_quantity"):
                v = getattr(self, f, None)
                if v:
                    total_tier_qty += int(v)
            if total_tier_qty > self.capacity:
                raise ValidationError("Sum of tier quantities exceeds content capacity")

        super().save(*args, **kwargs)

    def available_tickets(self):
        """Return remaining tickets (None means unlimited/not set)."""
        if self.capacity is None:
            return None
        return max(0, self.capacity - (self.tickets_sold or 0))

    def __str__(self):
        return f"{self.type} - {self.title}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["start_at"]), models.Index(fields=["-created_at"])]
  
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

class ContentTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

class Playlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PlaylistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

class ContentView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

class ContentLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

class OTP(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(auto_now=True)
    session_id = models.UUIDField(default=uuid.uuid4)

    def is_expired(self):
        from django.conf import settings
        expiration = settings.OTP_EXPIRATION_SECONDS
        return (timezone.now() - self.last_sent_at).total_seconds() > expiration

    def can_resend(self):
        from django.conf import settings
        cooldown = settings.OTP_SEND_COOLDOWN_SECONDS
        return (timezone.now() - self.last_sent_at).total_seconds() > cooldown

class ChurchAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Admin"),
        ("MODERATOR", "Moderator"),
        ("PASTOR", "Pastor"),
    ]

    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="admins")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="church_roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="ADMIN")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "user")

    def __str__(self):
        return f"{self.user.phone_number} @ {self.church.title} ({self.role})"

class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PLAN_CHOICES = [
        ("FREE", "Free"),
        ("STARTER", "Starter"),
        ("PRO", "Pro"),
        ("PREMUIM", "Premium"),
    ]

    church = models.OneToOneField("Church", on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=30, choices=PLAN_CHOICES, default="FREE")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # gateway data
    gateway = models.CharField(max_length=50, blank=True, null=True)  # e.g. stripe, mobilemoney
    gateway_subscription_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.church.title} - {self.plan}"

# Extend Notification to hold channel info + send status
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    NOTIF_TYPES = [
        ('OTP', 'Code OTP'),
        ('DOC_REQUEST', 'Demande de documents'),
        ('DOC_VALIDATED', 'Documents validés'),
        ('ACCOUNT_APPROVED', 'Compte activé'),
        ('INFO', 'Information'),
        ('WARNING', 'Avertissement'),
        ('ERROR', 'Erreur'),
        ("SUCCESS","Success")
    ]

    CHANNEL_CHOICES = [
        ("IN_APP", "In App"),
        ("WHATSAPP", "WhatsApp"),
        ("EMAIL", "Email")
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    eng_message = models.TextField(default="")
    eng_title = models.TextField(default="")
    type = models.CharField(max_length=20, choices=NOTIF_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default="IN_APP")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)  # store payload / gateway response

    def mark_sent(self, response_meta=None):
        self.sent = True
        self.sent_at = timezone.now()
        if response_meta:
            self.meta = response_meta
        self.save()

    def __str__(self):
        # safer if user might not have phone_number set
        phone = getattr(self.user, "phone_number", str(self.user.pk))
        return f"{phone} • {self.title}"

class Commission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    eng_name = models.CharField(max_length=255, unique=True,default="")
    logo = models.URLField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChurchCommission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ROLE_CHOICES = [
        ("MEMBER", "Member"),
        ("LEADER", "Leader"),
        ("ASSISTANT", "Assistant"),
    ]

    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="church_commissions")
    commission = models.ForeignKey("Commission", on_delete=models.CASCADE, related_name="church_links")
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="church_commissions")

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="MEMBER")

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "commission", "user")

    def __str__(self):
        return f"{self.user.phone_number} → {self.commission.name} @ {self.church.title}"

class Deny(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="denied_members")
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="denied_in_churches")
    reason = models.TextField(blank=True)
    denied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "user")

    def __str__(self):
        return f"{self.user.phone_number} denied from {self.church.title}"
    
class DonationCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

  # Une catégorie par église

    def __str__(self):
        return f"{self.name}"
    
class Donation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PAYMENT_GATEWAYS = [
        ("MOMO", "Mobile Money"),
        ("OM", "Orange Money"),
        ("CARD", "Carte Bancaire"),
        ("CASH", "Cash"),
        ("OTHER", "Autre"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="donations")
    church = models.ForeignKey(Church, on_delete=models.CASCADE, related_name="donations")
    category = models.ForeignKey(DonationCategory, on_delete=models.SET_NULL, null=True)
    withdrawed = models.BooleanField(default=False) 
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="XAF")

    gateway = models.CharField(max_length=20, choices=PAYMENT_GATEWAYS, default="CASH")
    gateway_transaction_id = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    message = models.TextField(blank=True)  # message du donateur (optionnel)
    metadata = models.JSONField(default=dict, blank=True)  # données techniques du paiement
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.phone_number} → {self.amount} {self.currency} ({self.category})"


class Payment(models.Model):
    """Unified payment record for orders and donations (for admin reconciliation).

    - Can be linked to a BookOrder or a Donation (or both/none for manual entries).
    - Stores gateway metadata and who processed the payment in the admin.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Successful"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    church = models.ForeignKey(Church, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    order = models.ForeignKey("BookOrder", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    donation = models.ForeignKey("Donation", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="XAF")

    GATEWAY_CHOICES = [
        ("MOMO", "Mobile Money"),
        ("OM", "Orange Money"),
        ("CARD", "Card"),
        ("CASH", "Cash"),
        ("OTHER", "Other"),
    ]
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default="MOMO")
    gateway_transaction_id = models.CharField(max_length=200, blank=True, null=True, db_index=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Admin who reconciled/created this payment (if any)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_payments")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["gateway_transaction_id"]), models.Index(fields=["status"])]

    def __str__(self):
        who = self.user.phone_number if self.user else (self.church.title if self.church else str(self.id))
        return f"Payment {self.id} — {who} — {self.amount} {self.currency} ({self.status})"

class BookOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PAYMENT_CHOICES = [
        ("MOMO", "Mobile Money"),
        ("OM", "Orange Money"),
        ("CARD", "Carte Bancaire"),
        ("CASH", "Cash"),
        ("OTHER", "Autre"),
    ]
    DELIVERY_CHOICES = [
        ("DIGITAL", "Numérique"),
        ("PHYSICAL", "Physique"),
    ]
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="book_orders")
    content = models.ForeignKey("Content", on_delete=models.CASCADE, related_name="book_orders")
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default="DIGITAL")
    
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    withdrawed = models.BooleanField(default=False) 
    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="CASH")
    payment_transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    shipped = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Optional delivery information for physical goods
    delivery_recipient_name = models.CharField(max_length=250, blank=True, null=True)
    delivery_address_line1 = models.CharField(max_length=250, blank=True, null=True)
    delivery_address_line2 = models.CharField(max_length=250, blank=True, null=True)
    delivery_city = models.CharField(max_length=150, blank=True, null=True)
    delivery_postal_code = models.CharField(max_length=50, blank=True, null=True)
    delivery_country = models.CharField(max_length=150, blank=True, null=True)
    delivery_phone = models.CharField(max_length=50, blank=True, null=True)
    shipping_method = models.CharField(max_length=100, blank=True, null=True)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # flag to indicate this order purchases tickets for an event
    is_ticket = models.BooleanField(default=False)
    # optional: which ticket type (if ticket types are used)
    # Backwards-compatible: keep FK but prefer `ticket_tier` which reads tiers from Content
    ticket_type = models.ForeignKey("TicketType", on_delete=models.SET_NULL, null=True, blank=True)
    # New: choose a tier stored on Content directly: CLASSIC, VIP or PREMIUM
    TIER_CHOICES = [("CLASSIC", "Classic"), ("VIP", "VIP"), ("PREMIUM", "Premium")]
    ticket_tier = models.CharField(max_length=20, choices=TIER_CHOICES, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Vérifie la disponibilité des tickets si c'est une commande de billets.
        # On utilise une transaction + select_for_update pour éviter la sur-vente.
        with transaction.atomic():
            # lock related rows
            if self.is_ticket:
                # Prefer explicit ticket_type FK if present, else use ticket_tier info on content
                if getattr(self, "ticket_type_id", None):
                    # lock the ticket type row
                    tt = TicketType.objects.select_for_update().get(pk=self.ticket_type_id)
                    if tt.quantity is not None and tt.quantity < (self.quantity or 0):
                        raise ValidationError("Not enough tickets available for the selected ticket type")
                elif getattr(self, "ticket_tier", None):
                    # lock the content row and check tier availability
                    c = Content.objects.select_for_update().get(pk=self.content_id)
                    tier = (self.ticket_tier or "").upper()
                    qty_field = {
                        "CLASSIC": "classic_quantity",
                        "VIP": "vip_quantity",
                        "PREMIUM": "premium_quantity",
                    }.get(tier)
                    if qty_field:
                        avail = getattr(c, qty_field)
                        if avail is not None and avail < (self.quantity or 0):
                            raise ValidationError("Not enough tickets available for the selected tier")
                else:
                    # lock the content row and check overall capacity
                    c = Content.objects.select_for_update().get(pk=self.content_id)
                    if c.capacity is not None and (c.capacity - (c.tickets_sold or 0)) < (self.quantity or 0):
                        raise ValidationError("Not enough tickets available for this event")

            # Calcul automatique du prix total
            unit_price = 0
            try:
                # Determine unit price from ticket_type FK, or ticket_tier on content, or content.price
                if self.is_ticket and getattr(self, "ticket_type", None):
                    unit_price = self.ticket_type.price or 0
                elif getattr(self, "ticket_tier", None) and getattr(self, "content", None):
                    tier = (self.ticket_tier or "").upper()
                    unit_price = {
                        "CLASSIC": (self.content.classic_price or 0),
                        "VIP": (self.content.vip_price or 0),
                        "PREMIUM": (self.content.premium_price or 0),
                    }.get(tier, 0)
                elif getattr(self, "content", None) and self.content.price:
                    unit_price = self.content.price
            except Exception:
                unit_price = 0
            self.total_price = (self.quantity or 0) * (unit_price or 0)
            super().save(*args, **kwargs)

    def issue_tickets(self, payment_transaction_id=None, buyer=None):
        """
        Atomically issue tickets for this order after payment confirmation.
        Returns list of created Ticket instances.
        """
        if not self.is_ticket:
            raise ValidationError("This order is not a ticket order")

        Ticket = apps.get_model("api", "Ticket")
        TicketType = apps.get_model("api", "TicketType")
        ContentModel = apps.get_model("api", "Content")

        with transaction.atomic():
            # Lock and validate availability
            if self.ticket_type_id:
                tt = TicketType.objects.select_for_update().get(pk=self.ticket_type_id)
                if tt.quantity is not None and tt.quantity < (self.quantity or 0):
                    raise ValidationError("Not enough tickets available for the selected ticket type")
            else:
                c = ContentModel.objects.select_for_update().get(pk=self.content_id)
                if c.capacity is not None and (c.capacity - (c.tickets_sold or 0)) < (self.quantity or 0):
                    raise ValidationError("Not enough tickets available for this event")

            # compute unit price
            unit_price = 0
            if self.ticket_type_id:
                tt = TicketType.objects.get(pk=self.ticket_type_id)
                unit_price = tt.price or 0
            else:
                c = ContentModel.objects.get(pk=self.content_id)
                unit_price = c.price or 0

            # create tickets
            tickets = []
            content_obj = ContentModel.objects.get(pk=self.content_id)
            buyer_user = buyer or self.user
            for _ in range(self.quantity or 0):
                t = Ticket.objects.create(
                    content=content_obj,
                    order=self,
                    ticket_type=(tt if getattr(self, "ticket_type_id", None) else None),
                    user=buyer_user,
                    price=unit_price,
                )
                tickets.append(t)

            # decrement stock and increment sold counters
            # If using ticket_type FK, decrement its quantity
            if self.ticket_type_id and tt.quantity is not None:
                TicketType.objects.filter(pk=tt.pk).update(quantity=F('quantity') - (self.quantity or 0))
            # If using ticket_tier stored on content, decrement the corresponding content tier quantity
            elif getattr(self, "ticket_tier", None):
                tier = (self.ticket_tier or "").upper()
                qty_field = {
                    "CLASSIC": "classic_quantity",
                    "VIP": "vip_quantity",
                    "PREMIUM": "premium_quantity",
                }.get(tier)
                if qty_field:
                    ContentModel.objects.filter(pk=self.content_id).update(**{
                        qty_field: F(qty_field) - (self.quantity or 0)
                    })

            # Always increment tickets_sold counter
            ContentModel.objects.filter(pk=self.content_id).update(tickets_sold=F('tickets_sold') + (self.quantity or 0))

            # update order with payment transaction id if provided
            if payment_transaction_id:
                self.payment_transaction_id = payment_transaction_id
                # update without re-running availability checks via queryset
                BookOrder = apps.get_model("api", "BookOrder")
                BookOrder.objects.filter(pk=self.pk).update(payment_transaction_id=payment_transaction_id)

            return tickets

    def __str__(self):
        return f"{self.user.phone_number} - {self.content.title} ({self.delivery_type}) x{self.quantity}"

class TicketType(models.Model):
    """Category / tariff for an event (e.g. CLASSIQUE, VIP)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey("Content", on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    # quantity=None means unlimited
    quantity = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["-created_at"])]

    class Meta:
        unique_together = ("content", "name")

    def __str__(self):
        return f"{self.content.title} — {self.name} ({self.price})"

    def available(self):
        """Return remaining tickets for this type (None means unlimited)."""
        if self.quantity is None:
            return None
        Ticket = apps.get_model("api", "Ticket")
        reserved = TicketReservation.objects.filter(ticket_type=self, expires_at__gt=timezone.now()).aggregate(sum=Sum('quantity'))['sum'] or 0
        sold = Ticket.objects.filter(ticket_type=self).count()
        return max(0, self.quantity - (reserved or 0) - sold)

class TicketReservation(models.Model):
    """Temporary reservation to hold tickets during payment window."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True)
    content = models.ForeignKey("Content", on_delete=models.CASCADE)
    ticket_type = models.ForeignKey("TicketType", on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["expires_at"])]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"Reservation {self.id} — {self.content.title} x{self.quantity}"

class Ticket(models.Model):
    """Issued ticket linked to an order. Use UUID as public identifier."""
    T_STATUS = [("NEW", "New"), ("USED", "Used"), ("CANCELLED", "Cancelled")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.ForeignKey("Content", on_delete=models.CASCADE, related_name="tickets")
    order = models.ForeignKey("BookOrder", on_delete=models.CASCADE, related_name="tickets")
    ticket_type = models.ForeignKey("TicketType", on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True)
    seat = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=T_STATUS, default="NEW")
    issued_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user"]), models.Index(fields=["status"]), models.Index(fields=["-issued_at"])]

    def __str__(self):
        ttype = self.ticket_type.name if self.ticket_type else "--"
        return f"Ticket {self.id} — {self.content.title} ({ttype})"

class Receipt(models.Model):
    """Receipt model for transactions. Can be linked to an event (Content) or standalone."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="receipts")
    
    # Optional links to specific transactions
    content = models.ForeignKey("Content", on_delete=models.SET_NULL, null=True, blank=True, related_name="receipts")    
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    description = models.TextField(blank=True)
    
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    

    class Meta:
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["church"]),
            models.Index(fields=["-issued_at"]),
        ]

    def __str__(self):
        who = self.user.phone_number if self.user else (self.church.title if self.church else "Unknown")
        return f"Receipt {self.receipt_number} — {who} — {self.amount} {self.currency}"

# =====================================================
# Chat Model
# =====================================================
class ChatRoom(models.Model):
    """Chat room for church, commission, roles, or custom member selection"""
    
    ROOM_TYPES = (
        ('CHURCH', 'Tous les membres'),
        ('OWNER', 'Propriétaires'),
        ('PASTOR', 'Pasteurs'),
        ('COMMISSION', 'Commission'),
        ('CUSTOM', 'Personnalisé'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="chat_rooms")
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='CHURCH')
    name = models.CharField(max_length=100)
    
    # Optional: for COMMISSION type
    commission = models.ForeignKey("Commission", on_delete=models.CASCADE, null=True, blank=True, related_name="chat_rooms")
    
    # Custom members (for CUSTOM type)
    members = models.ManyToManyField("User", blank=True, related_name="custom_chat_rooms")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, related_name="created_chat_rooms")

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["church", "room_type"]),
            models.Index(fields=["commission"]),
        ]

    def __str__(self):
        return f"{self.church.title} - {self.get_room_type_display()} - {self.name}"
    
    def user_has_access(self, user):
        """Check if a user has access to this room"""
        from django.db.models import Q
        
        if not user.is_authenticated:
            return False
        
        # Owners always have access to all rooms of their church
        is_owner = User.objects.filter(
            id=user.id,
            church_roles__church=self.church,
            church_roles__role='OWNER'
        ).exists()
        if is_owner:
            return True
        
        # Check based on room type
        if self.room_type == 'CHURCH':
            return user.current_church_id == self.church_id
        
        elif self.room_type == 'OWNER':
            return User.objects.filter(
                id=user.id,
                church_roles__church=self.church,
                church_roles__role='OWNER'
            ).exists()
        
        elif self.room_type == 'PASTOR':
            return User.objects.filter(
                id=user.id,
                church_roles__church=self.church,
                church_roles__role='PASTOR'
            ).exists()
        
        elif self.room_type == 'COMMISSION':
            if self.commission:
                return User.objects.filter(
                    id=user.id,
                    church_commissions__commission=self.commission
                ).exists()
            return False
        
        elif self.room_type == 'CUSTOM':
            return self.members.filter(id=user.id).exists()
        
        return False
    
    def get_members_queryset(self):
        """Get all members who have access to this room based on type"""
        from django.db.models import Q
        
        # Get owners
        owners_qs = User.objects.filter(
            church_roles__church=self.church,
            church_roles__role='OWNER'
        )
        
        if self.room_type == 'CHURCH':
            # All church members + owners
            return User.objects.filter(
                Q(current_church=self.church) | 
                Q(church_roles__church=self.church, church_roles__role='OWNER')
            ).distinct()
        
        elif self.room_type == 'OWNER':
            # All owners of the church
            return owners_qs.distinct()
        
        elif self.room_type == 'PASTOR':
            # All pastors + owners
            return User.objects.filter(
                Q(church_roles__church=self.church, church_roles__role='PASTOR') |
                Q(church_roles__church=self.church, church_roles__role='OWNER')
            ).distinct()
        
        elif self.room_type == 'COMMISSION':
            # All commission members + owners
            if self.commission:
                return User.objects.filter(
                    Q(church_commissions__commission=self.commission) |
                    Q(church_roles__church=self.church, church_roles__role='OWNER')
                ).distinct()
            return owners_qs.distinct()
        
        elif self.room_type == 'CUSTOM':
            # Custom members + owners
            custom_members = self.members.values_list('id', flat=True)
            return User.objects.filter(
                Q(id__in=custom_members) |
                Q(church_roles__church=self.church, church_roles__role='OWNER')
            ).distinct()
        
        return owners_qs.distinct()

class ChatMessage(models.Model):
    """Chat messages in a room"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey("ChatRoom", on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="chat_messages")
    message = models.TextField(blank=True)
    
    # AWS URLs
    image_url = models.URLField(max_length=500, null=True, blank=True)
    audio_url = models.URLField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "-created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user.name} - {self.room.name}"