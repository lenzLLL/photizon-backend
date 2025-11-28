from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.utils.text import slugify
from api.permissions import IsAuthenticatedUser, IsSuperAdmin
from api.serializers import CategorySerializer, CommentSerializer, ContentCreateUpdateSerializer, ContentDetailSerializer, ContentListSerializer, PlaylistItemSerializer, PlaylistSerializer, TagSerializer
# imports communs pour serializers + views
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

# tes modèles (adaptés à ton projet)
from api.models import (
    ChurchAdmin, Content, Category, Tag, ContentTag, Playlist, PlaylistItem,
    ContentView, ContentLike, Comment, Church, User
)
# permissions existantes
from api.permissions import IsAuthenticatedUser
# utilitaires si besoin
from django.utils import timezone


@api_view(["POST"])
@permission_classes([IsSuperAdmin])
def create_category(request):
    data = request.data.copy()
    if "name" in data:
        data["slug"] = slugify(data["name"])

    serializer = CategorySerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def list_categories(request):
    categories = Category.objects.all().order_by("name")
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def get_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    serializer = CategorySerializer(category)
    return Response(serializer.data)

@api_view(["PUT", "PATCH"])
@permission_classes([IsSuperAdmin])
def update_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    data = request.data.copy()
    if "name" in data:
        data["slug"] = slugify(data["name"])

    serializer = CategorySerializer(category, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
# @permission_classes([IsAuthenticatedUser])
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return Response({"detail": "Category deleted successfully"})

class DefaultPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100

# List all content (global or by church) with filters, search, ordering
@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_content(request):
    """
    Query params:
      - church_id
      - type (ARTICLE,AUDIO,EVENT,VIDEO,POST,BOOK)
      - category_id
      - tag (name)
      - search (title/description)
      - ordering (created_at, likes, views) prefixed with - for desc
      - published (true/false)
    """
    qs = Content.objects.all()

    church_id = request.GET.get("church_id")
    ctype = request.GET.get("type")
    category_id = request.GET.get("category_id")
    tag = request.GET.get("tag")
    search = request.GET.get("search")
    published = request.GET.get("published")

    if church_id:
        qs = qs.filter(church_id=church_id)

    if ctype:
        qs = qs.filter(type=ctype)

    if category_id:
        qs = qs.filter(category_id=category_id)

    if tag:
        qs = qs.filter(contenttag__tag__name__icontains=tag)

    if published is not None:
        if published.lower() in ["true","1","yes"]:
            qs = qs.filter(published=True)
        else:
            qs = qs.filter(published=False)

    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # annotate likes & views for ordering if requested
    qs = qs.annotate(likes_count=Count("contentlike"), views_count=Count("contentview"))

    ordering = request.GET.get("ordering")
    if ordering:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("-created_at")

    paginator = DefaultPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = ContentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def retrieve_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    serializer = ContentDetailSerializer(obj)
    return Response(serializer.data)


@api_view(["POST"])
# @permission_classes([IsAuthenticatedUser])
def create_content(request):
    # Only church admins/owner or SADMIN can create for other churches (we assume check)
    data = request.data.copy()
    # created_by set to request.user
    data["created_by"] = request.user.id
    serializer = ContentCreateUpdateSerializer(data=data)
    if serializer.is_valid():
        content = serializer.save()
        # handle tags if provided as comma separated or list
        tags = request.data.get("tags")
        if tags:
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            for t in tags:
                tag_obj, _ = Tag.objects.get_or_create(name=t, defaults={"slug": t.lower().replace(" ","-")})
                ContentTag.objects.get_or_create(content=content, tag=tag_obj)
        return Response(ContentDetailSerializer(content).data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["PUT","PATCH"])
@permission_classes([IsAuthenticatedUser])
def update_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    # check permission: creator or church admin or SADMIN (you can implement strict check)
    if request.user != obj.created_by and request.user.role != "SADMIN":
        # also allow church owner/admin check
        if not ChurchAdmin.objects.filter(church=obj.church, user=request.user).exists():
            return Response({"detail":"Forbidden"}, status=403)
    serializer = ContentCreateUpdateSerializer(obj, data=request.data, partial=True)
    if serializer.is_valid():
        content = serializer.save()
        return Response(ContentDetailSerializer(content).data)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_content(request, content_id):
    obj = get_object_or_404(Content, id=content_id)
    if request.user != obj.created_by and request.user.role != "SADMIN":
        if not ChurchAdmin.objects.filter(church=obj.church, user=request.user).exists():
            return Response({"detail":"Forbidden"}, status=403)
    obj.delete()
    return Response({"detail":"deleted"})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def like_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    obj, created = ContentLike.objects.get_or_create(user=request.user, content=content)
    if created:
        return Response({"liked": True})
    return Response({"liked": True, "note":"already liked"})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def unlike_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    ContentLike.objects.filter(user=request.user, content=content).delete()
    return Response({"liked": False})

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def view_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    ContentView.objects.create(user=request.user, content=content)
    return Response({"viewed": True})

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_comments(request, content_id):
    qs = Comment.objects.filter(content_id=content_id).order_by("-created_at")
    paginator = DefaultPagination()
    page = paginator.paginate_queryset(qs, request)
    serializer = CommentSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def add_comment(request, content_id):
    text = request.data.get("text")
    if not text:
        return Response({"error":"text required"}, status=400)
    content = get_object_or_404(Content, id=content_id)
    c = Comment.objects.create(user=request.user, content=content, text=text)
    return Response(CommentSerializer(c).data, status=201)

@api_view(["DELETE"])
@permission_classes([IsAuthenticatedUser])
def delete_comment(request, comment_id):
    c = get_object_or_404(Comment, id=comment_id)
    if c.user != request.user and request.user.role != "SADMIN":
        return Response({"error":"forbidden"}, status=403)
    c.delete()
    return Response({"deleted": True})


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def list_tags(request):
    qs = Tag.objects.all()
    serializer = TagSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser, IsSuperAdmin])
