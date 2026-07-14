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
    ("Gaji telat sehari, grup WA HR mendadak paling ramai sejagat kantor.",
     "Yang biasanya diem, jadi paling rajin nanya kapan cair.",
     "Sabar ada batasnya, apalagi soal duit."),
    ("THR cair, abis buat nutup utang bulan lalu.",
     "Niatnya buat seneng-seneng, ujungnya buat bayar cicilan.",
     "Bonus paling ditunggu, paling cepat juga abisnya."),
    ("WFH katanya bebas, tapi laptop nyala lebih lama dari pas ngantor.",
     "Gak ada jam pulang kalau kerjaan masih numpuk di layar.",
     "Kerja dari rumah, rumah jadi kantor 24 jam."),
    ("Kerjaan orang lain pelan-pelan pindah ke mejamu, tanpa pernah resmi jadi tugasmu.",
     "Awalnya bantuin sekali, lama-lama jadi tanggung jawab tetap.",
     "Baik hati di kantor kadang dibalas tambahan beban."),
    ("Review kinerja tahunan isinya penilaian orang yang jarang liat kerjaanmu langsung.",
     "Yang keliatan cuma yang rajin lapor, bukan yang rajin kerja.",
     "Penilaian kantor kadang soal keliatan, bukan soal hasil."),
    ("Atasan minta ide segar, tiap ide baru ujungnya 'coba cara lama dulu aja'.",
     "Kreativitas diminta, keputusan tetap yang aman-aman aja.",
     "Inovasi cuma jargon kalau ujungnya balik ke rutinitas."),
    ("Rapat dadakan jam 5 sore, judulnya penting, isinya bisa dikirim lewat chat.",
     "Waktu istirahat kepotong buat sesuatu yang harusnya semenit doang.",
     "Rapat paling lama sering yang paling gak perlu."),
    ("Cuti sakit diambil, tetap ditanyain kapan bisa online.",
     "Sakit aja masih harus standby, apalagi cuma capek biasa.",
     "Istirahat penuh itu privilese, bukan hak yang otomatis dikasih."),
    ("Kerja giat bertahun-tahun, jabatan gitu-gitu aja.",
     "Yang naik cuma tanggung jawab, bukan posisi.",
     "Loyalitas dihargai ucapan terima kasih, bukan promosi."),
    ("Notifikasi kerja masuk pas weekend, judulnya 'santai aja dibales kapan bisa'.",
     "Tapi telat bales sejam, udah ditanyain lagi.",
     "Kata 'santai aja' di kantor sering artinya sebaliknya."),
    ("Diawasin ketat tiap 10 menit, katanya biar kerjaan lebih rapi.",
     "Dipercaya kerja sendiri kadang jadi hal langka.",
     "Diawasin ketat bukan bikin kerja lebih baik, cuma bikin makin cemas."),
    ("Kantor bilang 'anggap kita keluarga', tapi keluarga gak minta lembur tanpa bayar.",
     "Kata manis di orientasi, beda sama kenyataan pas kerja.",
     "Kekeluargaan kantor sering cuma sampai jam kerja aja."),
    ("Gaji naik ikut standar tahunan, harga-harga naik ikut standar sendiri.",
     "Kenaikan gaji kadang cuma nutup selisih, bukan nambah simpanan.",
     "Naik gaji di atas kertas, kepakenya abis sebelum kerasa."),
    ("Medsos kerja keliatan produktif terus, padahal laporan numpuk nunggu di-notice atasan.",
     "Citra rapi di medsos, laporan tetap keteteran.",
     "Citra online sering lebih rapi dari kondisi kerja sebenarnya."),
    ("Semangat kerja awal masuk beda jauh sama semangat tahun ketiga.",
     "Idealisme luntur pelan-pelan ketemu rutinitas.",
     "Yang tersisa cuma disiplin datang tepat waktu."),
    ("Kerja keras dipuji sebentar, kerja cerdas malah dicurigai males.",
     "Yang penting keliatan capek, bukan keliatan efisien.",
     "Kantor kadang lebih ngargain proses ribet daripada hasil cepat."),
    ("Interview kerja nanya soal passion, giliran diterima nanya kenapa lambat submit laporan.",
     "Idealisme dibahas pas rekrutmen, realita dibahas pas evaluasi.",
     "Semangat kerja gampang ditanya, jarang difasilitasi."),
    ("Diminta speak up, giliran speak up malah dicap banyak drama.",
     "Kritik membangun sering dianggap sikap kurang bersyukur.",
     "Diam dianggap aman, padahal cuma nahan."),
    ("Kerja lembur dibilang 'buat pengalaman', padahal cuma nutup kurangnya orang.",
     "Pengalaman gratis lebih sering nguntungin perusahaan.",
     "Kerja ekstra sering dibungkus kata belajar biar keliatan wajar."),
    ("Chat kerja masuk jam 10 malam, dibales 'noted' jam itu juga.",
     "Batas jam kerja makin kabur makin ke sini.",
     "Yang harusnya istirahat, tetap standby demi kata cepat tanggap."),
    ("Kerjaan dibagi rata katanya, yang cepat selesai malah dikasih tambahan lagi.",
     "Cepat kerja bukan hadiah, kadang jadi bumerang sendiri.",
     "Rajin dibales rajin dikasih beban, bukan rajin diistirahatin."),
    ("Diskusi kerja 30 menit, keputusannya diambil 5 menit terakhir sama satu orang.",
     "Pendapat ditanya, keputusan tetap punya sendiri.",
     "Rapat kadang formalitas doang sebelum keputusan yang udah dibuat duluan."),
    ("Semangat abis gajian bertahan sampai H+3, abis itu balik lagi ke mode survive.",
     "Motivasi keuangan cuma nempel sebentar.",
     "Yang bikin capek bukan gajinya, tapi jaraknya ke gajian berikutnya."),
    ("Dikasih tanggung jawab lebih tanpa gelar lebih, katanya 'buat portofolio'.",
     "Portofolio nambah, slip gaji tetap sama.",
     "Pengakuan formal sering telat dari beban yang udah nambah duluan."),
    ("Jam istirahat makan siang, chat kerjaan tetap masuk kayak gak kenal waktu.",
     "Istirahat sejam berasa kepotong jadi setengah.",
     "Waktu makan siang jadi waktu kerja versi santai doang."),
    ("Kantor minta inisiatif, giliran inisiatif salah malah disalahin sendirian.",
     "Berani ambil keputusan jadi lebih berisiko dari diam aja.",
     "Inisiatif cuma aman kalau hasilnya bener."),
    ("Target kerja naik tiap kuartal, alasan naiknya gak pernah dijelasin sedetail targetnya.",
     "Angka gampang dinaikin, alasannya sering menggantung.",
     "Yang dikejar cuma pencapaian, jarang yang dijelasin logikanya."),
    ("Karyawan lama dianggap paham semua tanpa pernah diajarin ulang.",
     "Pengalaman dianggap otomatis nutup training yang gak pernah ada.",
     "Senioritas kadang jadi alasan buat gak dikasih penjelasan."),
    ("Kerja tim katanya, giliran gagal yang disorot cuma satu nama.",
     "Sukses milik tim, gagal milik orang tertentu.",
     "Kerja bareng enak pas lancar, sepi pas ada yang harus tanggung jawab."),
    ("Jam pulang kantor cuma formalitas, kerjaan pulang bareng laptop ke rumah.",
     "Absen keluar gedung, kerjaan belum keluar dari kepala.",
     "Jarak kantor-rumah gak nolong kalau pikiran masih di kantor."),
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
    avoid = avoid or []
    pool = QUOTES[:]
    random.shuffle(pool)
    q = next((x for x in pool if not _dup(x[0], avoid)), None)
    if q is None:
        # Bank abis (semua quote kena avoid, biasa kejadian krn bank cuma ~20 & posting
        # 4x/hari) → JANGAN asal pool[0] (bisa balikin yang BARU aja dipost). Pilih yang
        # PALING LAMA gak muncul di riwayat (avoid diurut dari paling baru).
        def _last_seen_rank(hook: str) -> int:
            for i, a in enumerate(avoid):
                if _dup(hook, [a]):
                    return i
            return len(avoid)  # gak ketemu sama sekali di riwayat = paling lama/aman
        q = max(pool, key=lambda x: _last_seen_rank(x[0]))
    hook, l1, l2 = q
    caption = (f"{hook}\n\n{l1}\n{l2}\n\n"
               f"Yang ngerasa, tag temen kantormu 👇\n\n"
               f"#storykantor #anakkantoran #relatable #duniakerja #curhatkantor")
    return {"type": "relatable", "kicker": "STORY KANTOR", "topic": "kerja",
            "hook": hook, "lines": [l1, l2], "caption": caption}
