
from google.cloud.firestore_v1.base_query import FieldFilter
from flask import Blueprint, request, jsonify, session
from flask_mail import Message, Mail
from datetime import datetime
import random
import json
import os
import time
import hashlib
import uuid
import requests
from urllib.request import urlopen
from urllib.parse import quote_plus, quote
from firebase_admin import firestore
from firebase_auth_middleware import firebase_auth_required
import system_logs_storage


bp = Blueprint('api', __name__, url_prefix='/api')

# Store OTPs temporarily (in production, use Redis or database)
otp_storage = {}

MIMAROPA_REGION_NAMES = {'MIMAROPA', 'MIMAROPA REGION', 'REGION IV-B', 'REGION-IV-B'}
_MUNICIPALITY_CODE_CACHE = {}


def _cloudinary_enabled() -> bool:
    return all([
        os.environ.get('CLOUDINARY_CLOUD_NAME'),
        os.environ.get('CLOUDINARY_API_KEY'),
        os.environ.get('CLOUDINARY_API_SECRET')
    ])


def _cloudinary_signature(params: dict, api_secret: str) -> str:
    filtered = {k: v for k, v in params.items() if v is not None and v != ''}
    base = '&'.join([f"{k}={filtered[k]}" for k in sorted(filtered.keys())])
    return hashlib.sha1(f"{base}{api_secret}".encode('utf-8')).hexdigest()


def _upload_to_cloudinary(file_obj, folder: str):
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

    if not cloud_name or not api_key or not api_secret:
        print(f"❌ [CLOUDINARY] Missing credentials - cloud_name: {bool(cloud_name)}, api_key: {bool(api_key)}, api_secret: {bool(api_secret)}")
        return None

    print(f"🔵 [CLOUDINARY] Starting upload for {file_obj.filename} to folder: {folder}")
    
    timestamp = int(time.time())
    params_to_sign = {
        'folder': folder,
        'timestamp': timestamp
    }
    signature = _cloudinary_signature(params_to_sign, api_secret)

    filename_lower = (getattr(file_obj, 'filename', '') or '').lower()
    mimetype_lower = (getattr(file_obj, 'mimetype', '') or '').lower()
    is_image_like = mimetype_lower.startswith('image/') or filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif'))
    resource_type = 'image' if is_image_like else 'raw'

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/upload"
    print(f"🔵 [CLOUDINARY] Endpoint: {endpoint}")
    
    try:
        file_obj.stream.seek(0)
    except Exception:
        pass

    try:
        # Upload with public access - NO authentication required for viewing
        resp = requests.post(
            endpoint,
            data={
                'api_key': api_key,
                'timestamp': timestamp,
                'folder': folder,
                'signature': signature,
            },
            files={
                'file': (file_obj.filename, file_obj.stream, file_obj.mimetype or 'application/octet-stream')
            },
            timeout=30
        )

        if not resp.ok:
            print(f"❌ [CLOUDINARY] Upload failed ({resp.status_code}). Response: {resp.text[:200]}")
            return None

        payload = resp.json() or {}
        url = payload.get('secure_url') or payload.get('url')
        print(f"✅ [CLOUDINARY] Upload successful ({resource_type}): {url}")
        return url

    except requests.RequestException as e:
        print(f"❌ [CLOUDINARY] Request error: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ [CLOUDINARY] Unexpected error: {str(e)}")
        return None
    finally:
        try:
            file_obj.stream.seek(0)
        except Exception:
            pass


def _is_image_file(file_obj) -> bool:
    filename = (getattr(file_obj, 'filename', '') or '').lower()
    mimetype = (getattr(file_obj, 'mimetype', '') or '').lower()
    image_exts = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
    return mimetype.startswith('image/') or filename.endswith(image_exts)


def _upload_to_firebase_storage(file_obj, folder: str):
    """Upload file to Firebase Storage and return tokenized download URL."""
    try:
        from firebase_config import get_storage_bucket

        bucket = get_storage_bucket()
        if not bucket:
            return None

        original_name = os.path.basename((file_obj.filename or 'upload.bin').strip())
        safe_name = original_name.replace(' ', '_')
        token = str(uuid.uuid4())
        unique_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_name}"
        blob_path = f"{folder.strip('/')}/{unique_name}"

        blob = bucket.blob(blob_path)

        try:
            file_obj.stream.seek(0)
        except Exception:
            pass

        blob.upload_from_file(
            file_obj.stream,
            content_type=(file_obj.mimetype or 'application/octet-stream'),
            rewind=True
        )

        # Firebase token-based media URL
        blob.metadata = {'firebaseStorageDownloadTokens': token}
        blob.patch()

        encoded_path = quote(blob_path, safe='')
        return f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_path}?alt=media&token={token}"
    except Exception as e:
        print(f"❌ [FIREBASE_STORAGE] Upload failed: {e}")
        return None


