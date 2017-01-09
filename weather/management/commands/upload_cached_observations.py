from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import os
import subprocess


class Command(BaseCommand):
    help = 'Reads the contents of the upload_data_cache directory and uploads observations to DAFWA'

    def handle(self, *args, **options):
        # If the upload_data_cache directory doesn't exist, return.
        if not os.path.exists(os.path.join(settings.BASE_DIR, 'upload_data_cache')):
            return
        try:
            connect_str = 'sftp://{}:{}@{}/{}'.format(
                settings.DAFWA_UPLOAD_USER, settings.DAFWA_UPLOAD_PASSWORD,
                settings.DAFWA_UPLOAD_HOST, settings.DAFWA_UPLOAD_DIR)
            # Read the contents of the upload_data_cache directory and upload.
            for f in os.listdir(os.path.join(settings.BASE_DIR, 'upload_data_cache')):
                path = os.path.abspath(os.path.join(settings.BASE_DIR, 'upload_data_cache', f))
                # Use lftp to tranfer each file using SFTP.
                try:
                    subprocess.check_call(
                        ['lftp', connect_str, '-e', 'put -E {}; quit'.format(path)],
                        stderr=subprocess.STDOUT)
                    self.stdout.write(self.style.SUCCESS('Uploaded {} to DAFWA'.format(f)))
                except subprocess.CalledProcessError:
                    self.stdout.write(self.style.WARNING('Error uploading {} to DAFWA'.format(f)))
        except:
            raise CommandError('Error while uploading observation data to DAFWA')
