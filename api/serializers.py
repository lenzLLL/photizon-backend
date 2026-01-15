from rest_framework import serializers
from api.models import BookOrder, Comment, Content, Donation, DonationCategory,Tag, ContentLike, ContentView, Playlist, PlaylistItem, User,Church, Subscription, ChurchAdmin,Commission,ChurchCommission,Category, TicketType, Ticket, TicketReservation, Receipt
from django.utils.text import slugify

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"

class ChurchSerializer(serializers.ModelSerializer):
    sub_churches = serializers.SerializerMethodField()
    phone_number = serializers.CharField(read_only=True)
    phone_number_1 = serializers.CharField(read_only=True)
    phone_number_2 = serializers.CharField(read_only=True)
    phone_number_3 = serializers.CharField(read_only=True)
    phone_number_4 = serializers.CharField(read_only=True)
    class Meta:
        model = Church
        fields = "__all__"
        read_only_fields = ["status", "code", "slug", "is_verified", "created_at"]

    def get_sub_churches(self, obj):
        qs = obj.sub_churches.all()
        return [{"id": c.id, "title": c.title, "slug": c.slug, "status": c.status,"code":c.code,"logo_url":c.logo_url,
                 "phone_number":c.phone_number,
                 "phone_number_1": c.phone_number_1,
                 "phone_number_2": c.phone_number_2,
                 "phone_number_3": c.phone_number_3,
                 "phone_number_4": c.phone_number_4,
                 "is_verified":c.is_verified} for c in qs]



class ChurchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = [
            "title", "logo_url",
            "primary_color", "secondary_color",
            "phone_number_1", "phone_number_2", "phone_number_3", "phone_number_4",
            "city", "country","lang",
            "seats", "is_public"
        ]

class SubChurchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = [
            "title", "logo_url", "parent",
            "primary_color", "secondary_color",
            "phone_number_1", "phone_number_2", "phone_number_3", "phone_number_4",
            "city", "country", "lang",
            "seats", "is_public",
        ]
        
class ChurchAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChurchAdmin
        fields = "__all__"

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["started_at"]

class ChurchRoleSerializer(serializers.ModelSerializer):
    church = serializers.SerializerMethodField()

    class Meta:
        model = ChurchAdmin
        fields = ["church", "role", "created_at"]

    def get_church(self, obj):
        return {
            "id": obj.church.id,
            "title": obj.church.title,
            "code": obj.church.code,
            "city": obj.church.city,
            "country": obj.church.country,
            "status": obj.church.status,
        }

class ChurchMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Church
        fields = ["id", "title", "code", "city", "country", "status"]

class UserMeSerializer(serializers.ModelSerializer):
    current_church = ChurchMiniSerializer(read_only=True)
    church_roles = ChurchRoleSerializer(many=True, read_only=True)

    is_sadmin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "phone_number",
            "picture_url",
            "role",
            "is_sadmin",
            "current_church",
            "church_roles",
            "created_at",
            "updated_at",
        ]

    def get_is_sadmin(self, obj):
        return obj.role == "SADMIN"

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "phone_number", "picture_url", "created_at"]

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = ["id", "name","eng_name","logo","description"]

class ChurchCommissionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    commission = serializers.SerializerMethodField()

    class Meta:
        model = ChurchCommission
        fields = [
            "id",
            "church",
            "commission",
            "user",
            "role",
          
        ]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "name": obj.user.name,
            "phone_number": obj.user.phone_number,
            "picture_url": obj.user.picture_url,
        }

    def get_commission(self, obj):
        return {
            "id": obj.commission.id,
            "name": obj.commission.name,
            "eng_name": obj.commission.eng_name,
            "logo": obj.commission.logo,
        }

class AddMemberToCommissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.CharField(required=False, default="MEMBER")

class ChurchCommissionSummarySerializer(serializers.Serializer):
    commission_id = serializers.IntegerField()
    commission_name = serializers.CharField()
    members_count = serializers.IntegerField()

class CommissionMemberSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id")
    name = serializers.CharField(source="user.name")
    phone_number = serializers.CharField(source="user.phone_number")
    picture_url = serializers.CharField(source="user.picture_url")

    class Meta:
        model = ChurchCommission
        fields = [
            "id",
            "role",
            "name",
            "phone_number",
            "picture_url",
        ]

class ChurchCommissionMemberSerializer(serializers.ModelSerializer):
    user = UserMeSerializer()

    class Meta:
        model = ChurchCommission
        fields = ["id", "user", "role", "joined_at"]


class CommissionWithMembersSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Commission
        fields = ["id", "name", "logo", "description", "members"]

    def get_members(self, obj):
        church_id = self.context.get("church_id")
        qs = ChurchCommission.objects.filter(church_id=church_id, commission=obj)
        # Return flattened user objects with role (id, name, phone_number, picture_url, role, created_at)
        return CommissionMemberSerializer(qs, many=True).data

class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

    def validate_name(self, value):
        if Category.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("This category already exists.")
        return value

    def create(self, validated_data):
        validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.slug = slugify(validated_data["name"])
        return super().update(instance, validated_data)

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]

class ContentListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    church = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Content
        fields = [
            "id","church","type","title","slug","description","cover_image_url",
            "is_paid","price","currency","category","tags","created_at","published",
            "capacity","tickets_sold","allow_ticket_sales"
        ]

    def get_tags(self, obj):
        return list(obj.contenttag_set.select_related("tag").values("tag__id","tag__name","tag__slug"))

class ContentDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    church = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Content
        fields = "__all__"

    def get_tags(self, obj):
        return TagSerializer([ct.tag for ct in obj.contenttag_set.all()], many=True).data

    def get_church(self, obj):
        return {"id": obj.church.id, "title": obj.church.title, "code": obj.church.code}

    def get_created_by(self, obj):
        if obj.created_by:
            return {"id": obj.created_by.id, "name": obj.created_by.name, "phone_number": obj.created_by.phone_number}
        return None

class ContentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        exclude = ["created_at", "updated_at"]

    def validate(self, data):
        # If capacity is provided in payload or already on instance, ensure tier sums fit
        capacity = data.get("capacity")
        # When updating, instance may have existing capacity
        instance = getattr(self, "instance", None)
        if capacity is None and instance is not None:
            capacity = instance.capacity

        has_tiers = data.get("has_ticket_tiers", None)
        # If not provided, fall back to instance
        if has_tiers is None and instance is not None:
            has_tiers = instance.has_ticket_tiers

        if has_tiers and capacity is not None:
            # compute sum of provided/new tier quantities, falling back to instance values
            def val(field):
                return data.get(field, getattr(instance, field, None) if instance is not None else None) or 0

            total = int(val("classic_quantity")) + int(val("vip_quantity")) + int(val("premium_quantity"))
            if total > int(capacity):
                raise serializers.ValidationError("Sum of tier quantities exceeds capacity")

        return data

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    class Meta:
        model = Comment
        fields = ["id","user","content","text","created_at"]

    def get_user(self, obj):
        return {"id": obj.user.id, "name": obj.user.name, "phone": obj.user.phone_number}
    def get_content(self, obj):
        return {"id": obj.content.id, "title": obj.content.title, "slug": obj.content.slug}
class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentLike
        fields = ["id","user","content","liked_at"]
class ContentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ["id", "title", "slug", "type", "cover_image_url"]

class ViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentView
        fields = ["id","user","content","viewed_at"]
class PlaylistItemNestedSerializer(serializers.ModelSerializer):
    content = ContentNestedSerializer()  # inclut les infos du content

    class Meta:
        model = PlaylistItem
        fields = ["id", "content", "position"]
class PlaylistSerializer(serializers.ModelSerializer):
    items = PlaylistItemNestedSerializer(source="playlistitem_set", many=True, read_only=True)
    church = serializers.SerializerMethodField()
    class Meta:
        model = Playlist
        fields = ["id", "church", "title", "description", "cover_image_url", "items"]
    def get_church(self, obj):
        return {
            "id": obj.church.id,
            "title": obj.church.title,
            "code": obj.church.code
        }