@bp.route('/files/proxy', methods=['GET'])
def proxy_file():
    """
    Proxy endpoint for viewing/downloading files with authentication.
    Caches Cloudinary files locally to bypass 401 errors.
    Handles both remote (Cloudinary) and local (/static/) paths.
    
    Usage: /api/files/proxy?url=<encoded_cloudinary_url_or_local_path>
    """
    try:
        from flask import send_file
        from urllib.parse import unquote, quote
        import io
        import hashlib
        
        # Do not hard-require Flask session here.
        # Hosted environments may rely on Firebase auth only; URL validation below remains enforced.
        requester = session.get('user_email') if 'user_email' in session else 'anonymous'
        
        file_url = request.args.get('url', '').strip()
        if not file_url:
            return jsonify({'error': 'Missing file URL'}), 400
        
        # Decode URL
        try:
            file_url = unquote(file_url)
        except Exception:
            pass
        
        # Check if this is a local static file path
        is_local_path = file_url.startswith('/static/') or file_url.startswith('static/')
        
        # Validate
        if not ('cloudinary.com' in file_url or is_local_path or file_url.startswith('http')):
            return jsonify({'error': 'Invalid file URL'}), 400
        
        print(f"🔵 [FILE_PROXY] Request from {requester}: {file_url[:100]}...")

        def _guess_mime_and_inline(filename_hint: str, content_type_hint: str = ''):
            ext = (str(filename_hint or '').split('?')[0].split('.')[-1] or '').lower()
            ct = str(content_type_hint or '').lower()

            if 'image/' in ct:
                return ct.split(';')[0], True
            if 'application/pdf' in ct:
                return 'application/pdf', True

            ext_map = {
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
                'svg': 'image/svg+xml', 'avif': 'image/avif',
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'application/vnd.ms-excel',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'txt': 'text/plain', 'csv': 'text/csv',
            }
            mime = ext_map.get(ext, 'application/octet-stream')
            inline = mime.startswith('image/') or mime == 'application/pdf' or mime.startswith('text/')
            return mime, inline
        
        # Handle local paths directly
        if is_local_path:
            local_path = file_url.lstrip('/')
            full_path = os.path.join(os.getcwd(), local_path)
            
            if not os.path.exists(full_path):
                print(f"❌ [FILE_PROXY] Local file not found: {full_path}")
                return jsonify({'error': 'File not found'}), 404
            
            filename = os.path.basename(full_path)
            
            # Determine MIME type and whether to display inline or download
            mime_type = 'application/octet-stream'
            inline = False  # Display in browser, not download
            
            if filename.lower().endswith(('.pdf',)):
                mime_type = 'application/pdf'
                inline = True
            elif filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
                inline = True
            elif filename.lower().endswith(('.png',)):
                mime_type = 'image/png'
                inline = True
            elif filename.lower().endswith(('.gif',)):
                mime_type = 'image/gif'
                inline = True
            elif filename.lower().endswith(('.webp',)):
                mime_type = 'image/webp'
                inline = True
            elif filename.lower().endswith(('.doc', '.docx')):
                mime_type = 'application/msword'
                inline = False
            elif filename.lower().endswith(('.xls', '.xlsx')):
                mime_type = 'application/vnd.ms-excel'
                inline = False
            
            print(f"📄 [FILE_PROXY] Serving local file: {filename} ({mime_type}, inline={inline})")
            return send_file(
                full_path,
                mimetype=mime_type,
                as_attachment=not inline,
                download_name=filename if not inline else None
            )
        
        # Create cache directory (best-effort on hosted env)
        cache_dir = os.path.join('static', 'file_cache')
        can_cache = True
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as mk_err:
            print(f"⚠️  [FILE_PROXY] Cache directory unavailable: {mk_err}")
            can_cache = False
        
        # Generate cache filename from URL hash
        url_hash = hashlib.md5(file_url.encode()).hexdigest()
        
        # Try to get original filename from URL
        filename = file_url.split('/')[-1].split('?')[0] or 'download'
        if not filename or filename.startswith('v'):
            # Fallback: use hash + generic extension
            ext = '.bin'
            if any(x in file_url.lower() for x in ['.pdf', 'pdf']):
                ext = '.pdf'
            elif any(x in file_url.lower() for x in ['.doc', 'docx', 'word']):
                ext = '.docx'
            elif any(x in file_url.lower() for x in ['.jpg', '.jpeg', '.png', '.gif']):
                ext = '.pdf'  # Default for images in docs
            filename = f"cached_{url_hash}{ext}"
        
        cache_file = os.path.join(cache_dir, f"{url_hash}_{filename}") if can_cache else ''
        
        # Check if file is already cached
        if can_cache and os.path.exists(cache_file):
            print(f"✅ [FILE_PROXY] Serving from cache: {filename}")
            mime_type, inline = _guess_mime_and_inline(filename)
            return send_file(
                cache_file,
                mimetype=mime_type,
                as_attachment=not inline,
                download_name=filename if not inline else None
            )
        
        # Not cached - fetch from source
        print(f"🔄 [FILE_PROXY] Fetching from source and caching...")
        # Initialize auth with Cloudinary API credentials for HTTP Basic Auth
        auth = None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*'
        }
        
        if 'cloudinary.com' in file_url:
            api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
            api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()
            
            if api_key and api_secret:
                # Use HTTP Basic Auth with Cloudinary API credentials
                auth = (api_key, api_secret)
                print(f"🔐 [FILE_PROXY] Using Cloudinary API credentials for auth...")
        
        # Attempt 1: Direct fetch with HTTP Basic Auth (for Cloudinary)
        print(f"📥 [FILE_PROXY] Attempt 1: Fetching with auth...")
        try:
            def _safe_get(url, **kwargs):
                try:
                    return requests.get(url, **kwargs)
                except requests.RequestException as req_err:
                    print(f"⚠️  [FILE_PROXY] GET failed for {url[:90]}... -> {req_err}")
                    return None

            response = _safe_get(
                file_url,
                timeout=30,
                stream=False,
                headers=headers,
                auth=auth,
                allow_redirects=True
            )

            if response is None:
                # Treat as unauthorized/unavailable so Cloudinary fallbacks still run
                class _TmpResp:
                    status_code = 401
                    content = b''
                response = _TmpResp()
            
            if response.status_code == 200:
                print(f"✅ [FILE_PROXY] Success with auth!")
            elif response.status_code == 401:
                print(f"⚠️  [FILE_PROXY] Auth failed (401), attempting without credentials...")
                retry_resp = _safe_get(
                    file_url,
                    timeout=30,
                    stream=False,
                    headers=headers,
                    allow_redirects=True
                )
                if retry_resp is not None:
                    response = retry_resp
                if response.status_code == 200:
                    print(f"✅ [FILE_PROXY] Success without auth!")

            # Attempt 1.5 (Cloudinary fallback): if PDF/doc URL is on image/upload, retry with raw/upload path
            if response.status_code in (401, 404) and 'cloudinary.com' in file_url:
                lower_url = file_url.lower()
                if '/image/upload/' in lower_url and any(lower_url.endswith(ext) or f"{ext}?" in lower_url for ext in ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.txt', '.zip')):
                    alt_raw_url = file_url.replace('/image/upload/', '/raw/upload/')
                    print(f"⚠️  [FILE_PROXY] Trying raw/upload retry for document URL...")
                    alt_resp = _safe_get(
                        alt_raw_url,
                        timeout=30,
                        stream=False,
                        headers=headers,
                        auth=auth,
                        allow_redirects=True
                    )
                    if alt_resp is not None and alt_resp.status_code == 200:
                        print("✅ [FILE_PROXY] Success via raw/upload URL")
                        response = alt_resp

            # Attempt 2 (Cloudinary fallback): signed private download API
            if response.status_code == 401 and 'cloudinary.com' in file_url:
                print("⚠️  [FILE_PROXY] Delivery URL unauthorized. Trying Cloudinary private download API...")
                try:
                    from urllib.parse import urlparse

                    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
                    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
                    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

                    parsed = urlparse(file_url)
                    path = parsed.path or ''
                    marker = '/upload/'
                    idx = path.find(marker)

                    if idx != -1 and cloud_name and api_key and api_secret:
                        asset_part = path[idx + len(marker):]
                        parts = [p for p in asset_part.split('/') if p]

                        # remove version segment (e.g., v1774686013)
                        if parts and parts[0].startswith('v') and parts[0][1:].isdigit():
                            parts = parts[1:]

                        if parts:
                            original_parts = list(parts)
                            last = parts[-1]
                            basename = None
                            file_format = None
                            if '.' in last:
                                basename, ext = last.rsplit('.', 1)
                                file_format = ext.lower()

                            # Try both public_id variants because raw assets may keep extension in public_id
                            public_id_candidates = []
                            if basename:
                                parts_no_ext = list(original_parts)
                                parts_no_ext[-1] = basename
                                public_id_candidates.append('/'.join(parts_no_ext))
                            public_id_candidates.append('/'.join(original_parts))

                            timestamp = int(time.time())

                            # PDFs/docs are often stored as raw; images as image.
                            # Try both resource types and both with/without format.
                            resource_types = ['image', 'raw']
                            if file_format and file_format in ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv'):
                                resource_types = ['raw', 'image']

                            fallback_response = None
                            for resource_type in resource_types:
                                private_download_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/download"

                                for public_id in public_id_candidates:
                                    # Some accounts/resources require delivery type in signature.
                                    for include_type in (True, False):
                                        base_sign_payload = {
                                            'public_id': public_id,
                                            'timestamp': timestamp,
                                        }

                                        if include_type:
                                            base_sign_payload['type'] = 'upload'

                                        # First try with format when useful
                                        if file_format:
                                            params_with_format = {
                                                'public_id': public_id,
                                                'timestamp': timestamp,
                                                'api_key': api_key,
                                                'format': file_format,
                                            }
                                            sign_payload_with_format = dict(base_sign_payload)
                                            sign_payload_with_format['format'] = file_format

                                            if include_type:
                                                params_with_format['type'] = 'upload'

                                            params_with_format['signature'] = _cloudinary_signature(sign_payload_with_format, api_secret)

                                            fallback_response = requests.get(
                                                private_download_url,
                                                params=params_with_format,
                                                timeout=30,
                                                stream=False,
                                                headers=headers,
                                                allow_redirects=True,
                                            )
                                            print(f"📥 [FILE_PROXY] Private download ({resource_type}, with format, type={include_type}, pid={public_id}) status: {fallback_response.status_code}")
                                            if fallback_response.status_code == 200:
                                                break

                                        # Retry without format (some assets fail if forced)
                                        params_without_format = {
                                            'public_id': public_id,
                                            'timestamp': timestamp,
                                            'api_key': api_key,
                                            'signature': _cloudinary_signature(base_sign_payload, api_secret),
                                        }

                                        if include_type:
                                            params_without_format['type'] = 'upload'

                                        fallback_response = requests.get(
                                            private_download_url,
                                            params=params_without_format,
                                            timeout=30,
                                            stream=False,
                                            headers=headers,
                                            allow_redirects=True,
                                        )
                                        print(f"📥 [FILE_PROXY] Private download ({resource_type}, no format, type={include_type}, pid={public_id}) status: {fallback_response.status_code}")
                                        if fallback_response.status_code == 200:
                                            break

                                    if fallback_response is not None and fallback_response.status_code == 200:
                                        break

                                if fallback_response is not None and fallback_response.status_code == 200:
                                    break

                            if fallback_response is not None:
                                response = fallback_response
                except Exception as fallback_err:
                    print(f"⚠️  [FILE_PROXY] Private download fallback failed: {fallback_err}")

            # Attempt 3 (Cloudinary fallback): make legacy asset anonymous via explicit API, then retry original URL
            if response.status_code in (401, 404) and 'cloudinary.com' in file_url:
                print("⚠️  [FILE_PROXY] Trying explicit API fallback to unrestrict legacy asset...")
                try:
                    from urllib.parse import urlparse

                    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
                    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
                    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

                    parsed = urlparse(file_url)
                    path = parsed.path.strip('/')
                    segs = [s for s in path.split('/') if s]

                    # Expected: /<cloud_name>/<resource_type>/<type>/v123/.../<filename>
                    if len(segs) >= 5 and cloud_name and api_key and api_secret:
                        resource_type = segs[1]
                        delivery_type = segs[2]

                        asset_parts = segs[3:]
                        if asset_parts and asset_parts[0].startswith('v') and asset_parts[0][1:].isdigit():
                            asset_parts = asset_parts[1:]

                        if asset_parts:
                            last = asset_parts[-1]
                            if '.' in last and resource_type != 'raw':
                                asset_parts[-1] = last.rsplit('.', 1)[0]

                            public_id = '/'.join(asset_parts)

                            explicit_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/{resource_type}/explicit"
                            explicit_resp = requests.post(
                                explicit_url,
                                auth=(api_key, api_secret),
                                data={
                                    'public_id': public_id,
                                    # Force legacy assets back to publicly deliverable mode
                                    'type': 'upload',
                                    'access_mode': 'public',
                                    'access_control': json.dumps([{'access_type': 'anonymous'}]),
                                    'invalidate': 'true',
                                },
                                timeout=30,
                            )

                            print(f"📥 [FILE_PROXY] Explicit update status: {explicit_resp.status_code}")

                            # Retry original URL after explicit update
                            if explicit_resp.status_code in (200, 201):
                                try:
                                    explicit_json = explicit_resp.json() or {}
                                except Exception:
                                    explicit_json = {}

                                # Prefer original URL first (more stable in this project), then secure_url
                                retry_candidates = [file_url]
                                alt_secure = (explicit_json.get('secure_url') or '').strip()
                                if alt_secure and alt_secure != file_url:
                                    retry_candidates.append(alt_secure)

                                for retry_url in retry_candidates:
                                    try:
                                        response = requests.get(
                                            retry_url,
                                            timeout=30,
                                            stream=False,
                                            headers=headers,
                                            allow_redirects=True,
                                        )
                                        print(f"📥 [FILE_PROXY] Retry after explicit ({retry_url[:90]}...) status: {response.status_code}")
                                        if response.status_code == 200:
                                            break
                                    except requests.RequestException as retry_err:
                                        print(f"⚠️  [FILE_PROXY] Retry URL failed: {retry_err}")
                except Exception as explicit_err:
                    print(f"⚠️  [FILE_PROXY] Explicit fallback failed: {explicit_err}")

            # Attempt 4 (Cloudinary fallback): Admin API download_backup (returns file bytes)
            if response.status_code in (401, 404) and 'cloudinary.com' in file_url:
                print("⚠️  [FILE_PROXY] Trying download_backup fallback...")
                try:
                    from urllib.parse import urlparse

                    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
                    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
                    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

                    parsed = urlparse(file_url)
                    path = parsed.path.strip('/')
                    segs = [s for s in path.split('/') if s]

                    # /<cloud>/<resource_type>/<type>/v<version>/<public_id...>
                    if len(segs) >= 5 and cloud_name and api_key and api_secret:
                        resource_type = segs[1]
                        delivery_type = segs[2]

                        asset_parts = segs[3:]
                        url_version_num = None
                        if asset_parts and asset_parts[0].startswith('v') and asset_parts[0][1:].isdigit():
                            url_version_num = int(asset_parts[0][1:])
                            asset_parts = asset_parts[1:]

                        if asset_parts:
                            last = asset_parts[-1]
                            if '.' in last and resource_type != 'raw':
                                asset_parts[-1] = last.rsplit('.', 1)[0]
                            public_id = '/'.join(asset_parts)

                            # Try multiple resource detail endpoints; public_id may include slashes
                            details_candidates = [
                                (resource_type, delivery_type or 'upload'),
                                (resource_type, 'upload'),
                            ]
                            if resource_type == 'image':
                                details_candidates.append(('raw', delivery_type or 'upload'))
                                details_candidates.append(('raw', 'upload'))

                            details_resp = None
                            for cand_resource, cand_type in details_candidates:
                                details_url = (
                                    f"https://api.cloudinary.com/v1_1/{cloud_name}/resources/"
                                    f"{cand_resource}/{cand_type}/{quote(public_id, safe='/')}"
                                )
                                details_resp = requests.get(
                                    details_url,
                                    auth=(api_key, api_secret),
                                    params={'versions': 'true'},
                                    timeout=30,
                                )
                                print(f"📥 [FILE_PROXY] Resource details ({cand_resource}/{cand_type}) status: {details_resp.status_code}")
                                if details_resp.status_code == 200:
                                    break

                            if details_resp is not None and details_resp.status_code == 200:
                                details = details_resp.json() or {}
                                asset_id = details.get('asset_id')
                                version_id = details.get('version_id')
                                versions_obj = details.get('versions')

                                # pick matching version_id if URL version exists
                                if not version_id and url_version_num and isinstance(versions_obj, list):
                                    for ver in versions_obj:
                                        if isinstance(ver, dict) and int(ver.get('version') or 0) == url_version_num and ver.get('version_id'):
                                            version_id = ver.get('version_id')
                                            break

                                # versions can be a dict in some responses
                                if not version_id and url_version_num and isinstance(versions_obj, dict):
                                    ver_entry = versions_obj.get(str(url_version_num)) or versions_obj.get(url_version_num)
                                    if isinstance(ver_entry, dict):
                                        version_id = ver_entry.get('version_id') or ver_entry.get('id')
                                    elif isinstance(ver_entry, str):
                                        version_id = ver_entry

                                # Fallback: pick any available version_id if top-level/matching not found
                                if not version_id and isinstance(versions_obj, list):
                                    for ver in versions_obj:
                                        if not isinstance(ver, dict):
                                            continue
                                        if ver.get('version_id'):
                                            version_id = ver.get('version_id')
                                            break
                                        if ver.get('id'):
                                            version_id = ver.get('id')
                                            break

                                if not version_id and isinstance(versions_obj, dict):
                                    for _, ver_entry in versions_obj.items():
                                        if isinstance(ver_entry, dict):
                                            cand = ver_entry.get('version_id') or ver_entry.get('id')
                                            if cand:
                                                version_id = cand
                                                break
                                        elif isinstance(ver_entry, str):
                                            version_id = ver_entry
                                            break

                                if not version_id:
                                    print(f"⚠️  [FILE_PROXY] versions payload type={type(versions_obj).__name__} keys={list(versions_obj.keys())[:5] if isinstance(versions_obj, dict) else 'n/a'}")

                                print(f"📥 [FILE_PROXY] Backup params asset_id={bool(asset_id)} version_id={bool(version_id)}")

                                if asset_id and version_id:
                                    timestamp = int(time.time())
                                    sign_payload = {
                                        'asset_id': asset_id,
                                        'timestamp': timestamp,
                                        'version_id': version_id,
                                    }
                                    signature = _cloudinary_signature(sign_payload, api_secret)

                                    backup_url = f"https://api.cloudinary.com/v1_1/{cloud_name}/download_backup"
                                    response = requests.get(
                                        backup_url,
                                        params={
                                            'asset_id': asset_id,
                                            'version_id': version_id,
                                            'timestamp': timestamp,
                                            'api_key': api_key,
                                            'signature': signature,
                                        },
                                        timeout=30,
                                        stream=False,
                                        headers=headers,
                                        allow_redirects=True,
                                    )
                                    print(f"📥 [FILE_PROXY] download_backup status: {response.status_code}")
                                else:
                                    print("⚠️  [FILE_PROXY] Skipping download_backup: missing asset_id/version_id")
                except Exception as backup_err:
                    print(f"⚠️  [FILE_PROXY] download_backup fallback failed: {backup_err}")

            # Attempt 5 (Cloudinary fallback): signed delivery URLs for restricted assets
            if response.status_code in (401, 404) and 'cloudinary.com' in file_url:
                print("⚠️  [FILE_PROXY] Trying signed delivery URL fallback...")
                try:
                    from urllib.parse import urlparse
                    import cloudinary
                    import cloudinary.utils

                    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
                    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
                    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

                    if cloud_name and api_key and api_secret:
                        cloudinary.config(
                            cloud_name=cloud_name,
                            api_key=api_key,
                            api_secret=api_secret,
                            secure=True,
                        )

                        parsed = urlparse(file_url)
                        path = parsed.path or ''
                        marker = '/upload/'
                        idx = path.find(marker)

                        if idx != -1:
                            asset_part = path[idx + len(marker):]
                            parts = [p for p in asset_part.split('/') if p]

                            if parts and parts[0].startswith('v') and parts[0][1:].isdigit():
                                parts = parts[1:]

                            if parts:
                                original_parts = list(parts)
                                last = parts[-1]
                                fmt = None
                                public_id_candidates = []
                                if '.' in last:
                                    base, ext = last.rsplit('.', 1)
                                    fmt = ext.lower()
                                    parts_no_ext = list(original_parts)
                                    parts_no_ext[-1] = base
                                    public_id_candidates.append('/'.join(parts_no_ext))
                                public_id_candidates.append('/'.join(original_parts))

                                resource_types = ['image', 'raw']
                                delivery_types = ['upload', 'private', 'authenticated']

                                signed_ok = False
                                for resource_type in resource_types:
                                    if signed_ok:
                                        break
                                    for public_id in public_id_candidates:
                                        for delivery_type in delivery_types:
                                            url_opts = {
                                                'resource_type': resource_type,
                                                'type': delivery_type,
                                                'secure': True,
                                                'sign_url': True,
                                            }
                                            # For raw assets, format can break if public_id already includes extension
                                            if fmt and resource_type != 'raw':
                                                url_opts['format'] = fmt

                                            signed_url, _ = cloudinary.utils.cloudinary_url(public_id, **url_opts)
                                            signed_resp = requests.get(
                                                signed_url,
                                                timeout=30,
                                                stream=False,
                                                headers=headers,
                                                allow_redirects=True,
                                            )
                                            print(f"📥 [FILE_PROXY] Signed URL ({resource_type}/{delivery_type}, pid={public_id}) status: {signed_resp.status_code}")
                                            if signed_resp.status_code == 200:
                                                response = signed_resp
                                                signed_ok = True
                                                break
                                        if signed_ok:
                                            break
                except Exception as signed_err:
                    print(f"⚠️  [FILE_PROXY] Signed URL fallback failed: {signed_err}")
            
            if response.status_code == 200:
                # Cache the file
                if can_cache:
                    try:
                        with open(cache_file, 'wb') as f:
                            f.write(response.content)
                        print(f"✅ [FILE_PROXY] Cached: {filename} ({len(response.content)} bytes)")
                    except IOError as cache_err:
                        print(f"⚠️  [FILE_PROXY] Cache write failed: {cache_err}")
                else:
                    print("ℹ️  [FILE_PROXY] Skipping cache write (cache unavailable)")

                resp_ct = ''
                try:
                    resp_ct = response.headers.get('Content-Type', '')
                except Exception:
                    pass
                mime_type, inline = _guess_mime_and_inline(filename, resp_ct)
                
                # Return file
                if can_cache and os.path.exists(cache_file):
                    return send_file(
                        cache_file,
                        mimetype=mime_type,
                        as_attachment=not inline,
                        download_name=filename if not inline else None
                    )
                else:
                    return send_file(
                        io.BytesIO(response.content),
                        mimetype=mime_type,
                        as_attachment=not inline,
                        download_name=filename if not inline else None
                    )
            else:
                print(f"❌ [FILE_PROXY] HTTP {response.status_code}")
                if response.status_code in (401, 404) and 'cloudinary.com' in file_url and file_url.lower().endswith('.pdf'):
                    return jsonify({
                        'error': 'Unable to access this Cloudinary PDF. Asset is restricted and backup version is unavailable.'
                    }), 502
                return jsonify({'error': f'Failed to fetch: {response.status_code}'}), 502
                
        except requests.RequestException as fetch_err:
            print(f"❌ [FILE_PROXY] Request failed: {str(fetch_err)}")
            return jsonify({'error': 'Failed to retrieve file'}), 502
    
    except Exception as e:
        print(f"❌ [FILE_PROXY] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Server error'}), 500


def _normalize_muni_name(name: str) -> str:
    return ' '.join(str(name or '').strip().upper().replace('’', "'").replace('`', "'").split())


def _strip_city_muni_suffix(name: str) -> str:
    v = _normalize_muni_name(name)
    for suffix in (' CITY', ' MUNICIPALITY'):
        if v.endswith(suffix):
            v = v[: -len(suffix)].strip()
    return v


def _fetch_json(url: str):
    with urlopen(url, timeout=12) as resp:
        payload = resp.read().decode('utf-8')
        return json.loads(payload)


def _load_mimaropa_municipalities_from_firestore():
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        for key in ('REGION-IV-B', 'MIMAROPA'):
            doc = db.collection('municipalities').document(key).get()
            if not doc.exists:
                continue

            data = doc.to_dict() or {}
            items = data.get('items') or data.get('municipalities') or []
            rows = []

            if isinstance(items, list):
                rows = items
            elif isinstance(items, dict):
                rows = list(items.values())

            names = set()
            for row in rows:
                if isinstance(row, str):
                    name = row.strip()
                elif isinstance(row, dict):
                    name = str(
                        row.get('municipality')
                        or row.get('municipality_name')
                        or row.get('name')
                        or ''
                    ).strip()
                else:
                    name = ''

                if name:
                    names.add(name)

            if names:
                return sorted(names)

        return []
    except Exception as e:
        print(f"[WARN] Firestore municipality lookup failed: {e}")
        return []


def _load_mimaropa_municipalities_from_psgc():
    try:
        url = 'https://psgc.gitlab.io/api/regions/174000000/cities-municipalities/'
        rows = _fetch_json(url)
        names = sorted({str(row.get('name') or '').strip() for row in rows if str(row.get('name') or '').strip()})
        return names
    except Exception as e:
        print(f"[WARN] PSGC municipality list fetch failed: {e}")
        return []


def _resolve_municipality_code(municipality_name: str):
    key = _normalize_muni_name(municipality_name)
    if not key:
        return None

    if key in _MUNICIPALITY_CODE_CACHE:
        return _MUNICIPALITY_CODE_CACHE[key]

    key_stripped = _strip_city_muni_suffix(key)

    try:
        rows = _fetch_json('https://psgc.gitlab.io/api/regions/174000000/cities-municipalities/')
        candidate = None

        for row in rows:
            name = str(row.get('name') or '').strip()
            code_val = str(row.get('code') or '').strip()
            if not name or not code_val:
                continue

            normalized = _normalize_muni_name(name)
            _MUNICIPALITY_CODE_CACHE[normalized] = code_val

            if normalized == key:
                candidate = code_val
                break
            if _strip_city_muni_suffix(normalized) == key_stripped:
                candidate = code_val

        return candidate
    except Exception as e:
        print(f"[WARN] PSGC municipality code lookup failed: {e}")
        return None


@bp.route('/locations/mimaropa/municipalities', methods=['GET'])
def get_mimaropa_municipalities():
    """Return MIMAROPA municipalities from Firestore, fallback to PSGC API."""
    municipalities = _load_mimaropa_municipalities_from_firestore()
    source = 'firestore'
    if not municipalities:
        municipalities = _load_mimaropa_municipalities_from_psgc()
        source = 'psgc'
    return jsonify({'success': True, 'municipalities': municipalities, 'source': source})


@bp.route('/locations/mimaropa/barangays', methods=['GET'])
def get_mimaropa_barangays():
    """Return real barangays for a municipality (PSGC API)."""
    municipality = (request.args.get('municipality') or '').strip()
    if not municipality:
        return jsonify({'success': False, 'error': 'municipality is required'}), 400

    muni_code = _resolve_municipality_code(municipality)
    if not muni_code:
        return jsonify({'success': True, 'barangays': [], 'municipality': municipality})

    try:
        url = f'https://psgc.gitlab.io/api/cities-municipalities/{quote_plus(muni_code)}/barangays/'
        rows = _fetch_json(url)
        barangays = sorted({str(row.get('name') or '').strip() for row in rows if str(row.get('name') or '').strip()})
        return jsonify({'success': True, 'barangays': barangays, 'municipality': municipality})
    except Exception as e:
        print(f"[WARN] PSGC barangay fetch failed for {municipality}: {e}")
        return jsonify({'success': True, 'barangays': [], 'municipality': municipality})

# ==================== HELPERS ====================

def detect_device_from_request():
    """Detect device type from request headers"""
    user_agent = request.headers.get('User-Agent', '')
    return system_logs_storage.detect_device_type(user_agent)

def _normalize_municipality(value: str) -> str:
    return ' '.join(str(value or '').strip().split())


def get_user_municipality(user_id: str = None, user_email: str = None) -> str:
    """Get municipality from user document in Firestore"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                user_role = user_data.get('role', '')
                if user_role in ['national', 'national_admin']:
                    # National admin: no municipality restriction, no debug
                    return None
                if user_role in ['regional', 'regional_admin']:
                    print(f"[DEBUG] get_user_municipality(user_id={user_id}) -> 'regional' (regional admin)")
                    return 'regional'
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    normalized = _normalize_municipality(municipality)
                    print(f"[DEBUG] get_user_municipality(user_id={user_id}) -> '{normalized}' (raw: '{municipality}')")
                    return normalized

        if user_email:
            docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                user_role = user_data.get('role', '')
                if user_role in ['national', 'national_admin']:
                    # National admin: no municipality restriction, no debug
                    return None
                if user_role in ['regional', 'regional_admin']:
                    print(f"[DEBUG] get_user_municipality(user_email={user_email}) -> 'regional' (regional admin)")
                    return 'regional'
                municipality = user_data.get('municipality') or user_data.get('municipality_name')
                if municipality:
                    normalized = _normalize_municipality(municipality)
                    print(f"[DEBUG] get_user_municipality(user_email={user_email}) -> '{normalized}' (raw: '{municipality}')")
                    return normalized

        # Only print debug for non-national
        print(f"[DEBUG] get_user_municipality - no municipality found for user_id={user_id}, user_email={user_email}")
        return 'unknown'
    except Exception as e:
        print(f'[ERROR] Getting user municipality: {e}')
        return 'unknown'

def get_user_region(user_id: str = None, user_email: str = None) -> str:
    """Get region from user document in Firestore"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        if user_id:
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict() or {}
                # Prioritize regionName (full name like MIMAROPA) over region code (like 4B)
                region = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                if region:
                    print(f"[DEBUG] get_user_region(user_id={user_id}) -> '{region}'")
                    return region

        if user_email:
            docs = db.collection('users').where(filter=FieldFilter('email', '==', user_email)).limit(1).stream()
            for doc in docs:
                user_data = doc.to_dict() or {}
                # Prioritize regionName (full name like MIMAROPA) over region code (like 4B)
                region = user_data.get('regionName') or user_data.get('region_name') or user_data.get('region')
                if region:
                    print(f"[DEBUG] get_user_region(user_email={user_email}) -> '{region}'")
                    return region

        print(f"[DEBUG] get_user_region - no region found for user_id={user_id}, user_email={user_email}")
        return 'unknown'
    except Exception as e:
        print(f'[ERROR] Getting user region: {e}')
        return 'unknown'

# Store users temporarily (in production, use database)
users_db = {
    'municipal@gmail.com': {
        'password': '123456',
        'role': 'municipal',
        'data': {
            'firstName': 'Municipal',
            'lastName': 'Admin',
            'email': 'municipal@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Makati',
            'province': 'Metro Manila'
        }
    },
    'regional@gmail.com': {
        'password': '123456',
        'role': 'regional',
        'data': {
            'firstName': 'Regional',
            'lastName': 'Admin',
            'email': 'regional@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Regional',
            'province': 'National'
        }
    },
    'superadmin@gmail.com': {
        'password': '123456',
        'role': 'super-admin',
        'data': {
            'firstName': 'Super',
            'lastName': 'Admin',
            'email': 'superadmin@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'Admin',
            'province': 'National'
        }
    },
    'national@gmail.com': {
        'password': '123456',
        'role': 'national',
        'data': {
            'firstName': 'National',
            'lastName': 'Admin',
            'email': 'national@gmail.com',
            'phone': '000-000-0000',
            'municipality': 'National',
            'province': 'National'
        }
    }
}

# Mail instance will be initialized later
mail = None

def init_mail(mail_instance):
    global mail
    mail = mail_instance

@bp.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400
        
        # Check if mail is configured
        if not mail:
            return jsonify({
                'success': False, 
                'message': 'Email service not configured. Please contact administrator.'
            }), 500
        
        # Generate 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP (expires in 10 minutes)
        otp_storage[email] = otp
        
        # Send email
        msg = Message(
            subject='DENR TLPH - Email Verification Code',
            recipients=[email],
            body=f'''
Dear User,

Your verification code for DENR TLPH registration is: {otp}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

Best regards,
DENR TLPH Team
            '''
        )
        
        mail.send(msg)
        
        return jsonify({'success': True, 'message': 'OTP sent successfully'})
    
    except Exception as e:
        print(f'Error sending OTP: {str(e)}')
        return jsonify({'success': False, 'message': f'Failed to send OTP: {str(e)}'}), 500

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        
        if not email or not otp:
            return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400
        
        # Check if OTP matches
        stored_otp = otp_storage.get(email)
        
        if not stored_otp:
            return jsonify({'success': False, 'message': 'OTP expired or not found'}), 400
        
        if stored_otp == otp:
            # Remove OTP after successful verification
            del otp_storage[email]
            return jsonify({'success': True, 'message': 'OTP verified successfully'})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    except Exception as e:
        print(f'Error verifying OTP: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('applicationType', 'user')  # Default to 'user'

        # Map application types to roles
        role_mapping = {
            'tenant': 'user',
            'cooperative': 'user',
            'agribusiness': 'user',
            'research': 'user',
            'municipal': 'municipal',
            'national': 'national',
            'regional': 'regional',
            'super-admin': 'super-admin'
        }

        user_role = role_mapping.get(role, 'user')
        
        # Get municipality from current user (if municipal user creating account)
        # or from request data, normalized for consistency
        municipality_scope = 'unknown'
        if session.get('user_role') == 'municipal' and session.get('user_email'):
            current_email = session.get('user_email')
            current_user = users_db.get(current_email)
            if current_user:
                municipality_scope = _normalize_municipality(current_user.get('data', {}).get('municipality', 'unknown'))
        
        if municipality_scope == 'unknown':
            municipality_scope = _normalize_municipality(
                data.get('municipality')
                or data.get('data', {}).get('municipality')
                or 'unknown'
            )

        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400

        # Only allow municipal users to add users with their own province/municipality
        if session.get('user_role') == 'municipal':
            current_user = users_db.get(session.get('user_email'))
            if not current_user:
                return jsonify({'success': False, 'message': 'Session user not found'}), 403
            # Overwrite province and municipality in data
            if 'data' not in data:
                data['data'] = {}
            data['province'] = current_user['data'].get('province', '')
            data['municipality'] = current_user['data'].get('municipality', '')
            data['data']['province'] = current_user['data'].get('province', '')
            data['data']['municipality'] = current_user['data'].get('municipality', '')

        # Check if user already exists
        if email in users_db:
            system_logs_storage.add_system_log(
                municipality=municipality_scope,
                user=session.get('user_email', email),
                action='CREATE_ACCOUNT_ATTEMPT',
                target='User Account',
                target_id=email,
                module='USER_MANAGEMENT',
                outcome='FAILED',
                message=f'Account creation failed: {email} already exists',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
            return jsonify({'success': False, 'message': 'User already exists'}), 400

        # Store user (in production, hash password and use database)
        users_db[email] = {
            'password': password,
            'role': user_role,
            'data': data
        }

        system_logs_storage.add_system_log(
            municipality=municipality_scope,
            user=session.get('user_email', email),
            action='CREATE_ACCOUNT',
            target='User Account',
            target_id=email,
            module='USER_MANAGEMENT',
            outcome='SUCCESS',
            message=f'Created account for {email} with role {user_role}',
            device_type=detect_device_from_request(),
            user_agent=request.headers.get('User-Agent', ''),
            metadata={
                'created_email': email,
                'created_role': user_role,
                'municipality': municipality_scope
            }
        )

        return jsonify({'success': True, 'message': 'Registration successful', 'role': user_role})

    except Exception as e:
        print(f'Error registering user: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        # Check if user exists
        user = users_db.get(email)
        
        if not user:
            # Log failed login attempt
            device_type = detect_device_from_request()
            user_agent = request.headers.get('User-Agent', '')
            request_ip = system_logs_storage.extract_request_ip(request)
            municipality = 'unknown'  # User not found, can't fetch municipality
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - user not found',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent
            )
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Verify password (in production, use proper password hashing)
        if user['password'] != password:
            # Log failed login attempt - get municipality from user data
            municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown'))
            device_type = detect_device_from_request()
            user_agent = request.headers.get('User-Agent', '')
            request_ip = system_logs_storage.extract_request_ip(request)
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=email,
                action='LOGIN_ATTEMPT',
                target='Authentication',
                module='AUTH',
                outcome='FAILED',
                message='Invalid credentials - wrong password',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent
            )
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
        # Get municipality from user data - normalize it for consistency
        municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown'))
        
        # Set session
        session['user_email'] = email
        session['user_role'] = user['role']
        session['municipality'] = municipality
        session['user_municipality'] = municipality
        session['province'] = user.get('data', {}).get('province', '')
        session['user_province'] = user.get('data', {}).get('province', '')
        
        # Log successful login with normalized municipality from user data
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=email,
            action='LOGIN',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {email} logged in successfully',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )
        
        # Determine redirect URL based on role
        redirect_urls = {
            'user': '/user/dashboard',
            'municipal': '/municipal/dashboard',
            'national': '/national/dashboard',
            'regional': '/regional/dashboard',
            'super-admin': '/super-admin/dashboard'
        }
        
        redirect_url = redirect_urls.get(user['role'], '/user/dashboard')
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'role': user['role'],
            'redirect': redirect_url
        })
    
    except Exception as e:
        print(f'Error logging in: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/set-session', methods=['POST'])
def set_session():
    """Set Flask session after Firebase authentication"""
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        user_role = data.get('user_role')
        user_id = data.get('user_id')

        if not user_email or not user_role or not user_id:
            return jsonify({'success': False, 'message': 'Missing user_email, user_role, or user_id'}), 400

        # Set session
        session.permanent = True
        session['user_email'] = user_email
        session['user_role'] = user_role
        session['user_id'] = user_id

        # Get municipality from user document - always fetch from Firestore to ensure match
        municipality = get_user_municipality(user_id=user_id, user_email=user_email)
        session['municipality'] = municipality
        session['user_municipality'] = municipality

        # Get region from user document
        region = get_user_region(user_id=user_id, user_email=user_email)
        session['region'] = region
        session['user_region'] = region

        print(f'Session set for {user_email} with role {user_role} and user_id {user_id}')

        # Log successful login with municipality fetched from Firestore users collection
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=user_email,
            action='LOGIN',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {user_email} ({user_role}) logged in successfully via Firebase',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )

        if user_role in {'municipal', 'municipal_admin'}:
            print(f'[LOGIN_CAPTURE] Recording login event for {user_email} in municipality={municipality}, region={region}')
            system_logs_storage.add_regional_system_log(
                region=region,
                municipality=municipality,
                user=user_email,
                user_id=user_id,
                role=user_role,
                action='LOGIN',
                target='Authentication',
                target_id=user_id,
                module='AUTH',
                outcome='SUCCESS',
                message=f'Municipal admin {user_email} logged in.',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent,
                metadata={'source': 'set-session'}
            )
            print(f'[LOGIN_CAPTURE] ✅ Login event recorded successfully for {user_email}')

        return jsonify({'success': True, 'message': 'Session set successfully'})
    
    except Exception as e:
        print(f'Error setting session: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/logout', methods=['POST'])
def logout():
    """Clear Flask session on logout"""
    try:
        # Capture user info before clearing session
        user_email = session.get('user_email', 'unknown')
        user_id = session.get('user_id')
        user_role = session.get('user_role', '')
        region = session.get('region') or session.get('user_region') or get_user_region(user_id=user_id, user_email=user_email)
        
        # Get fresh municipality from Firestore to ensure consistency
        municipality = get_user_municipality(user_id=user_id, user_email=user_email) if user_email != 'unknown' else 'unknown'
        
        # Log logout with fresh municipality from Firestore
        device_type = detect_device_from_request()
        user_agent = request.headers.get('User-Agent', '')
        request_ip = system_logs_storage.extract_request_ip(request)
        system_logs_storage.add_system_log(
            municipality=municipality,
            user=user_email,
            action='LOGOUT',
            target='Authentication',
            module='AUTH',
            outcome='SUCCESS',
            message=f'User {user_email} logged out',
            ip_address=request_ip,
            device_type=device_type,
            user_agent=user_agent
        )

        if user_role in {'municipal', 'municipal_admin'}:
            print(f'[LOGOUT_CAPTURE] Recording logout event for {user_email} in municipality={municipality}, region={region}')
            system_logs_storage.add_regional_system_log(
                region=region,
                municipality=municipality,
                user=user_email,
                user_id=user_id,
                role=user_role,
                action='LOGOUT',
                target='Authentication',
                target_id=user_id,
                module='AUTH',
                outcome='SUCCESS',
                message=f'Municipal admin {user_email} logged out.',
                ip_address=request_ip,
                device_type=device_type,
                user_agent=user_agent,
                metadata={'source': 'logout'}
            )
            print(f'[LOGOUT_CAPTURE] ✅ Logout event recorded successfully for {user_email}')
        
        session.clear()
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    except Exception as e:
        print(f'Error logging out: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/check-session', methods=['GET'])
def check_session():
    """Quick session check for instant auth verification"""
    if 'user_email' in session:
        role = session.get('user_role', '')
        user_email = session.get('user_email', 'unknown')
        user_id = session.get('user_id')
        
        # Get fresh municipality from Firestore or users_db
        if user_email != 'unknown':
            # Try to get from Firestore first (Firebase users)
            if user_id:
                municipality = get_user_municipality(user_id=user_id, user_email=user_email)
            else:
                # Fall back to users_db (demo users)
                user = users_db.get(user_email)
                municipality = _normalize_municipality(user.get('data', {}).get('municipality', 'unknown')) if user else 'unknown'
        else:
            municipality = 'unknown'
        
        if role in ['municipal', 'municipal_admin']:
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=user_email,
                action='SESSION_CHECK',
                target='Session',
                module='AUTH',
                outcome='SUCCESS',
                message='Municipal session validated',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )

        profile_name = ''
        try:
            profile = _resolve_user_profile(user_id or '', user_email)
            profile_name = str(profile.get('name') or '').strip()
        except Exception:
            profile_name = ''

        return jsonify({
            'authenticated': True,
            'role': role,
            'email': user_email,
            'user_id': user_id,
            'name': profile_name,
        })
    return jsonify({'authenticated': False}), 401

