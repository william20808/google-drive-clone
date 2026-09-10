from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from drive.models import DriveItem, UserProfile
from drive.utils import get_user_storage_usage


# User Profile Storage Plan Inline inside User Admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Storage Tier & Plan Configuration'
    verbose_name_plural = 'Storage Tier & Plan Configuration'
    fields = ('storage_plan', 'custom_storage_limit_bytes')
    extra = 0


# Customized User Admin with Storage Tier Management
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        'username',
        'get_full_name_display',
        'email',
        'get_storage_plan_badge',
        'get_storage_usage_bar',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__storage_plan')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_inlines(self, request, obj=None):
        if obj is None:
            return ()
        return super().get_inlines(request, obj)

    def get_full_name_display(self, obj):
        full_name = obj.get_full_name()
        if full_name:
            return format_html('<strong>{}</strong>', full_name)
        return mark_safe('<span style="color: #9ca3af; font-style: italic;">(No name set)</span>')
    get_full_name_display.short_description = 'Full Name'

    def get_storage_plan_badge(self, obj):
        profile, _ = UserProfile.objects.get_or_create(user=obj)
        plan = profile.storage_plan
        if plan == '500GB':
            badge_style = "background: #7c3aed; color: #ffffff; padding: 3px 10px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block;"
        elif plan == '100GB':
            badge_style = "background: #0284c7; color: #ffffff; padding: 3px 10px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block;"
        else:
            badge_style = "background: #10b981; color: #ffffff; padding: 3px 10px; border-radius: 9999px; font-weight: 600; font-size: 11px; display: inline-block;"
        
        custom_note = " (Custom Override)" if profile.custom_storage_limit_bytes else ""
        return format_html(
            '<span style="{}">{}{}</span>',
            badge_style,
            profile.formatted_plan_name,
            custom_note
        )
    get_storage_plan_badge.short_description = 'Storage Plan'

    def get_storage_usage_bar(self, obj):
        usage = get_user_storage_usage(obj)
        pct = usage['percent']
        bar_color = "#ef4444" if pct >= 90 else "#f59e0b" if pct >= 75 else "#1a73e8"
        return format_html(
            '<div style="min-width: 140px;">'
            '<div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; font-weight: 500;">'
            '<span>{} / {}</span><span>{}%</span>'
            '</div>'
            '<div style="background: #e2e8f0; border-radius: 9999px; height: 6px; overflow: hidden;">'
            '<div style="background: {}; width: {}%; height: 100%; border-radius: 9999px;"></div>'
            '</div>'
            '</div>',
            usage['formatted_used'],
            usage['formatted_limit'],
            pct,
            bar_color,
            pct
        )
    get_storage_usage_bar.short_description = 'Storage Quota Used'


    actions = ['action_upgrade_15gb', 'action_upgrade_100gb', 'action_upgrade_500gb']

    @admin.action(description='⚡ Set storage to 15 GB for selected users')
    def action_upgrade_15gb(self, request, queryset):
        count = 0
        for u in queryset:
            p, _ = UserProfile.objects.get_or_create(user=u)
            p.storage_plan = '15GB'
            p.custom_storage_limit_bytes = None
            p.save()
            count += 1
        self.message_user(request, f'Updated {count} user(s) to 15 GB plan.')

    @admin.action(description='⚡ Upgrade storage to 100 GB for selected users')
    def action_upgrade_100gb(self, request, queryset):
        count = 0
        for u in queryset:
            p, _ = UserProfile.objects.get_or_create(user=u)
            p.storage_plan = '100GB'
            p.custom_storage_limit_bytes = None
            p.save()
            count += 1
        self.message_user(request, f'Upgraded {count} user(s) to 100 GB plan.')

    @admin.action(description='⚡ Upgrade storage to 500 GB for selected users')
    def action_upgrade_500gb(self, request, queryset):
        count = 0
        for u in queryset:
            p, _ = UserProfile.objects.get_or_create(user=u)
            p.storage_plan = '500GB'
            p.custom_storage_limit_bytes = None
            p.save()
            count += 1
        self.message_user(request, f'Upgraded {count} user(s) to 500 GB plan.')


# Standalone UserProfile Admin with In-Table Live Editing
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'get_full_name',
        'storage_plan',
        'custom_storage_limit_bytes',
        'get_quota_limit',
        'get_usage_bar',
        'updated_at',
    )
    list_editable = ('storage_plan', 'custom_storage_limit_bytes')
    list_filter = ('storage_plan',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    actions = ['action_set_15gb', 'action_set_100gb', 'action_set_500gb']

    def get_full_name(self, obj):
        name = obj.user.get_full_name()
        if name:
            return format_html('<strong>{}</strong>', name)
        return mark_safe('<span style="color: #9ca3af; font-style: italic;">(No name set)</span>')
    get_full_name.short_description = 'Name'

    def get_quota_limit(self, obj):
        from drive.utils import format_bytes
        return format_bytes(obj.storage_limit_bytes)
    get_quota_limit.short_description = 'Effective Limit'

    def get_usage_bar(self, obj):
        usage = get_user_storage_usage(obj.user)
        pct = usage['percent']
        bar_color = "#ef4444" if pct >= 90 else "#f59e0b" if pct >= 75 else "#1a73e8"
        return format_html(
            '<div style="min-width: 140px;">'
            '<div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px; font-weight: 500;">'
            '<span>{}</span><span>{}%</span>'
            '</div>'
            '<div style="background: #e2e8f0; border-radius: 9999px; height: 6px; overflow: hidden;">'
            '<div style="background: {}; width: {}%; height: 100%; border-radius: 9999px;"></div>'
            '</div>'
            '</div>',
            usage['formatted_used'],
            pct,
            bar_color,
            pct
        )
    get_usage_bar.short_description = 'Used Space'

    @admin.action(description='⚡ Set storage to 15 GB (Free / Basic)')
    def action_set_15gb(self, request, queryset):
        updated = queryset.update(storage_plan='15GB', custom_storage_limit_bytes=None)
        self.message_user(request, f'Updated {updated} user profile(s) to 15 GB.')

    @admin.action(description='⚡ Upgrade storage to 100 GB (Standard)')
    def action_set_100gb(self, request, queryset):
        updated = queryset.update(storage_plan='100GB', custom_storage_limit_bytes=None)
        self.message_user(request, f'Upgraded {updated} user profile(s) to 100 GB.')

    @admin.action(description='⚡ Upgrade storage to 500 GB (Premium Pro)')
    def action_set_500gb(self, request, queryset):
        updated = queryset.update(storage_plan='500GB', custom_storage_limit_bytes=None)
        self.message_user(request, f'Upgraded {updated} user profile(s) to 500 GB.')


# Re-register User with customized UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Unregister Group to remove unused permissions/group clutter
from django.contrib.auth.models import Group
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


# DriveItem Admin
@admin.register(DriveItem)
class DriveItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_folder', 'owner', 'parent', 'formatted_size', 'is_starred', 'is_trashed', 'is_shared', 'created_at')
    list_select_related = ('owner', 'parent')
    list_filter = ('is_folder', 'is_starred', 'is_trashed', 'is_shared', 'owner')
    search_fields = ('name', 'owner__username', 'owner__email')
    readonly_fields = ('id', 'created_at', 'updated_at')

