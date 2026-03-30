import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET'),
)

def upload_file_to_cloudinary(file_stream, public_id=None, folder='inquiries'):
    result = cloudinary.uploader.upload(
        file_stream,
        folder=folder,
        public_id=public_id,
        resource_type='auto',
        overwrite=True
    )
    return result.get('secure_url')
