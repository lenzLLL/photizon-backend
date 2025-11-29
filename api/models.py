from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.utils.text import slugify
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
    # Identification
    code = models.IntegerField(unique=True, db_index=True)
    title = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    lang = models.CharField(default="fr")
    # Description & branding
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=20, default="#1A73E8")
    secondary_color = models.CharField(max_length=20, default="#FFFFFF")

    # Contact info
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    whatsapp_phone = models.TextField(max_length=500, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
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
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
 # Exemple: A9F73B12E1
        if not self.code:
            last_churchs = Church.objects.all().count()
            self.code = last_churchs+1
        super().save(*args, **kwargs)
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
        on_delete=models.CASCADE,
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
    slug = models.SlugField()
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True, null=True)

    # For media (optional fields depending on type)
    audio_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    file = models.URLField(blank=True, null=True)

    # Event-specific fields
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=250, blank=True)
    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default="XAF")
    # Flexibility
    metadata = models.JSONField(default=dict)

    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True)

    created_by = models.ForeignKey("User", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    published = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.type} - {self.title}"
  


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

class ContentTag(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

class Playlist(models.Model):
    church = models.ForeignKey(Church, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0)

class ContentView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

class ContentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.ForeignKey(Content, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

class OTP(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent_at = models.DateTimeField(auto_now=True)
    session_id = models.UUIDField(default=uuid.uuid4)

    def is_expired(self):
        from django.conf import settings
        expiration = settings.OTP_EXPIRATION_SECONDS
        print("last_sent_at:", settings.OTP_EXPIRATION_SECONDS)
        return (timezone.now() - self.last_sent_at).total_seconds() > expiration

    def can_resend(self):
        from django.conf import settings
        cooldown = settings.OTP_SEND_COOLDOWN_SECONDS
        return (timezone.now() - self.last_sent_at).total_seconds() > cooldown


class ChurchAdmin(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Admin"),
        ("MODERATOR", "Moderator"),
    ]

    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="admins")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="church_roles")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="ADMIN")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "user")

    def __str__(self):
        return f"{self.user.phone_number} @ {self.church.title} ({self.role})"


# SaaS subscription model
class Subscription(models.Model):
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
    name = models.CharField(max_length=255, unique=True)
    eng_name = models.CharField(max_length=255, unique=True,default="")
    logo = models.URLField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChurchCommission(models.Model):
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

    church = models.ForeignKey("Church", on_delete=models.CASCADE, related_name="denied_members")
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="denied_in_churches")
    reason = models.TextField(blank=True)
    denied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("church", "user")

    def __str__(self):
        return f"{self.user.phone_number} denied from {self.church.title}"
    
class DonationCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

  # Une catégorie par église

    def __str__(self):
        return f"{self.name}"
    

class Donation(models.Model):

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
class BookOrder(models.Model):

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
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    withdrawed = models.BooleanField(default=False) 
    payment_gateway = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="CASH")
    payment_transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    shipped = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calcul automatique du prix total
        if self.content.price:
            self.total_price = self.quantity * self.content.price
        else:
            self.total_price = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.phone_number} - {self.content.title} ({self.delivery_type}) x{self.quantity}"