@bp.route('/upload-profile-photo', methods=['POST'])
@firebase_auth_required
def upload_profile_photo():
    """Upload profile photo to server and return the URL"""
    try:
        from werkzeug.utils import secure_filename

        user_id = session.get('user_id') or request.form.get('userId')
        if not user_id:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401

        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        photo_url = None
        if _cloudinary_enabled():
            photo_url = _upload_to_cloudinary(file, 'tlph/profiles')

        if not photo_url:
            upload_dir = os.path.join('static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)

            # Use uid as filename so each user has one photo (overwrites old one)
            filename = f"{user_id}.{ext}"
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            photo_url = f"/static/uploads/profiles/{filename}"

        return jsonify({'success': True, 'photoURL': photo_url})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/upload-inventory-image', methods=['POST'])
def upload_inventory_image():
    """Upload inventory image/permit to server filesystem (no Firebase Storage CORS issues)"""
    try:
        from werkzeug.utils import secure_filename

        user_id = request.form.get('userId', 'unknown')
        file_type = request.form.get('fileType', 'image')  # 'image' or 'permit'

        file_key = 'image' if file_type == 'image' else 'permit'
        if file_key not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files[file_key]
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        local_fallback_enabled = (
            str(os.environ.get('ALLOW_LOCAL_UPLOAD_FALLBACK', '')).strip().lower() in ('1', 'true', 'yes')
            or request.host.startswith('127.0.0.1')
            or request.host.startswith('localhost')
        )

        allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed:
            return jsonify({'success': False, 'error': f'Invalid file type: {ext}'}), 400

        url = None
        backend = 'none'
        if _cloudinary_enabled():
            url = _upload_to_cloudinary(file, f"tlph/inventory/{user_id}")
            if url:
                backend = 'cloudinary'

        if not url:
            url = _upload_to_firebase_storage(file, f"tlph/inventory/{user_id}")
            if url:
                backend = 'firebase_storage'

        if not url and local_fallback_enabled:
            upload_dir = os.path.join('static', 'uploads', 'inventory', user_id)
            os.makedirs(upload_dir, exist_ok=True)

            filename = f"{file_type}_{int(time.time())}_{secure_filename(file.filename)}"
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            url = f"/static/uploads/inventory/{user_id}/{filename}"
            backend = 'local_static'

        if not url:
            return jsonify({
                'success': False,
                'error': 'Upload backend unavailable. Configure Cloudinary (preferred) or Firebase Storage on hosted environment.'
            }), 503

        print(f"📦 [UPLOAD_INVENTORY] Stored via {backend}: {url}")

        return jsonify({'success': True, 'url': url})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/submit-application', methods=['POST'])
@firebase_auth_required
def submit_application():
    """Handle application submission with file uploads"""
    try:
        from werkzeug.utils import secure_filename
        
        # Get form data
        user_id = request.form.get('userId')
        user_email = request.form.get('userEmail')
        category = request.form.get('category')
        investment_qty = request.form.get('investmentQty')
        harvest_qty = request.form.get('harvestQty')
        farmer_id_number = request.form.get('farmerIdNumber')
        google_pin_location = request.form.get('googlePinLocation')
        
        # Validate required fields
        if not all([user_id, user_email, category, investment_qty, harvest_qty, farmer_id_number, google_pin_location]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400

        local_fallback_enabled = (
            str(os.environ.get('ALLOW_LOCAL_UPLOAD_FALLBACK', '')).strip().lower() in ('1', 'true', 'yes')
            or request.host.startswith('127.0.0.1')
            or request.host.startswith('localhost')
        )
        
        # Process file uploads
        file_fields = ['titleFile', 'taxFile', 'blueprintFile', 'landFile', 'cropFile', 'planFile', 'brgyFile', 'productPictureFile', 'validIdFile']
        multi_file_fields = {'blueprintFile', 'landFile', 'cropFile'}
        file_paths = {}
        
        for field in file_fields:
            if field in request.files:
                files = request.files.getlist(field)
                saved_urls = []

                for idx, file in enumerate(files):
                    if not file or not file.filename:
                        continue

                    # Secure filename
                    filename = secure_filename(file.filename)
                    timestamp = int(datetime.now().timestamp())
                    unique_filename = f"{timestamp}_{field}_{idx}_{filename}"

                    web_path = None
                    backend = 'none'
                    # 1) Cloudinary
                    if _cloudinary_enabled():
                        web_path = _upload_to_cloudinary(file, f"tlph/applications/{user_id}")
                        if web_path:
                            backend = 'cloudinary'

                    # 2) Firebase Storage (host-safe fallback)
                    if not web_path:
                        web_path = _upload_to_firebase_storage(file, f"tlph/applications/{user_id}")
                        if web_path:
                            backend = 'firebase_storage'

                    # 3) Local static (development fallback)
                    if not web_path and local_fallback_enabled:
                        upload_dir = os.path.join('static', 'uploads', 'applications', user_id)
                        os.makedirs(upload_dir, exist_ok=True)
                        file_path = os.path.join(upload_dir, unique_filename)
                        file.save(file_path)
                        web_path = f"/static/uploads/applications/{user_id}/{unique_filename}"
                        backend = 'local_static'

                    if not web_path:
                        return jsonify({
                            'success': False,
                            'message': f'Failed to upload {field}. Configure Cloudinary/Firebase storage in hosted environment.'
                        }), 503

                    print(f"📦 [SUBMIT_APPLICATION] {field} -> {backend}: {web_path}")

                    saved_urls.append(web_path)

                if not saved_urls:
                    continue

                normalized_key = field.replace('File', '')
                if field in multi_file_fields:
                    file_paths[normalized_key] = saved_urls
                    # Keep single-value compatibility for older viewers
                    file_paths[f"{normalized_key}Primary"] = saved_urls[0]
                else:
                    file_paths[normalized_key] = saved_urls[0]
        
        return jsonify({
            'success': True,
            'message': 'Files uploaded successfully',
            'filePaths': file_paths
        })
        
    except Exception as e:
        print(f'Error submitting application: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Failed to submit application: {str(e)}'
        }), 500


@bp.route('/upload-service-files', methods=['POST'])
def upload_service_files():
    """Upload service request files and return web URLs grouped by field id/name."""
    try:
        from werkzeug.utils import secure_filename

        user_id = (request.form.get('userId') or '').strip()
        if not user_id:
            return jsonify({'success': False, 'message': 'Missing userId'}), 400

        local_fallback_enabled = (
            str(os.environ.get('ALLOW_LOCAL_UPLOAD_FALLBACK', '')).strip().lower() in ('1', 'true', 'yes')
            or request.host.startswith('127.0.0.1')
            or request.host.startswith('localhost')
        )

        file_paths = {}
        upload_backends = {}
        timestamp = int(datetime.now().timestamp())

        for field in request.files:
            files = request.files.getlist(field)
            saved_urls = []

            for idx, file in enumerate(files):
                if not file or not file.filename:
                    continue

                filename = secure_filename(file.filename)
                unique_filename = f"{timestamp}_{field}_{idx}_{filename}"
                web_path = None
                backend = 'none'

                # 1) Cloudinary
                if _cloudinary_enabled():
                    web_path = _upload_to_cloudinary(file, f"tlph/service_requests/{user_id}")
                    if web_path:
                        backend = 'cloudinary'

                # 2) Firebase Storage (host-safe fallback)
                if not web_path:
                    web_path = _upload_to_firebase_storage(file, f"tlph/service_requests/{user_id}")
                    if web_path:
                        backend = 'firebase_storage'

                # 3) Local static (development fallback)
                if not web_path and local_fallback_enabled:
                    upload_dir = os.path.join('static', 'uploads', 'service_requests', user_id)
                    os.makedirs(upload_dir, exist_ok=True)
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    web_path = f"/static/uploads/service_requests/{user_id}/{unique_filename}"
                    backend = 'local_static'

                if not web_path:
                    return jsonify({
                        'success': False,
                        'message': f'Failed to upload file for field "{field}". Configure Cloudinary/Firebase storage in hosted environment.'
                    }), 503

                upload_backends[field] = backend
                print(f"📦 [UPLOAD_SERVICE_FILES] {field} -> {backend}: {web_path}")

                saved_urls.append(web_path)

            if saved_urls:
                file_paths[field] = saved_urls

        return jsonify({
            'success': True,
            'message': 'Service files uploaded successfully',
            'filePaths': file_paths,
            'uploadBackends': upload_backends
        })

    except Exception as e:
        print(f'Error uploading service files: {str(e)}')
        return jsonify({
            'success': False,
            'message': f'Failed to upload service files: {str(e)}'
        }), 500


@bp.route('/upload-backend-health', methods=['GET'])
def upload_backend_health():
    """Quick diagnostic endpoint for hosted upload backends (no secret values exposed)."""
    try:
        cloud_name = bool((os.environ.get('CLOUDINARY_CLOUD_NAME') or '').strip())
        api_key = bool((os.environ.get('CLOUDINARY_API_KEY') or '').strip())
        api_secret = bool((os.environ.get('CLOUDINARY_API_SECRET') or '').strip())

        firebase_bucket_ok = False
        firebase_bucket_name = ''
        firebase_bucket_error = ''
        try:
            from firebase_config import get_storage_bucket
            bucket = get_storage_bucket()
            firebase_bucket_ok = bool(bucket)
            firebase_bucket_name = getattr(bucket, 'name', '') if bucket else ''
        except Exception as fb_err:
            firebase_bucket_error = str(fb_err)

        return jsonify({
            'success': True,
            'cloudinary': {
                'configured': cloud_name and api_key and api_secret,
                'cloud_name_set': cloud_name,
                'api_key_set': api_key,
                'api_secret_set': api_secret,
            },
            'firebase_storage': {
                'configured': firebase_bucket_ok,
                'bucket_name': firebase_bucket_name,
                'error': firebase_bucket_error,
            },
            'local_fallback_enabled': str(os.environ.get('ALLOW_LOCAL_UPLOAD_FALLBACK', '')).strip().lower() in ('1', 'true', 'yes')
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/get-applications/<user_id>', methods=['GET'])
@firebase_auth_required
def get_user_applications(user_id):
    """Get all applications for a specific user"""
    try:
        # This is a placeholder - actual data is fetched from Firestore on frontend
        return jsonify({
            'success': True,
            'message': 'Fetch applications from Firestore on the frontend'
        })
    except Exception as e:
        print(f'Error fetching applications: {str(e)}')
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== SUPERADMIN APPLICATION REGISTRY ====================

def _sa_norm_text(value, fallback='N/A'):
    text = str(value or '').strip()
    return text if text else fallback


def _sa_to_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception:
            return None
    if hasattr(value, 'to_datetime'):
        try:
            return value.to_datetime()
        except Exception:
            return None
    if hasattr(value, 'strftime'):
        return value
    return None


def _sa_region_from_province(province_name):
    prov = str(province_name or '').strip().lower()
    if not prov:
        return ''
    try:
        from models.region_province_map import region_province_map
        for region, provinces in (region_province_map or {}).items():
            for p in (provinces or []):
                if str(p or '').strip().lower() == prov:
                    return region
    except Exception:
        return ''
    return ''


def _sa_category_from_app_type(application_type):
    app_type = str(application_type or '').strip().lower()
    if any(k in app_type for k in ['farm', 'crop', 'soil', 'pest', 'fertilizer', 'chemical']):
        return 'Farming'
    if any(k in app_type for k in ['fish', 'fisher', 'marine', 'aqua']):
        return 'Fisheries'
    if any(k in app_type for k in ['livestock', 'animal', 'poultry']):
        return 'Livestock'
    if any(k in app_type for k in ['forest', 'timber', 'tree']):
        return 'Forestry'
    if any(k in app_type for k in ['wildlife', 'fauna', 'protected']):
        return 'Wildlife'
    if any(k in app_type for k in ['environment', 'compliance', 'impact', 'waste']):
        return 'Environment'
    return 'General'


def _sa_sector_label(value):
    raw = str(value or '').strip()
    key = raw.lower()
    mapping = {
        'farming': 'Crop & Plant',
        'livestock': 'Fisheries & Agriculture',
        'agribusiness': 'Agribusiness & Agro-Processing',
        'trade': 'Agricultural Trade',
        'infrastructure': 'Infrastructure',
    }
    return mapping.get(key, raw if raw else 'General')


def _sa_status_payload(data):
    status = str(data.get('status') or 'pending').strip().lower()
    regional_status = str(data.get('regionalStatus') or '').strip().lower()
    national_status = str(data.get('nationalStatus') or '').strip().lower()

    approved_by_level = str(data.get('approvedByLevel') or '').strip()
    rejected_by_level = str(data.get('rejectedByLevel') or '').strip()
    forwarded_to_level = str(data.get('forwardedToLevel') or '').strip()
    forwarded_by_level = str(data.get('forwardedByLevel') or '').strip()

    def _norm_level(v):
        lv = str(v or '').strip().lower()
        if lv == 'national':
            return 'National'
        if lv == 'regional':
            return 'Regional'
        if lv == 'municipal':
            return 'Municipal'
        return str(v or '').strip()

    def _infer_forward_target():
        raw = _norm_level(forwarded_to_level)
        if raw:
            return raw
        if 'national' in status or national_status:
            return 'National'
        if 'regional' in status or regional_status or status in {'to review', 'to-review', 'review'}:
            return 'Regional'
        return 'Regional'

    resolved_forwarded_to = _infer_forward_target()

    if national_status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if national_status in {'cancelled', 'canceled'} else national_status
    elif status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if status in {'cancelled', 'canceled'} else status
    elif status in {'to review', 'to-review', 'review'} or regional_status in {'to review', 'to-review', 'review'}:
        effective_status = 'to review'
    elif status.startswith('forwarded') or forwarded_to_level:
        effective_status = 'forwarded'
    else:
        effective_status = 'pending'

    def _resolve_approved_level():
        # Source of truth: explicit workflow actor level saved in document.
        if _norm_level(approved_by_level):
            return _norm_level(approved_by_level)
        if national_status == 'approved':
            return 'National'
        if regional_status == 'approved':
            return 'Regional'
        if resolved_forwarded_to == 'National':
            return 'National'
        if resolved_forwarded_to == 'Regional':
            return 'Regional'
        return 'Municipal'

    def _resolve_rejected_level():
        # Source of truth: explicit workflow actor level saved in document.
        if _norm_level(rejected_by_level):
            return _norm_level(rejected_by_level)
        if national_status == 'rejected':
            return 'National'
        if regional_status == 'rejected':
            return 'Regional'
        if resolved_forwarded_to == 'National':
            return 'National'
        if resolved_forwarded_to == 'Regional':
            return 'Regional'
        return 'Municipal'

    if effective_status == 'approved':
        origin = _resolve_approved_level()
        status_display = f'Approved by {origin}'
    elif effective_status == 'rejected':
        origin = _resolve_rejected_level()
        status_display = f'Rejected by {origin}'
    elif effective_status == 'cancelled':
        origin = rejected_by_level or approved_by_level or 'Applicant/System'
        status_display = f'Cancelled ({origin})'
    elif effective_status == 'forwarded':
        target = resolved_forwarded_to
        origin = _norm_level(forwarded_by_level) or ('Regional' if target == 'National' else 'Municipal')
        status_display = f'Forwarded by {origin} to {target}'
    elif effective_status == 'to review':
        status_display = 'For Review'
    else:
        status_display = 'Pending'

    return {
        'status': effective_status,
        'status_display': status_display,
        'status_origin': {
            'approvedByLevel': approved_by_level,
            'rejectedByLevel': rejected_by_level,
            'forwardedByLevel': forwarded_by_level,
            'forwardedToLevel': forwarded_to_level,
            'resolvedApprovedByLevel': _resolve_approved_level(),
            'resolvedRejectedByLevel': _resolve_rejected_level(),
            'resolvedForwardedByLevel': _norm_level(forwarded_by_level) or ('Regional' if resolved_forwarded_to == 'National' else 'Municipal'),
            'resolvedForwardedToLevel': resolved_forwarded_to,
            'regionalStatus': regional_status,
            'nationalStatus': national_status,
            'rawStatus': status
        }
    }


def _sa_extract_application(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('dateFiled') or data.get('date_filed') or data.get('submittedAt'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    application_type = _sa_norm_text(data.get('applicationType') or form_data.get('applicationType'), 'General')
    raw_sector = (
        data.get('categoryType')
        or data.get('category')
        or data.get('applicantCategory')
        or data.get('sector')
        or form_data.get('categoryType')
        or form_data.get('category')
        or form_data.get('sector')
        or 'General'
    )
    sector = _sa_sector_label(raw_sector)

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    product_name = (
        data.get('productName')
        or data.get('resourceName')
        or data.get('item_name')
        or data.get('itemName')
        or form_data.get('productName')
        or form_data.get('resourceName')
        or form_data.get('itemName')
        or form_data.get('cropName')
        or data.get('cropName')
        or 'N/A'
    )

    status_payload = _sa_status_payload(data)

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'product_name': _sa_norm_text(product_name),
        'sector': sector,
        'application_type': application_type,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status_payload['status'],
        'status_display': status_payload['status_display'],
        'status_origin': status_payload['status_origin'],
        'applicant_photo': _sa_norm_text(
            user_data.get('photoURL')
            or user_data.get('profilePicture')
            or user_data.get('profilePic')
            or user_data.get('avatarUrl')
            or data.get('photoURL')
            or data.get('profilePicture'),
            ''
        ),
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(
            user_data.get('contactNumber')
            or user_data.get('phone')
            or user_data.get('phoneNumber')
            or user_data.get('mobile')
            or user_data.get('mobileNumber')
            or data.get('contact')
            or data.get('contactNumber')
            or form_data.get('contact')
            or form_data.get('contactNumber')
        ),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data
    }

@bp.route('/superadmin/applications', methods=['GET'])
def superadmin_get_applications():
    """Return all applications for superadmin master registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]
        apps.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': apps, 'total': len(apps)})

    except Exception as e:
        print(f'[ERROR] superadmin_get_applications: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/stats', methods=['GET'])
def superadmin_application_stats():
    """Return KPI stats for superadmin application registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]

        total = 0
        pending = 0
        approved = 0
        rejected = 0
        to_review = 0
        cancelled = 0

        for app in apps:
            total += 1
            effective = app.get('status', 'pending')

            if effective in ['approved']:
                approved += 1
            elif effective in ['rejected']:
                rejected += 1
            elif effective in ['cancelled']:
                cancelled += 1
            elif effective in ['to review', 'review']:
                to_review += 1
            else:
                pending += 1

        approval_rate = round((approved / total * 100), 1) if total > 0 else 0

        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'pending': pending,
                'approved': approved,
                'rejected': rejected,
                'to_review': to_review,
                'cancelled': cancelled,
                'approval_rate': approval_rate,
            }
        })

    except Exception as e:
        print(f'[ERROR] superadmin_application_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/charts', methods=['GET'])
