from drive.utils import get_user_storage_usage, get_admin_contact_email

def drive_context(request):
    admin_email = get_admin_contact_email()
    if request.user.is_authenticated:
        storage = get_user_storage_usage(request.user)
        return {
            'storage': storage,
            'current_user': request.user,
            'admin_email': admin_email,
        }
    return {
        'storage': {
            'used_bytes': 0,
            'limit_bytes': 15 * 1024 * 1024 * 1024,
            'formatted_used': '0 B',
            'formatted_limit': '15 GB',
            'percent': 0,
        },
        'admin_email': admin_email,
    }
