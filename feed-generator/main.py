import os, shutil, tempfile, zipfile
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from caption_generator import generate_copy
from image_maker import make_slides

app = FastAPI(title="Feed Generator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "feed-generator"}


@app.post("/generate")
async def generate(
    photo: UploadFile = File(..., description="Foto produk (JPG/PNG)"),
    product_name: str = Form(...),
    price: str = Form(...),
    description: str = Form(...),
    niche: str = Form("default"),
    contact: str = Form(""),
):
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Format foto harus JPG, PNG, atau WebP")

    tmpdir = tempfile.mkdtemp()
    try:
        # Simpan foto
        photo_path = os.path.join(tmpdir, "photo.jpg")
        data = await photo.read()
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(400, "Ukuran foto maksimal 20MB")
        with open(photo_path, "wb") as f:
            f.write(data)

        # Generate copy dengan Claude
        try:
            copy = generate_copy(product_name, price, description, niche)
        except Exception as e:
            raise HTTPException(500, f"Gagal generate copy: {e}")

        # Generate slides
        out_dir = os.path.join(tmpdir, "slides")
        os.makedirs(out_dir)
        try:
            slide_paths = make_slides(
                photo_path=photo_path,
                product_name=product_name,
                price=price,
                hook=copy.get("hook", "Produk terbaik untuk kamu"),
                tagline=copy.get("tagline", "Kualitas terjamin"),
                features=copy.get("features", ["Kualitas premium", "Harga terjangkau", "Cepat sampai"]),
                feature_descs=copy.get("feature_descs", ["", "", ""]),
                cta=copy.get("cta", "Order sekarang!"),
                niche=niche,
                out_dir=out_dir,
            )
        except Exception as e:
            raise HTTPException(500, f"Gagal buat gambar: {e}")

        # Simpan caption
        caption_path = os.path.join(out_dir, "caption.txt")
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(copy.get("caption", ""))

        # Buat ZIP
        safe_name = "".join(c for c in product_name[:20] if c.isalnum() or c in " _-").strip()
        zip_path = os.path.join(tmpdir, f"{safe_name or 'feeds'}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for sp in slide_paths:
                zf.write(sp, os.path.basename(sp))
            zf.write(caption_path, "caption.txt")

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{safe_name or 'feeds'}_IG.zip",
            background=BackgroundTask(shutil.rmtree, tmpdir, True),
        )

    except HTTPException:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(500, f"Error: {e}")