def superadmin_application_charts():
    """Return chart data for superadmin application registry"""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import calendar
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('applications').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        apps = [_sa_extract_application(doc, users_map) for doc in docs]

        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        category_count = defaultdict(int)
        weekly_trend = defaultdict(int)

        for app in apps:
            created_at = _sa_to_datetime(app.get('date_iso'))
            if created_at:
                monthly_trend[created_at.strftime('%Y-%m')] += 1
                iso = created_at.isocalendar()
                weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1

            region = str(app.get('region') or '').strip()
            if region and region.upper() != 'N/A':
                region_count[region] += 1

            category = str(app.get('sector') or 'General').strip()
            category_count[category] += 1

        # Last 8 weeks (week-by-week) trend
        now = datetime.now()
        week_labels = []
        week_data = []

        for i in range(7, -1, -1):
            target = now - dt_module.timedelta(weeks=i)
            iso = target.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            week_labels.append(f"W{iso[1]}")
            week_data.append(weekly_trend.get(key, 0))

        # Monthly fallback labels too
        last_6_months = []
        monthly_data = []
        for i in range(5, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            key = f"{target_year}-{target_month:02d}"
            last_6_months.append(calendar.month_abbr[target_month])
            monthly_data.append(monthly_trend.get(key, 0))

        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:7]
        top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'trend': {'labels': week_labels, 'data': week_data},
            'monthly': {'labels': last_6_months, 'data': monthly_data},
            'regions': {
                'labels': [r[0] for r in top_regions],
                'data': [r[1] for r in top_regions],
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })

    except Exception as e:
        print(f'[ERROR] superadmin_application_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/applications/audit-trail', methods=['GET'])
