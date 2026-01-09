from django.contrib import admin
from .models import Church, ChurchAdmin, Subscription, Notification, OTP, Content, Category, BookOrder, TicketType, TicketReservation, Ticket

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
