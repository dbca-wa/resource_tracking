from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
import logging
import os
import subprocess


class Command(BaseCommand):
    help = 'Reads the contents of the upload_data_cache directory and uploads observations to DAFWA'

    def handle(self, *args, **options):
        # If the upload_data_cache directory doesn't exist, return.
        if not os.path.exists(os.path.join(settings.BASE_DIR, 'upload_data_cache')):
            return
        logger = logging.getLogger('dafwa_uploads')
        try:
            connect_str = 'sftp://{}:{}@{}/{}'.format(
                settings.DAFWA_UPLOAD_USER, settings.DAFWA_UPLOAD_PASSWORD,
                settings.DAFWA_UPLOAD_HOST, settings.DAFWA_UPLOAD_DIR)
            # Read the contents of the upload_data_cache directory and upload.
            for f in os.listdir(os.path.join(settings.BASE_DIR, 'upload_data_cache')):
                path = os.path.abspath(os.path.join(settings.BASE_DIR, 'upload_data_cache', f))
                # Use lftp to tranfer each file using SFTP.
                try:
                    output = subprocess.check_output(
                        ['timeout', '10', 'lftp', connect_str, '-e', 'put -E {}; quit'.format(path)],
                        stderr=subprocess.STDOUT)
                    logger.info('Uploaded {} to DAFWA'.format(f))
                except subprocess.CalledProcessError:
                    logger.exception('Error uploading {} to DAFWA'.format(f))
                    raise CommandError('Error uploading {} to DAFWA'.format(f))
        except:
            logger.exception('Error while uploading observation data to DAFWA')
            raise CommandError('Error while uploading observation data to DAFWA')
