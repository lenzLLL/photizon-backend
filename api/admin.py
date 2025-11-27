from django.contrib import admin
from .models import Church, ChurchAdmin, Subscription, Notification, OTP, Content, Category

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

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("church","plan","is_active","started_at","expires_at")
    list_filter = ("plan","is_active")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user","title","type","channel","sent","created_at")
    search_fields = ("user__phone_number","title","message")
    list_filter = ("type","channel","sent")
