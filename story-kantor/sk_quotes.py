"""Bank quote 'Story Kantor' — mode HEMAT (tanpa AI/Anthropic).

Kumpulan quote relatable/sindiran kerja yang udah ditulis. `pick_quote(avoid)`
pilih 1 yang belum baru dibahas → output kompatibel sama sk_generator.generate_content.
"""
import random
import re

HANDLE = "storykantor.idn"

# tiap quote: (hook = statement utama, line1, line2)
QUOTES = [
    ("Capeknya kerja bukan karena tugasnya, tapi karena harus pura-pura sibuk pas bos lewat.",
     "Yang penting keliatan produktif, bukan beneran produktif.",
     "Drama kantor kadang lebih melelahkan dari kerjaannya sendiri."),
    ("Yang cari muka naik duluan, yang kerja beneran cuma jadi penonton.",
     "Di kantor, kadang yang dinilai bukan hasil, tapi siapa yang paling pinter ngomong.",
     "Kerja diem-diem itu mulia, tapi sering kalah sama yang jago pencitraan."),
    ("Gaji numpang lewat, cicilan yang tetap setia.",
     "Tanggal muda cuma mampir, tanggal tua yang lama tinggal.",
     "Kerja keras sebulan, habis dalam seminggu."),
    ("Senin itu bukti kalau weekend gak pernah cukup.",
     "Belum sempat istirahat, udah disuruh produktif lagi.",
     "Badan masuk kerja, jiwa masih ketinggalan di hari Minggu."),
    ("Meeting yang harusnya 10 menit, molor jadi 2 jam tanpa keputusan.",
     "Habis rapat malah nambah kerjaan, bukan nyelesaiin.",
     "Rapat paling produktif itu yang dibatalin."),
    ("Yang bikin lembur bukan kerjaan, tapi keputusan yang gonta-ganti.",
     "Udah dikerjain sesuai brief, eh brief-nya yang berubah.",
     "Revisi ke-17 dengan alasan 'balik ke yang awal aja'."),
    ("Kerja keras kamu diapresiasi pakai kata 'tolong sekalian ya'.",
     "Makin rajin, makin dikasih kerjaan orang lain.",
     "Yang bisa diandalkan sering dijadikan tumbal."),
    ("Grup WA kantor: tempat pesan masuk jam 11 malam, dibales 'noted' doang.",
     "Libur cuma di kalender, chat kerjaan tetap jalan.",
     "Notif grup kantor lebih rajin dari alarm pagi."),
    ("Kopi bukan lagi kenikmatan, tapi kebutuhan buat bertahan hidup.",
     "Tanpa kopi, mata melek badan tidur.",
     "Satu-satunya teman yang ngerti beratnya pagi."),
    ("Katanya kerja buat hidup, kok malah hidup buat kerja?",
     "Pulang udah gelap, berangkat masih gelap.",
     "Sabtu buat rebahan, Minggu buat overthinking soal Senin."),
    ("Bos: 'anggap aja kantor rumah kedua.' Ya tapi rumah gak nyuruh lembur.",
     "Loyalitas diminta, tapi kesejahteraan dilupakan.",
     "Dianggap keluarga cuma pas ada kerjaan tambahan."),
    ("Resign itu nakutin, tapi bertahan di tempat yang salah lebih nakutin.",
     "Zona nyaman yang bikin kamu diam di tempat.",
     "Kadang yang bikin capek bukan kerjaannya, tapi lingkungannya."),
    ("Yang paling sibuk belum tentu paling kerja, kadang cuma paling jago keliatan sibuk.",
     "Buka banyak tab bukan berarti banyak progres.",
     "Sok sibuk juga butuh energi, sayangnya gak dibayar."),
    ("Naik gaji 10 persen, kerjaan naik 200 persen.",
     "Tanggung jawab nambah, apresiasi tetap segitu.",
     "Promosi kadang cuma ganti nama beban."),
    ("Rekan kerja toxic bikin senin makin berat.",
     "Bukan kerjaannya yang bikin stres, tapi orang-orangnya.",
     "Kadang yang paling ngajarin sabar itu meja sebelah."),
    ("Kamu bukan malas, kamu cuma capek yang gak pernah dikasih istirahat.",
     "Produktif terus itu bukan target, itu jebakan.",
     "Istirahat bukan hadiah, itu kebutuhan."),
    ("Deadline mepet karena atasan mikirnya juga mepet.",
     "Yang santai di atas, yang panik di bawah.",
     "Kerjaan kilat, keputusan lambat."),
    ("Cuti diambil, tapi laptop tetap dibawa.",
     "Liburan sambil mantau email bukan liburan namanya.",
     "Badan di pantai, pikiran di kantor."),
    ("Yang penting bukan seberapa lama di kantor, tapi seberapa dihargai.",
     "Datang paling pagi pulang paling malam belum tentu diliat.",
     "Jam kerja panjang bukan tanda dedikasi, kadang tanda sistem yang rusak."),
    ("Kadang yang kamu butuhin bukan motivasi, tapi lingkungan kerja yang sehat.",
     "Susah semangat di tempat yang gak menghargai.",
     "Bukan kamu yang kurang, tapi tempatnya yang gak cocok."),
]

_STOP = set("yang dan itu bukan tapi kamu kita gue buat pas jadi dari lebih udah".split())


def _kw(s):
    return set(w for w in re.findall(r"[a-z]+", s.lower()) if len(w) > 3 and w not in _STOP)


def _dup(hook, avoid):
    hw = _kw(hook)
    for a in avoid or []:
        if hw and len(hw & _kw(a)) >= 3:
            return True
    return False


def pick_quote(avoid=None) -> dict:
    """Pilih 1 quote (skip yang mirip avoid). Output = {type,kicker,hook,lines,caption,topic}."""
    pool = QUOTES[:]
    random.shuffle(pool)
    q = next((x for x in pool if not _dup(x[0], avoid or [])), pool[0])
    hook, l1, l2 = q
    caption = (f"{hook}\n\n{l1}\n{l2}\n\n"
               f"Yang ngerasa, tag temen kantormu 👇\n\n"
               f"#storykantor #anakkantoran #relatable #duniakerja #curhatkantor")
    return {"type": "relatable", "kicker": "STORY KANTOR", "topic": "kerja",
            "hook": hook, "lines": [l1, l2], "caption": caption}
