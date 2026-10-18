from django.contrib import admin

from .models import InstagramAccount, MediaAsset, Post, PostItem, QueueSettings, RecurringRule


class PostItemInline(admin.TabularInline):
    model = PostItem
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["__str__", "post_type", "status", "scheduled_at", "published_at", "source"]
    list_filter = ["status", "post_type", "source"]
    inlines = [PostItemInline]


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ["__str__", "kind", "in_queue", "times_used", "created_at"]
    list_filter = ["kind", "in_queue"]


@admin.register(InstagramAccount)
class InstagramAccountAdmin(admin.ModelAdmin):
    list_display = ["username", "ig_user_id", "token_expires_at"]
    exclude = ["access_token"]


admin.site.register(RecurringRule)
admin.site.register(QueueSettings)
