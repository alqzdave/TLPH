import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv


def main():
    # Load credentials from .env (if present) + system env
    load_dotenv()

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not cloud_name or not api_key or not api_secret:
        print("❌ Missing Cloudinary credentials.")
        print("Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in .env or system env.")
        return

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
    )

    png_path = "static/340-3402747_denr-department-of-environment-and-natural.png"
    ico_path = "static/340-3402747_denr-department-of-environment-and-natural.ico"

    if not os.path.exists(png_path):
        print(f"❌ PNG not found: {png_path}")
        return
    if not os.path.exists(ico_path):
        print(f"❌ ICO not found: {ico_path}")
        return

    # PNG for logo/preview use
    png_result = cloudinary.uploader.upload(
        png_path,
        resource_type="image",
        folder="tlph/branding",
        public_id="denr-tab-logo",
        overwrite=True,
    )

    # ICO for browser tab favicon use
    ico_result = cloudinary.uploader.upload(
        ico_path,
        resource_type="raw",
        folder="tlph/branding",
        public_id="denr-favicon",
        overwrite=True,
    )

    print("✅ Upload complete")
    print("PNG URL:", png_result.get("secure_url"))
    print("ICO URL:", ico_result.get("secure_url"))


if __name__ == "__main__":
    main()
