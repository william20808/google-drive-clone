from django.core.management.base import BaseCommand
from drive.utils import cleanup_orphaned_media_files


class Command(BaseCommand):
    help = 'Clean up orphaned files from media/uploads directory to free storage space and memory.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Scanning media storage for orphaned files...'))
        res = cleanup_orphaned_media_files()
        deleted = res['deleted_files']
        reclaimed = res['formatted_reclaimed']
        self.stdout.write(
            self.style.SUCCESS(f'Successfully purged {deleted} orphaned file(s), reclaiming {reclaimed} of storage!')
        )