def superadmin_application_audit():
    """Return recent audit trail entries for application registry"""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = db.collection('applications') \
                 .order_by('createdAt', direction='DESCENDING') \
                 .limit(10) \
                 .stream()

        docs = list(docs)
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        entries = []
        for doc in docs:
            app = _sa_extract_application(doc, users_map)
            created_at = _sa_to_datetime(app.get('date_iso'))
            time_str = created_at.strftime('%H:%M') if created_at else '--:--'

            entries.append({
                'time': time_str,
                'ref': app.get('ref', doc.id[:8].upper()),
                'name': app.get('name', 'N/A'),
                'status': app.get('status', 'pending'),
                'status_display': app.get('status_display', 'Pending')
            })

        return jsonify(entries)

    except Exception as e:
        print(f'[ERROR] superadmin_application_audit: {e}')
        # Fallback: get latest without ordering
        try:
            from firebase_config import get_firestore_db
            db = get_firestore_db()
            docs = db.collection('applications').limit(10).stream()
            entries = []
            for doc in docs:
                data = doc.to_dict() or {}
                status = (data.get('status') or 'pending').lower()
                name = (data.get('applicantName') or data.get('fullName') or doc.id[:8].upper())
                entries.append({'time': '--:--', 'ref': doc.id[:8].upper(), 'name': name, 'status': status})
            return jsonify(entries)
        except Exception as e2:
            return jsonify({'success': False, 'message': str(e2)}), 500