def create_tag(request):
    name = request.data.get("name")
    if not name:
        return Response({"error":"name required"}, status=400)
    tag, created = Tag.objects.get_or_create(name=name, defaults={"slug": name.lower().replace(" ","-")})
    return Response(TagSerializer(tag).data, status=201 if created else 200)



@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def create_playlist(request):
    serializer = PlaylistSerializer(data=request.data)
    if serializer.is_valid():
        pl = serializer.save()
        return Response(PlaylistSerializer(pl).data, status=201)
    return Response(serializer.errors, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def add_to_playlist(request, playlist_id):
    playlist = get_object_or_404(Playlist, id=playlist_id)
    content_id = request.data.get("content_id")
    pos = request.data.get("position", 0)
    content = get_object_or_404(Content, id=content_id)
    item = PlaylistItem.objects.create(playlist=playlist, content=content, position=pos)
    return Response(PlaylistItemSerializer(item).data, status=201)

@api_view(["POST"])
@permission_classes([IsAuthenticatedUser])
def reorder_playlist_item(request, item_id):
    item = get_object_or_404(PlaylistItem, id=item_id)
    new_pos = int(request.data.get("position", item.position))
    item.position = new_pos
    item.save()
    return Response(PlaylistItemSerializer(item).data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def trending_content(request):
    # trending by views + likes (simple score)
    qs = Content.objects.annotate(
        likes=Count("contentlike"),
        views=Count("contentview")
    ).annotate(
        score=Count("contentview") + Count("contentlike")*2
    ).order_by("-score")[:20]
    serializer = ContentListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def recommend_for_user(request):
    # simple tag-based recommendations: pick user last viewed content tags and recommend similar content
    last_views = ContentView.objects.filter(user=request.user).order_by("-viewed_at")[:10]
    tag_ids = ContentTag.objects.filter(content__in=[v.content for v in last_views]).values_list("tag_id", flat=True)
    qs = Content.objects.filter(contenttag__tag_id__in=tag_ids).exclude(id__in=[v.content_id for v in last_views]).distinct()[:20]
    serializer = ContentListSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def feed_for_church(request, church_id):
    # Latest content
    latest = list(
        Content.objects
        .filter(church_id=church_id)
        .order_by("-created_at")[:30]
    )

    # IDs déjà utilisés
    used_ids = {c.id for c in latest}

    # Trending content, sans ceux déjà dans latest
    trending = list(
        Content.objects
        .filter(church_id=church_id)
        .exclude(id__in=used_ids)
        .annotate(views=Count("contentview"))
        .order_by("-views")[:10]
    )

    # Combine proprement
    items = latest + trending

    serializer = ContentListSerializer(items, many=True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def content_stats_global(request):
    total = Content.objects.count()
    by_type = Content.objects.values("type").annotate(total=Count("id")).order_by("-total")
    by_month = Content.objects.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id")).order_by("month")
    top_liked = Content.objects.annotate(likes=Count("contentlike")).order_by("-likes")[:10].values("id","title","likes")
    return Response({
        "total": total,
        "by_type": list(by_type),
        "by_month": list(by_month),
        "top_liked": list(top_liked)
    })


@api_view(["GET"])
@permission_classes([IsAuthenticatedUser])
def content_stats_for_church(request, church_id):
    church = get_object_or_404(Church, id=church_id)
    total = Content.objects.filter(church=church).count()
    by_type = Content.objects.filter(church=church).values("type").annotate(total=Count("id")).order_by("-total")
    top_liked = Content.objects.filter(church=church).annotate(likes=Count("contentlike")).order_by("-likes")[:10].values("id","title","likes")
    views = ContentView.objects.filter(content__church=church).count()
    return Response({
        "total": total,
        "by_type": list(by_type),
        "top_liked": list(top_liked),
        "views": views
    })

@api_view(["GET"])
@permission_classes([IsAuthenticatedUser, IsSuperAdmin])
def list_all_playlists(request):
    qs = (
        Playlist.objects
        .select_related("church")
        .prefetch_related(
            "playlistitem_set",
            "playlistitem_set__content",
        )
        .order_by("-created_at")
    )
    church_id = request.GET.get("church_id")
    if church_id:
       qs = qs.filter(church_id=church_id)

    serializer = PlaylistSerializer(qs, many=True)
    return Response(serializer.data)