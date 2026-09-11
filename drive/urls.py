from django.urls import path
from drive import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),

    # Drive Views
    path('', views.drive_root, name='drive_root'),
    path('drive/', views.drive_root, name='drive_home'),
    path('drive/folder/<uuid:folder_id>/', views.folder_view, name='folder_view'),
    path('drive/starred/', views.starred_view, name='starred_view'),
    path('drive/trash/', views.trash_view, name='trash_view'),
    path('share/<str:share_token>/', views.share_view, name='share_view'),
    path('share/<str:share_token>/download-zip/', views.share_folder_download_zip, name='share_folder_download_zip'),
    path('drive/download/<uuid:file_id>/', views.download_file, name='download_file'),
    path('drive/view/<uuid:file_id>/', views.view_file, name='view_file'),


    # API Endpoints
    path('api/folders/create/', views.api_create_folder, name='api_create_folder'),
    path('api/files/upload/', views.api_upload_file, name='api_upload_file'),
    path('api/items/<uuid:item_id>/rename/', views.api_rename_item, name='api_rename_item'),
    path('api/items/<uuid:item_id>/move/', views.api_move_item, name='api_move_item'),
    path('api/items/<uuid:item_id>/copy/', views.api_copy_item, name='api_copy_item'),
    path('api/items/<uuid:item_id>/star/', views.api_toggle_star, name='api_toggle_star'),
    path('api/items/<uuid:item_id>/trash/', views.api_trash_item, name='api_trash_item'),
    path('api/items/<uuid:item_id>/restore/', views.api_restore_item, name='api_restore_item'),
    path('api/items/<uuid:item_id>/delete/', views.api_delete_permanent, name='api_delete_permanent'),
    path('api/trash/empty/', views.api_empty_trash, name='api_empty_trash'),
    path('api/items/<uuid:item_id>/share/', views.api_share_settings, name='api_share_settings'),
    path('api/search/', views.api_instant_search, name='api_instant_search'),
    path('api/shared/save-copy/<uuid:item_id>/', views.api_save_shared_copy, name='api_save_shared_copy'),
    path('api/storage/', views.api_storage_stats, name='api_storage_stats'),
    path('api/folders/available/', views.api_available_folders, name='api_available_folders_all'),
    path('api/folders/available/<uuid:item_id>/', views.api_available_folders, name='api_available_folders_filtered'),

    # Batch Operations
    path('api/batch/trash/', views.api_batch_trash, name='api_batch_trash'),
    path('api/batch/restore/', views.api_batch_restore, name='api_batch_restore'),
    path('api/batch/delete/', views.api_batch_delete, name='api_batch_delete'),
    path('api/batch/star/', views.api_batch_star, name='api_batch_star'),
    path('api/batch/move/', views.api_batch_move, name='api_batch_move'),
    path('api/batch/download-zip/', views.api_batch_download_zip, name='api_batch_download_zip'),

    # User Profile & Password Management
    path('api/account/profile/', views.api_update_profile, name='api_update_profile'),
    path('api/account/change-password/', views.api_change_password, name='api_change_password'),
]