@bp.route('/superadmin/applications/<application_id>', methods=['GET'])
def superadmin_get_application_detail(application_id):
    """Return complete and normalized details for one application (superadmin view modal)."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        app_doc = db.collection('applications').document(application_id).get()
        if not app_doc.exists:
            return jsonify({'success': False, 'message': 'Application not found'}), 404

        data = app_doc.to_dict() or {}
        user_id = data.get('userId')
        users_map = {}
        if user_id:
            try:
                u_doc = db.collection('users').document(user_id).get()
                if u_doc.exists:
                    users_map[user_id] = u_doc.to_dict() or {}
            except Exception:
                pass

        app = _sa_extract_application(app_doc, users_map)
        return jsonify({'success': True, 'data': app})
    except Exception as e:
        print(f'[ERROR] superadmin_get_application_detail: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SUPERADMIN SERVICE REQUEST REGISTRY ====================

def _sa_sr_status_payload(data):
    status = str(data.get('status') or 'pending').strip().lower()
    regional_status = str(data.get('regionalStatus') or '').strip().lower()
    national_status = str(data.get('nationalStatus') or '').strip().lower()

    approved_by_level = str(data.get('approvedByLevel') or '').strip()
    rejected_by_level = str(data.get('rejectedByLevel') or '').strip()
    forwarded_by_level = str(data.get('forwardedByLevel') or data.get('forwardedToNationalByLevel') or '').strip()
    forwarded_to_level = str(data.get('forwardedToLevel') or '').strip()

    def _norm_level(v):
        lv = str(v or '').strip().lower()
        if lv == 'national':
            return 'National'
        if lv == 'regional':
            return 'Regional'
        if lv == 'municipal':
            return 'Municipal'
        return str(v or '').strip()

    def _infer_forward_target():
        raw = _norm_level(forwarded_to_level)
        if raw:
            return raw
        if 'national' in status or national_status:
            return 'National'
        if 'regional' in status or regional_status or status in {'to review', 'to-review', 'review'}:
            return 'Regional'
        return 'Regional'

    resolved_forward_target = _infer_forward_target()

    if national_status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if national_status in {'cancelled', 'canceled'} else national_status
    elif status in {'approved', 'rejected', 'cancelled', 'canceled'}:
        effective_status = 'cancelled' if status in {'cancelled', 'canceled'} else status
    elif status in {'to review', 'to-review', 'review'} or regional_status in {'to review', 'to-review', 'review'}:
        effective_status = 'to review'
    elif status.startswith('forwarded') or forwarded_to_level:
        effective_status = 'forwarded'
    else:
        effective_status = 'pending'

    def _resolve_approved_level():
        if _norm_level(approved_by_level):
            return _norm_level(approved_by_level)
        if national_status == 'approved':
            return 'National'
        if regional_status == 'approved':
            return 'Regional'
        if resolved_forward_target == 'National':
            return 'National'
        if resolved_forward_target == 'Regional':
            return 'Regional'
        return 'Municipal'

    def _resolve_rejected_level():
        if _norm_level(rejected_by_level):
            return _norm_level(rejected_by_level)
        if national_status == 'rejected':
            return 'National'
        if regional_status == 'rejected':
            return 'Regional'
        if resolved_forward_target == 'National':
            return 'National'
        if resolved_forward_target == 'Regional':
            return 'Regional'
        return 'Municipal'

    resolved_forwarded_by = _norm_level(forwarded_by_level) or ('Regional' if resolved_forward_target == 'National' else 'Municipal')

    pending_target = resolved_forward_target or ('National' if national_status else 'Regional')

    if effective_status == 'approved':
        status_display = f"Approved by {_resolve_approved_level()}"
    elif effective_status == 'rejected':
        status_display = f"Rejected by {_resolve_rejected_level()}"
    elif effective_status == 'cancelled':
        status_display = f"Cancelled ({rejected_by_level or approved_by_level or 'Applicant/System'})"
    elif effective_status == 'forwarded':
        status_display = f"Forwarded by {resolved_forwarded_by} to {resolved_forward_target}"
    elif effective_status == 'to review':
        status_display = f"For Review at {pending_target}"
    else:
        status_display = f"Pending at {pending_target}"

    return {
        'status': effective_status,
        'status_display': status_display,
        'status_origin': {
            'approvedByLevel': approved_by_level,
            'rejectedByLevel': rejected_by_level,
            'forwardedByLevel': forwarded_by_level,
            'forwardedToLevel': forwarded_to_level,
            'resolvedApprovedByLevel': _resolve_approved_level(),
            'resolvedRejectedByLevel': _resolve_rejected_level(),
            'resolvedForwardedByLevel': resolved_forwarded_by,
            'resolvedForwardedToLevel': resolved_forward_target,
            'regionalStatus': regional_status,
            'nationalStatus': national_status,
            'rawStatus': status,
        }
    }


def _sa_extract_service_request(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    applicant_photo = (
        data.get('photoURL')
        or data.get('photoUrl')
        or data.get('profilePhoto')
        or data.get('profile_photo')
        or data.get('photo')
        or form_data.get('photoURL')
        or form_data.get('photoUrl')
        or user_data.get('photoURL')
        or user_data.get('photoUrl')
        or user_data.get('profilePhoto')
        or user_data.get('profile_photo')
        or user_data.get('photo')
        or ''
    )

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('submittedAt') or data.get('dateFiled') or data.get('date_filed'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    category = _sa_norm_text(
        data.get('categoryType')
        or data.get('category')
        or data.get('serviceType')
        or data.get('serviceCategory')
        or data.get('requestType')
        or form_data.get('categoryType')
        or form_data.get('category')
        or form_data.get('serviceType')
        or form_data.get('serviceCategory')
        or form_data.get('requestType'),
        'General'
    )

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or data.get('userName')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    status_payload = _sa_sr_status_payload(data)

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'category': category,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status_payload['status'],
        'status_display': status_payload['status_display'],
        'status_actor_level': (
            status_payload['status_origin'].get('resolvedApprovedByLevel')
            if status_payload['status'] == 'approved'
            else status_payload['status_origin'].get('resolvedRejectedByLevel')
            if status_payload['status'] == 'rejected'
            else status_payload['status_origin'].get('resolvedForwardedByLevel')
            if status_payload['status'] == 'forwarded'
            else None
        ),
        'status_target_level': (
            status_payload['status_origin'].get('resolvedForwardedToLevel')
            if status_payload['status'] in {'pending', 'to review', 'forwarded'}
            else None
        ),
        'status_origin': status_payload['status_origin'],
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(data.get('contact') or data.get('contactNumber') or user_data.get('contactNumber')),
        'applicant_photo': _sa_norm_text(applicant_photo, ''),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data,
    }


@bp.route('/superadmin/service-requests', methods=['GET'])
def superadmin_get_service_requests():
    """Return all service requests for superadmin registry across all municipalities/regions."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]
        rows.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': rows, 'requests': rows, 'total': len(rows)})
    except Exception as e:
        print(f'[ERROR] superadmin_get_service_requests: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/stats', methods=['GET'])