class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ["id", "title", "slug", "type", "cover_image_url"] 

class PlaylistItemSerializer(serializers.ModelSerializer):
    content = ContentSerializer(read_only=True)
    playlist = PlaylistSerializer(read_only=True)

    class Meta:
        model = PlaylistItem
        fields = ["id", "playlist", "content", "position"]

class SubscriptionSerializer(serializers.ModelSerializer):
    church = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id", "church", "plan", "started_at", "expires_at",
            "is_active", "gateway", "gateway_subscription_id"
        ]

    def get_church(self, obj):
        return {
            "id": obj.church.id,
            "title": obj.church.title,
            "code": obj.church.code
        }

class PlaylistItemSContenterializer(serializers.ModelSerializer):
    content = ContentDetailSerializer()

    class Meta:
        model = PlaylistItem
        fields = ["id", "position", "content"]



class OwnerSerializer(serializers.ModelSerializer):
    churches = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "phone_number", "churches"]

    def get_churches(self, user):
        # Toutes les églises où ce user est OWNER
        admin_entries = ChurchAdmin.objects.filter(user=user, role="OWNER")
        churches = [entry.church for entry in admin_entries]

        return ChurchSerializer(churches, many=True).data

class DonationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationCategory
        fields = ["id", "name", "description"]

class DonationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    church = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            "id", "user", "church", "category",
            "amount", "currency", "gateway", "gateway_transaction_id",
             "message", "metadata","withdrawed"
            
        ]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "phone_number": obj.user.phone_number,
            "name": obj.user.name
        }

    def get_church(self, obj):
        return {
            "id": obj.church.id,
            "title": obj.church.title,
            "code": obj.church.code
        }

    def get_category(self, obj):
        if obj.category:
            return {
                "id": obj.category.id,
                "name": obj.category.name
            }
        return None
    
class BookOrderSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    tickets = serializers.SerializerMethodField()

    class Meta:
        model = BookOrder
        fields = [
            "id", "user", "content", "delivery_type", "quantity", 
            "total_price", "payment_gateway", "payment_transaction_id", 
            "shipped", "delivered_at", "created_at","withdrawed",
            "is_ticket", "ticket_type", "ticket_tier", "tickets",
            "delivery_recipient_name", "delivery_address_line1", "delivery_address_line2",
            "delivery_city", "delivery_postal_code", "delivery_country", "delivery_phone",
            "shipping_method", "shipping_cost",
        ]
    
    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "phone_number": obj.user.phone_number,
            "name": obj.user.name
        }

    def get_content(self, obj):
        return {
            "id": obj.content.id,
            "title": obj.content.title,
            "type": obj.content.type,
            "price": obj.content.price,
            "has_ticket_tiers": obj.content.has_ticket_tiers,
            "classic_price": obj.content.classic_price,
            "classic_quantity": obj.content.classic_quantity,
            "vip_price": obj.content.vip_price,
            "vip_quantity": obj.content.vip_quantity,
            "premium_price": obj.content.premium_price,
            "premium_quantity": obj.content.premium_quantity,
            "church_id": obj.content.church.id,
            "church_title": obj.content.church.title
        }

    def get_tickets(self, obj):
        qs = obj.tickets.all() if hasattr(obj, "tickets") else []
        return TicketSerializer(qs, many=True).data


class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ["id", "content", "name", "price", "quantity", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["id", "content", "order", "ticket_type", "user", "seat", "price", "status", "issued_at"]


class TicketReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketReservation
        fields = ["id", "user", "content", "ticket_type", "quantity", "reserved_at", "expires_at"]


class ReceiptSerializer(serializers.ModelSerializer):
    church_title = serializers.CharField(source="church.title", read_only=True, allow_null=True)
    content_title = serializers.CharField(source="content.title", read_only=True, allow_null=True)
    
    class Meta:
        model = Receipt
        fields = [
            "id", "church", "church_title", "content", "content_title",
            "amount", "description", "issued_at", "created_at"
        ]
        read_only_fields = ["id", "issued_at", "created_at", "church"]