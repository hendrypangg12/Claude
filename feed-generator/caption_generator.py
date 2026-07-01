import anthropic, json, os, re

_client = None

def _get():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

SYSTEM = (
    "Kamu copywriter ahli konten Instagram UMKM Indonesia yang persuasif dan kreatif. "
    "Balas HANYA dengan JSON valid tanpa markdown, komentar, atau teks tambahan apapun."
)

def generate_copy(product_name: str, price: str, description: str, niche: str) -> dict:
    prompt = f"""Buat konten feed Instagram untuk produk UMKM ini:
Nama Produk: {product_name}
Harga: {price}
Deskripsi: {description}
Niche/Kategori: {niche}

Balas dengan JSON PERSIS format ini:
{{
  "hook": "kalimat pembuka menarik, max 10 kata, langsung to the point",
  "tagline": "tagline singkat produk, max 7 kata",
  "features": ["keunggulan singkat 1", "keunggulan singkat 2", "keunggulan singkat 3"],
  "feature_descs": ["penjelasan 1 kalimat", "penjelasan 1 kalimat", "penjelasan 1 kalimat"],
  "cta": "ajakan beli singkat, max 5 kata",
  "caption": "caption IG 3-4 kalimat natural + 5 hashtag relevan"
}}"""

    for attempt in range(3):
        try:
            resp = _get().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=700,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                m = re.search(r'\{[\s\S]*\}', text)
                if m:
                    return json.loads(m.group())
        except Exception:
            if attempt == 2:
                raise
    raise ValueError("Gagal generate copy dari Claude")