def superadmin_service_request_stats():
    """Return KPI counts for superadmin service request registry."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]

        stats = {
            'total': len(rows),
            'pending': 0,
            'for_review': 0,
            'approved': 0,
            'rejected': 0,
            'cancelled': 0,
        }

        for row in rows:
            st = str(row.get('status') or 'pending').lower()
            if st == 'approved':
                stats['approved'] += 1
            elif st == 'rejected':
                stats['rejected'] += 1
            elif st == 'cancelled':
                stats['cancelled'] += 1
            elif st in {'to review', 'review', 'forwarded'}:
                stats['for_review'] += 1
            else:
                stats['pending'] += 1

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/charts', methods=['GET'])
def superadmin_service_request_charts():
    """Return trend + category chart data for superadmin service request registry."""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(5000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]

        weekly_trend = defaultdict(int)
        category_count = defaultdict(int)

        for row in rows:
            dt = _sa_to_datetime(row.get('date_iso'))
            if dt:
                iso = dt.isocalendar()
                weekly_trend[f"{iso[0]}-W{iso[1]:02d}"] += 1
            category_count[str(row.get('category') or 'General')] += 1

        now = datetime.now()
        week_labels = []
        week_data = []
        for i in range(7, -1, -1):
            target = now - dt_module.timedelta(weeks=i)
            iso = target.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            week_labels.append(f"W{iso[1]}")
            week_data.append(weekly_trend.get(key, 0))

        top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'trend': {
                'labels': week_labels,
                'data': week_data,
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/service-requests/audit-trail', methods=['GET'])
def superadmin_service_request_audit():
    """Return latest service request actions for live audit panel."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('service_requests').limit(20).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_service_request(doc, users_map) for doc in docs]
        rows.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        entries = []
        for row in rows[:10]:
            dt = _sa_to_datetime(row.get('date_iso'))
            entries.append({
                'time': dt.strftime('%H:%M') if dt else '--:--',
                'ref': row.get('ref', 'N/A'),
                'name': row.get('name', 'N/A'),
                'status': row.get('status', 'pending'),
                'status_display': row.get('status_display', 'Pending')
            })

        return jsonify({'success': True, 'entries': entries})
    except Exception as e:
        print(f'[ERROR] superadmin_service_request_audit: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SUPERADMIN LICENSE & PERMIT REGISTRY ====================

def _sa_extract_permit_application(doc, users_map):
    data = doc.to_dict() or {}
    form_data = data.get('formData') or {}
    user_data = users_map.get(data.get('userId', ''), {})

    created_dt = _sa_to_datetime(data.get('createdAt') or data.get('dateFiled') or data.get('date_filed') or data.get('submittedAt'))
    date_filed = created_dt.strftime('%Y-%m-%d') if created_dt else _sa_norm_text(data.get('dateFiled') or data.get('date_filed'), '')

    province = data.get('province') or form_data.get('province') or user_data.get('province') or user_data.get('Province') or ''
    region = (
        data.get('region')
        or data.get('regionName')
        or form_data.get('region')
        or user_data.get('region')
        or user_data.get('regionName')
        or _sa_region_from_province(province)
        or 'N/A'
    )

    municipality = (
        data.get('municipality')
        or form_data.get('municipality')
        or form_data.get('cityMunicipality')
        or data.get('location')
        or user_data.get('municipality')
        or 'N/A'
    )

    application_type = _sa_norm_text(data.get('applicationType') or form_data.get('applicationType'), 'General')
    category = _sa_norm_text(
        data.get('categoryType')
        or data.get('category')
        or form_data.get('categoryType')
        or form_data.get('category')
        or application_type,
        'General'
    )

    name = (
        data.get('applicantName')
        or data.get('fullName')
        or data.get('name')
        or f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
        or user_data.get('displayName')
        or 'N/A'
    )

    status_payload = _sa_status_payload(data)
    status = status_payload['status']
    status_origin = status_payload['status_origin']

    status_actor_level = (
        status_origin.get('resolvedApprovedByLevel') if status == 'approved'
        else status_origin.get('resolvedRejectedByLevel') if status == 'rejected'
        else status_origin.get('resolvedForwardedByLevel') if status == 'forwarded'
        else None
    )
    status_target_level = status_origin.get('resolvedForwardedToLevel') if status in {'pending', 'to review', 'forwarded'} else None

    return {
        'id': doc.id,
        'ref': doc.id[:12].upper(),
        'date': date_filed,
        'date_iso': date_filed,
        'name': _sa_norm_text(name),
        'category': category,
        'application_type': application_type,
        'region': _sa_norm_text(region),
        'municipality': _sa_norm_text(municipality),
        'province': _sa_norm_text(province),
        'status': status,
        'status_display': status_payload['status_display'],
        'status_actor_level': status_actor_level,
        'status_target_level': status_target_level,
        'status_origin': status_origin,
        'email': _sa_norm_text(data.get('email') or data.get('userEmail') or user_data.get('email')),
        'contact': _sa_norm_text(data.get('contact') or data.get('contactNumber') or user_data.get('contactNumber')),
        'description': _sa_norm_text(data.get('description') or data.get('notes') or form_data.get('description') or form_data.get('purpose')),
        'form_data': form_data,
        'raw': data,
    }


@bp.route('/superadmin/permits', methods=['GET'])
def superadmin_get_permits():
    """Return all license/permit applications across municipalities and regions for superadmin."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())

        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        permits = [_sa_extract_permit_application(doc, users_map) for doc in docs]
        permits.sort(key=lambda x: x.get('date_iso') or '', reverse=True)

        return jsonify({'success': True, 'data': permits, 'permits': permits, 'total': len(permits)})
    except Exception as e:
        print(f'[ERROR] superadmin_get_permits: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/permits/stats', methods=['GET'])
def superadmin_permits_stats():
    """Return KPI stats for superadmin permits/license registry."""
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_permit_application(doc, users_map) for doc in docs]
        stats = {
            'total': len(rows),
            'approved': 0,
            'rejected': 0,
            'pending': 0,
            'for_review': 0,
            'forwarded': 0,
            'cancelled': 0,
        }

        for row in rows:
            st = str(row.get('status') or 'pending').lower()
            if st == 'approved':
                stats['approved'] += 1
            elif st == 'rejected':
                stats['rejected'] += 1
            elif st == 'cancelled':
                stats['cancelled'] += 1
            elif st == 'forwarded':
                stats['forwarded'] += 1
            elif st in {'to review', 'review'}:
                stats['for_review'] += 1
            else:
                stats['pending'] += 1

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f'[ERROR] superadmin_permits_stats: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/superadmin/permits/charts', methods=['GET'])
def superadmin_permits_charts():
    """Return chart data for superadmin permits/license dashboard."""
    try:
        from firebase_config import get_firestore_db
        from collections import defaultdict
        import datetime as dt_module
        db = get_firestore_db()

        docs = list(db.collection('license_applications').limit(7000).stream())
        user_ids = {d.to_dict().get('userId') for d in docs if (d.to_dict() or {}).get('userId')}
        users_map = {}
        for uid in user_ids:
            try:
                u_doc = db.collection('users').document(uid).get()
                if u_doc.exists:
                    users_map[uid] = u_doc.to_dict() or {}
            except Exception:
                continue

        rows = [_sa_extract_permit_application(doc, users_map) for doc in docs]

        month_counts = defaultdict(int)
        category_counts = defaultdict(int)

        for row in rows:
            dt = _sa_to_datetime(row.get('date_iso'))
            if dt:
                month_counts[dt.strftime('%Y-%m')] += 1
            category_counts[str(row.get('category') or 'General')] += 1

        now = datetime.now()
        month_labels = []
        month_data = []
        for i in range(5, -1, -1):
            target = now - dt_module.timedelta(days=30 * i)
            key = target.strftime('%Y-%m')
            month_labels.append(target.strftime('%b'))
            month_data.append(month_counts.get(key, 0))

        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:6]

        return jsonify({
            'success': True,
            'issuance': {
                'labels': month_labels,
                'data': month_data,
            },
            'categories': {
                'labels': [c[0] for c in top_categories],
                'data': [c[1] for c in top_categories],
            }
        })
    except Exception as e:
        print(f'[ERROR] superadmin_permits_charts: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== PROJECT MANAGEMENT ====================

@bp.route('/projects/create', methods=['POST'])
def create_project():
    """
    Create a new project based on admin role
    National: Direct creation (auto-approved, visible to all)
    Regional: Pending national approval (visible to region)
    Municipal: Pending regional review (visible to municipality and regional)
    """
    try:
        import projects_storage
        from firebase_admin import auth as firebase_auth
        
        data = request.get_json() or {}
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if not user_role or not user_email:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        # Validate required fields
        name = (data.get('name') or '').strip()
        description = (data.get('description') or '').strip()
        region = (data.get('region') or '').strip()
        municipality = (data.get('municipality') or '').strip()
        barangay = (data.get('barangay') or '').strip()
        start_date = (data.get('start_date') or '').strip()
        
        if not all([name, region, municipality, start_date]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        # Create based on role
        if user_role == 'national':
            result = projects_storage.create_project_national(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        elif user_role == 'regional':
            result = projects_storage.create_project_regional(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        elif user_role in ['municipal', 'municipal_admin']:
            result = projects_storage.create_project_municipal(
                name=name,
                description=description,
                region=region,
                municipality=municipality,
                barangay=barangay,
                start_date=start_date,
                created_by_email=user_email
            )
        else:
            return jsonify({'success': False, 'error': 'Unauthorized role'}), 403
        
        if result['success']:
            # Add to system logs
            system_logs_storage.add_system_log(
                municipality=municipality,
                user=user_email,
                action='PROJECT_CREATED',
                target='Projects',
                target_id=result.get('project_id', 'n/a'),
                module='PROJECTS',
                outcome='SUCCESS',
                message=f'Project "{name}" created by {user_role}',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f'[PROJECT_ERROR] create_project failed: {e}')
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/approve/<project_id>', methods=['POST'])
def approve_project(project_id):
    """
    Approve a project (national admin only)
    Moves pending_national_approval → active
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'national':
            return jsonify({'success': False, 'error': 'Only National Admin can approve'}), 403
        
        data = request.get_json() or {}
        notes = (data.get('notes') or '').strip()
        
        result = projects_storage.approve_project_national(
            project_id=project_id,
            reviewer_email=user_email,
            notes=notes
        )
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='National',
                user=user_email,
                action='PROJECT_APPROVED',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message='Project approved by National Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] approve_project failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/reject/<project_id>', methods=['POST'])
def reject_project(project_id):
    """
    Reject a project (national admin only)
    Moves to rejected status
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'national':
            return jsonify({'success': False, 'error': 'Only National Admin can reject'}), 403
        
        data = request.get_json() or {}
        notes = (data.get('notes') or '').strip()
        
        result = projects_storage.reject_project_national(
            project_id=project_id,
            reviewer_email=user_email,
            notes=notes
        )
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='National',
                user=user_email,
                action='PROJECT_REJECTED',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message='Project rejected by National Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] reject_project failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/review-regional/<project_id>', methods=['POST'])
def review_project_regional(project_id):
    """
    Regional admin reviews/approves a municipal project
    Moves pending_regional_approval → pending_national_approval
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_email = session.get('user_email', '')
        
        if user_role != 'regional':
            return jsonify({'success': False, 'error': 'Only Regional Admin can review regionally'}), 403
        
        data = request.get_json() or {}
        action = (data.get('action') or '').strip().lower()
        notes = (data.get('notes') or '').strip()
        
        if action == 'approve':
            result = projects_storage.approve_project_regional(
                project_id=project_id,
                reviewer_email=user_email,
                notes=notes
            )
        elif action == 'reject':
            result = projects_storage.reject_project_regional(
                project_id=project_id,
                reviewer_email=user_email,
                notes=notes
            )
        else:
            return jsonify({'success': False, 'error': 'Invalid action. Use approve or reject'}), 400
        
        if result['success']:
            system_logs_storage.add_system_log(
                municipality='Regional',
                user=user_email,
                action=f'PROJECT_{action.upper()}_REGIONAL',
                target='Projects',
                target_id=project_id,
                module='PROJECTS',
                outcome='SUCCESS',
                message=f'Project {action} by Regional Admin',
                device_type=detect_device_from_request(),
                user_agent=request.headers.get('User-Agent', '')
            )
        
        return jsonify(result)
        
    except Exception as e:
        print(f'[PROJECT_ERROR] review_project_regional failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/list', methods=['GET'])
