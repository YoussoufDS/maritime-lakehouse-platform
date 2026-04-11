"""
Maritime Lakehouse Platform
Upload fichiers locaux vers ADLS Gen2
"""

import os
from azure.storage.blob import BlobServiceClient

# ─── CONFIG — remplace ces valeurs ───────────────
STORAGE_ACCOUNT = "adlsmaritimedev"
STORAGE_KEY     = 
CONTAINER       = "landing"
# ─────────────────────────────────────────────────

LOCAL_BASE = "output_files/landing/files"

def upload_folder():
    conn_str = (
        f"DefaultEndpointsProtocol=https;"
        f"AccountName={STORAGE_ACCOUNT};"
        f"AccountKey={STORAGE_KEY};"
        f"EndpointSuffix=core.windows.net"
    )

    client    = BlobServiceClient.from_connection_string(conn_str)
    container = client.get_container_client(CONTAINER)

    total = 0
    errors = 0

    for root, dirs, files in os.walk(LOCAL_BASE):
        for filename in files:
            local_path = os.path.join(root, filename)
            
            # Construire le chemin blob
            relative = os.path.relpath(local_path, "output_files/landing")
            blob_path = relative.replace(os.sep, "/")

            try:
                with open(local_path, "rb") as data:
                    container.upload_blob(
                        blob_path,
                        data,
                        overwrite=True
                    )
                total += 1
                if total % 50 == 0:
                    print(f"  Uploaded {total} files... ({blob_path})")
            except Exception as e:
                errors += 1
                print(f"  ERROR: {blob_path} -> {e}")

    print(f"\n  Done! {total} files uploaded, {errors} errors")

if __name__ == "__main__":
    print("=" * 55)
    print("  Maritime Lakehouse - Upload to ADLS Gen2")
    print(f"  Container : {CONTAINER}")
    print(f"  Local path: {LOCAL_BASE}")
    print("=" * 55)
    upload_folder()