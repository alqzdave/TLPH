import cloudinary
import cloudinary.uploader
import os

# Ensure your Cloudinary credentials are set in your environment variables:
# CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Path to your favicon file
file_path = "static/340-3402747_denr-department-of-environment-and-natural.ico"

# Upload to Cloudinary as a raw file (for .ico)
result = cloudinary.uploader.upload(
    file_path,
    resource_type="raw",  # Use 'raw' for .ico files
    public_id="denr-favicon",  # You can change this name
    overwrite=True
)

print("Cloudinary URL:", result["secure_url"])