def list_projects():
    """
    Get projects based on user role
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_region = session.get('user_region', '')
        user_municipality = session.get('user_municipality', '')
        
        if not user_role:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if user_role == 'national':
            projects = projects_storage.get_projects_national()
        elif user_role == 'regional':
            projects = projects_storage.get_projects_regional(user_region)
        elif user_role in ['municipal', 'municipal_admin']:
            projects = projects_storage.get_projects_municipal(user_municipality, user_region)
        else:
            projects = []
        
        return jsonify({'success': True, 'projects': projects})
        
    except Exception as e:
        print(f'[PROJECT_ERROR] list_projects failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/projects/pending-approval', methods=['GET'])
def get_projects_pending_approval():
    """
    Get projects pending approval for current user's role
    """
    try:
        import projects_storage
        
        user_role = session.get('user_role', '').lower()
        user_region = session.get('user_region', '')
        
        if not user_role:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        if user_role == 'regional':
            projects = projects_storage.get_projects_for_approval('regional', user_region)
        elif user_role == 'national':
            projects = projects_storage.get_projects_for_approval('national')
        else:
            projects = []
        
        return jsonify({'success': True, 'pending_projects': projects})
        
    except Exception as e:
        print(f'[PROJECT_ERROR] get_projects_pending_approval failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500



from notification_storage import create_notification, get_active_notifications

# --- Notification API ---
@bp.route('/notifications/create', methods=['POST'])
def api_create_notification():
    data = request.get_json() or {}
    type_ = data.get('type')
    scope = data.get('scope')
    content = data.get('content')
    post_date = data.get('post_date')
    end_date = data.get('end_date')
    created_by = session.get('user_email', 'system')
    # Parse datetimes if needed
    try:
        post_date_dt = datetime.fromisoformat(post_date) if isinstance(post_date, str) else post_date
        end_date_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    try:
        create_notification(type_, content, post_date_dt, end_date_dt, created_by, scope)
        return jsonify({'success': True, 'message': 'Notification created'})
    except AssertionError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {e}'}), 500

# List notifications (active)
@bp.route('/notifications/list', methods=['GET'])
def api_list_notifications():
    try:
        # For superadmin, show all notifications including canceled
        from flask import session
        user_role = session.get('user_role', '')
        if user_role == 'superadmin':
            from notification_storage import get_all_notifications
            notifications = get_all_notifications()
        else:
            from notification_storage import get_active_notifications
            notifications = get_active_notifications()
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    


# Delete notification
@bp.route('/notifications/delete/<notification_id>', methods=['POST'])
def api_delete_notification(notification_id):
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        db.collection("notifications").document(notification_id).delete()
        return jsonify({'success': True, 'message': 'Notification deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Cancel notification (set status to 'inactive')
@bp.route('/notifications/cancel/<notification_id>', methods=['POST'])
def api_cancel_notification(notification_id):
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        db.collection("notifications").document(notification_id).delete()
        return jsonify({'success': True, 'message': 'Notification canceled and deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Get a single notification by ID
@bp.route('/notifications/get/<notification_id>', methods=['GET'])
def api_get_notification(notification_id):
    try:
        from firebase_config import get_firestore_db
        db = get_firestore_db()
        doc = db.collection("notifications").document(notification_id).get()
        if not doc.exists:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
        from notification_storage import _serialize_notification
        return jsonify({'success': True, 'notification': _serialize_notification(doc)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Update notification
@bp.route('/notifications/update/<notification_id>', methods=['POST'])
def api_update_notification(notification_id):
    try:
        db = firestore.client()
        data = request.get_json() or {}
        update_fields = {}
        for field in ["type", "scope", "content", "post_date", "end_date"]:
            if field in data:
                update_fields[field] = data[field]
        if update_fields:
            db.collection("notifications").document(notification_id).update(update_fields)
        return jsonify({'success': True, 'message': 'Notification updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    


from inquiries_storage import get_conversations, get_messages, add_message, delete_conversation


def _extract_user_photo(user_data):
    if not isinstance(user_data, dict):
        return ''
    return (
        user_data.get('photoURL')
        or user_data.get('photoUrl')
        or user_data.get('profilePhoto')
        or user_data.get('profile_photo')
        or user_data.get('photo_url')
        or user_data.get('photo')
        or user_data.get('user_photo')
        or ''
    )


def _extract_user_name(user_data):
    if not isinstance(user_data, dict):
        return ''
    full_name = str(user_data.get('name') or '').strip()
    if full_name:
        return full_name

    first_name = str(user_data.get('firstName') or user_data.get('first_name') or '').strip()
    last_name = str(user_data.get('lastName') or user_data.get('last_name') or '').strip()
    combined = f"{first_name} {last_name}".strip()
    if combined:
        return combined

    return str(user_data.get('username') or user_data.get('displayName') or '').strip()


def _looks_like_email(value):
    text = str(value or '').strip()
    return '@' in text and '.' in text


def _is_placeholder_name(name_value, email_value=''):
    name_text = str(name_value or '').strip()
    if not name_text:
        return True
    if _looks_like_email(name_text):
        return True

    email_text = str(email_value or '').strip().lower()
    if email_text and '@' in email_text:
        local_part = email_text.split('@', 1)[0].strip().lower()
        if local_part and name_text.lower() == local_part:
            return True
    return False


def _resolve_user_profile(identity_key='', email_hint=''):
    """Resolve user profile from users collection by document id first, then by email."""
    db = firestore.client()
    identity_key = str(identity_key or '').strip()
    email = str(email_hint or '').strip().lower()

    if not email and '@' in identity_key:
        email = identity_key.lower()

    # Try direct document id lookup first.
    if identity_key and '@' not in identity_key:
        try:
            doc = db.collection('users').document(identity_key).get()
            if doc.exists:
                data = doc.to_dict() or {}
                return {
                    'name': _extract_user_name(data),
                    'photo': _extract_user_photo(data),
                    'email': str(data.get('email') or email or '').strip().lower(),
                }
        except Exception:
            pass

    # Email lookup fallback.
    if email:
        try:
            docs = db.collection('users').where(filter=FieldFilter('email', '==', email)).limit(1).stream()
            for doc in docs:
                data = doc.to_dict() or {}
                return {
                    'name': _extract_user_name(data),
                    'photo': _extract_user_photo(data),
                    'email': str(data.get('email') or email or '').strip().lower(),
                }
        except Exception:
            # Fallback: positional where for compatibility, then scan.
            try:
                docs = db.collection('users').where('email', '==', email).limit(1).stream()
                for doc in docs:
                    data = doc.to_dict() or {}
                    return {
                        'name': _extract_user_name(data),
                        'photo': _extract_user_photo(data),
                        'email': str(data.get('email') or email or '').strip().lower(),
                    }
            except Exception:
                pass

            try:
                for doc in db.collection('users').stream():
                    data = doc.to_dict() or {}
                    candidate_emails = [
                        str(data.get('email') or '').strip().lower(),
                        str(data.get('user_email') or '').strip().lower(),
                        str(data.get('userEmail') or '').strip().lower(),
                    ]
                    if email in [e for e in candidate_emails if e]:
                        return {
                            'name': _extract_user_name(data),
                            'photo': _extract_user_photo(data),
                            'email': email,
                        }
            except Exception:
                pass

    return {'name': '', 'photo': '', 'email': email}


# === INQUIRIES (MESSENGER) API ===
@bp.route('/inquiries/conversations', methods=['GET'])
@firebase_auth_required
def api_get_inquiry_conversations():
    try:
        convos = get_conversations()

        # Enrich conversation display data from users profile when missing.
        for convo in convos:
            try:
                convo_key = str(convo.get('user_id') or convo.get('email') or convo.get('user_email') or '').strip()
                convo_email = str(convo.get('email') or convo.get('user_email') or '').strip().lower()
                convo_name = str(convo.get('user_name') or '').strip()
                needs_name = _is_placeholder_name(convo_name, convo_email)
                needs_photo = not convo.get('user_photo')
                needs_email = not convo.get('email')

                if not needs_name and not needs_photo and not needs_email:
                    continue

                profile = _resolve_user_profile(convo_key, convo_email)
                if needs_photo and profile.get('photo'):
                    convo['user_photo'] = profile.get('photo')
                if needs_name and profile.get('name'):
                    convo['user_name'] = profile.get('name')
                if needs_email and profile.get('email'):
                    convo['email'] = profile.get('email')
            except Exception:
                # Never fail the entire list due to one malformed user profile.
                continue

        return jsonify({'success': True, 'conversations': convos})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/inquiries/messages/<user_id>', methods=['GET'])
@firebase_auth_required
def api_get_inquiry_messages(user_id):
    def _json_safe(v):
        if isinstance(v, dict):
            return {str(k): _json_safe(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_json_safe(i) for i in v]
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        if hasattr(v, 'isoformat'):
            try:
                return v.isoformat()
            except Exception:
                return str(v)
        return str(v)

    def _ts_sort_value(msg):
        ts = msg.get('timestamp')
        if hasattr(ts, 'timestamp'):
            try:
                return ts.timestamp()
            except Exception:
                return 0
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
            except Exception:
                return 0
        return 0

    try:
        convo_key = (user_id or '').strip()
        if not convo_key:
            convo_key = (request.args.get('email') or session.get('user_email') or '').strip()
        raw_msgs = get_messages(convo_key)
        msgs = [m for m in (raw_msgs or []) if isinstance(m, dict)]

        # Fill missing user profile info for end-user messages.
        profile = _resolve_user_profile(convo_key, convo_key)
        admin_roles = {'superadmin', 'super-admin', 'municipal', 'municipal_admin', 'regional', 'regional_admin', 'national', 'national_admin'}
        for msg in msgs:
            sender_role = str(msg.get('sender_role') or '').strip().lower()
            is_admin_msg = bool(msg.get('is_admin')) or sender_role in admin_roles
            if is_admin_msg:
                continue

            if not msg.get('user_photo') and profile.get('photo'):
                msg['user_photo'] = profile.get('photo')
            current_name = str(msg.get('user_name') or '').strip()
            msg_email = str(msg.get('email') or msg.get('user_email') or convo_key or '').strip().lower()
            if _is_placeholder_name(current_name, msg_email) and profile.get('name'):
                msg['user_name'] = profile.get('name')

        safe_msgs = _json_safe(msgs)
        return jsonify({'success': True, 'messages': safe_msgs})
    except Exception as e:
        # Fallback path: direct collection scan to keep UI alive even when primary path fails.
        try:
            import traceback
            traceback.print_exc()

            convo_key = (user_id or '').strip()
            if not convo_key:
                convo_key = (request.args.get('email') or session.get('user_email') or '').strip()
            key_l = convo_key.lower()

            docs = firestore.client().collection('inquiries').stream()
            fallback_msgs = []
            for d in docs:
                data = d.to_dict() or {}
                if not isinstance(data, dict):
                    continue
                msg_uid = str(data.get('user_id') or '').strip()
                msg_email = str(data.get('email') or data.get('user_email') or '').strip().lower()
                if msg_uid == convo_key or msg_email == key_l:
                    fallback_msgs.append(data)

            fallback_msgs.sort(key=_ts_sort_value)
            return jsonify({'success': True, 'messages': _json_safe(fallback_msgs), 'fallback': True})
        except Exception as inner:
            return jsonify({'success': False, 'message': f'{e} | fallback failed: {inner}'}), 500

@bp.route('/inquiries/send', methods=['POST'])
@firebase_auth_required
def api_send_inquiry_message():
    try:
        user_id = (request.form.get('user_id') or '').strip()
        user_email = (request.form.get('email') or request.form.get('user_email') or '').strip().lower()
        if not user_email and '@' in user_id:
            user_email = user_id.lower()

        if not user_id:
            user_id = user_email or (session.get('user_email') or '').strip().lower()

        if not user_email and '@' in user_id:
            user_email = user_id.lower()

        if not user_id:
            return jsonify({'success': False, 'message': 'User identity is required'}), 400

        user_name = (request.form.get('user_name') or '').strip()
        if not user_name:
            user_name = (session.get('user_name') or user_email or 'User').strip()

        session_user_id = str(session.get('user_id') or '').strip()
        session_user_email = str(session.get('user_email') or '').strip().lower()

        sender_email = (session.get('user_email') or '').strip().lower() or user_email
        sender_role = (session.get('user_role') or '').strip().lower()
        is_admin_sender = sender_role in {'superadmin', 'super-admin', 'municipal', 'municipal_admin', 'regional', 'regional_admin', 'national', 'national_admin'}

        message = request.form.get('message', '')
        user_photo = request.form.get('user_photo', '')

        # Backfill sender profile when photo/name is missing or name is placeholder-like.
        needs_name = _is_placeholder_name(user_name, user_email or session_user_email)
        if not user_photo or needs_name:
            resolved = {'name': '', 'photo': '', 'email': user_email}
            identity_candidates = [session_user_id, user_id]
            email_candidates = [user_email, session_user_email, sender_email]

            for identity in identity_candidates:
                for email_candidate in email_candidates:
                    resolved = _resolve_user_profile(identity, email_candidate)
                    if resolved.get('name') or resolved.get('photo'):
                        break
                if resolved.get('name') or resolved.get('photo'):
                    break

            if not user_photo and resolved.get('photo'):
                user_photo = resolved.get('photo')
            if needs_name and resolved.get('name'):
                user_name = resolved.get('name')

        file_url = ''
        file_type = ''
        file_name = ''
        if 'file' in request.files:
            file = request.files['file']
            file_url = _upload_to_cloudinary(file, folder='tlph/inquiries')
            file_type = file.mimetype
            file_name = file.filename or ''
        doc = add_message(
            user_id,
            user_name,
            message,
            user_photo,
            file_url,
            file_type,
            file_name,
            user_email=user_email,
            sender_email=sender_email,
            sender_role=sender_role,
            is_admin=is_admin_sender,
        )
        return jsonify({'success': True, 'message': doc})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/inquiries/conversation/<conversation_key>', methods=['DELETE'])
@firebase_auth_required
def api_delete_inquiry_conversation(conversation_key):
    try:
        role = str(session.get('user_role') or '').strip().lower()
        allowed_roles = {
            'superadmin',
            'super-admin',
            'municipal',
            'municipal_admin',
            'regional',
            'regional_admin',
            'national',
            'national_admin',
        }
        if role not in allowed_roles:
            return jsonify({'success': False, 'message': 'Forbidden'}), 403

        key = str(conversation_key or '').strip()
        if not key:
            return jsonify({'success': False, 'message': 'Conversation key is required'}), 400

        deleted_count = delete_conversation(key)
        return jsonify({'success': True, 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500