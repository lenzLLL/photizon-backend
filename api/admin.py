from django.contrib import admin
from .models import (
    Church, ChurchAdmin, Subscription, SubscriptionPlan, Notification, OTP,
    Content, Category, BookOrder, TicketType, TicketReservation, Ticket, Payment,
    ServiceConfiguration, User
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "name", "email", "role", "current_church", "city", "country", "is_active", "is_staff", "created_at")
    search_fields = ("phone_number", "name", "email", "city", "country")
    list_filter = ("role", "is_active", "is_staff", "is_superuser", "country")
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        ("Informations de base", {
            "fields": ("phone_number", "name", "email", "picture_url")
        }),
        ("Rôle et église", {
            "fields": ("role", "current_church")
        }),
        ("Localisation", {
            "fields": ("address", "city", "country", "longitude", "latitude")
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser"),
            "classes": ("collapse",)
        }),
        ("Informations système", {
            "fields": ("id", "created_at", "updated_at", "last_login"),
            "classes": ("collapse",)
        }),
    )

    def get_queryset(self, request):
        """Optimise la requête avec select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('current_church')

@admin.register(Church)
class ChurchAdminAdmin(admin.ModelAdmin):
    list_display = ("title","code","owner","status","is_verified","created_at")
    search_fields = ("title","code","owner__phone_number")
    list_filter = ("status","is_verified")
    readonly_fields = ("code","slug","created_at")

@admin.register(ChurchAdmin)
class ChurchAdminInline(admin.ModelAdmin):
    list_display = ("church","user","role","created_at")
    search_fields = ("church__title","user__phone_number")

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("display_name", "name", "price", "currency", "duration_days", "is_active", "order")
    list_filter = ("is_active", "has_chat", "has_programmes", "has_analytics")
    search_fields = ("name", "display_name", "description")
    ordering = ("order", "price")

    fieldsets = (
        ("Informations de base", {
            "fields": ("name", "display_name", "description", "order", "is_active")
        }),
        ("Prix et validité", {
            "fields": ("price", "currency", "duration_days")
        }),
        ("Limites", {
            "fields": ("max_members", "max_contents", "max_storage_gb")
        }),
        ("Fonctionnalités", {
            "fields": ("has_chat", "has_programmes", "has_analytics", "has_custom_branding", "features")
        }),
    )

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("church", "get_plan_display", "subscription_plan", "is_active", "started_at", "expires_at")
    list_filter = ("plan", "is_active", "subscription_plan")
    search_fields = ("church__title",)

    def get_plan_display(self, obj):
        return obj.get_plan_name()
    get_plan_display.short_description = "Plan actuel"

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user","title","type","channel","sent","created_at")
    search_fields = ("user__phone_number","title","message")
    list_filter = ("type","channel","sent")


@admin.register(BookOrder)
class BookOrderAdmin(admin.ModelAdmin):
    list_display = ("id","user","content","quantity","total_price","is_ticket","created_at")
    list_filter = ("is_ticket","payment_gateway")
    search_fields = ("user__phone_number","content__title","payment_transaction_id")


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ("id","content","name","price","quantity","created_at")
    search_fields = ("content__title","name")


@admin.register(TicketReservation)
class TicketReservationAdmin(admin.ModelAdmin):
    list_display = ("id","user","content","ticket_type","quantity","reserved_at","expires_at")
    search_fields = ("user__phone_number","content__title")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id","content","order","user","status","issued_at","price")
    search_fields = ("id","user__phone_number","content__title")
    list_filter = ("status",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id","user","church","amount","currency","gateway","status","gateway_transaction_id","created_at")
    search_fields = ("user__phone_number","gateway_transaction_id","church__title")
    list_filter = ("gateway","status")


@admin.register(ServiceConfiguration)
class ServiceConfigurationAdmin(admin.ModelAdmin):
    list_display = ("service_type", "is_active", "get_status", "updated_at")
    list_filter = ("service_type", "is_active")
    search_fields = ("service_type",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Configuration Générale", {
            "fields": ("service_type", "is_active", "config")
        }),
        ("Mode Maintenance", {
            "fields": ("maintenance_message",),
            "classes": ("collapse",),
            "description": "Configuration du mode maintenance"
        }),
        ("WhatsApp API", {
            "fields": (
                "whatsapp_api_token",
                "whatsapp_phone_number_id",
                "whatsapp_api_version",
                "whatsapp_template_name",
                "whatsapp_language"
            ),
            "classes": ("collapse",),
            "description": "Configuration de l'API WhatsApp (Meta/Facebook)"
        }),
        ("Nexaah SMS API", {
            "fields": (
                "nexaah_base_url",
                "nexaah_send_endpoint",
                "nexaah_credits_endpoint",
                "nexaah_user",
                "nexaah_password",
                "nexaah_sender_id"
            ),
            "classes": ("collapse",),
            "description": "Configuration de l'API Nexaah SMS"
        }),
        ("FreeMoPay Payment Gateway", {
            "fields": (
                "freemopay_base_url",
                "freemopay_app_key",
                "freemopay_secret_key",
                "freemopay_callback_url",
                "freemopay_init_payment_timeout",
                "freemopay_status_check_timeout",
                "freemopay_token_timeout",
                "freemopay_token_cache_duration",
                "freemopay_max_retries",
                "freemopay_retry_delay"
            ),
            "classes": ("collapse",),
            "description": "Configuration de l'API FreeMoPay"
        }),
        ("Préférences de Notification", {
            "fields": ("default_notification_channel",),
            "classes": ("collapse",),
            "description": "Configuration des préférences de notification"
        }),
        ("Informations système", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_status(self, obj):
        """Affiche le statut de configuration"""
        if obj.is_active:
            if obj.is_configured():
                return "✅ Configuré et actif"
            else:
                return "⚠️ Actif mais mal configuré"
        return "❌ Inactif"
    get_status.short_description = "Statut"

    def save_model(self, request, obj, form, change):
        """Valide la configuration avant sauvegarde"""
        super().save_model(request, obj, form, change)

        # Afficher les erreurs de validation si le service est actif
        if obj.is_active and not obj.is_configured():
            errors = []
            if obj.service_type == 'whatsapp':
                errors = obj.validate_whatsapp_config()
            elif obj.service_type == 'nexaah_sms':
                errors = obj.validate_nexaah_config()
            elif obj.service_type == 'freemopay':
                errors = obj.validate_freemopay_config()

            if errors:
                from django.contrib import messages
                messages.warning(
                    request,
                    f"Service activé mais incomplet : {', '.join(errors)}"
                )
