import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

# Veritabanı Bağlantısı
conn = sqlite3.connect("finans_yonetim.db", check_same_thread=False)
cursor = conn.cursor()


# Tabloları Oluştur
def init_db():
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cariler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT,
            tur TEXT,
            telefon TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS hesaplar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT,
            bakiye REAL
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            cari_id INTEGER,
            hesap_id INTEGER,
            tur TEXT,
            kategori TEXT,
            tutar REAL,
            vade_tarihi TEXT,
            durum TEXT,
            aciklama TEXT
        )
    """)
  conn.commit()


init_db()

st.set_page_config(
    page_title="Finans Yönetim Paneli", page_icon="💰", layout="wide"
)

st.title("📊 Dalkılıç Grup - Finans & Nakit Akış Yönetimi")

# Sol Menü
menu = st.sidebar.selectbox(
    "Menü",
    [
        "Genel Bakış",
        "Gelir / Gider Ekle",
        "Cari Hesaplar",
        "Banka / Kasalar",
        "Vadesi Gelenler",
    ],
)

# 1. GENEL BAKIŞ & RAPORLAR
if menu == "Genel Bakış":
  st.subheader("Finansal Özet ve Nakit Akışı")

  # Özet Kartları için Veriler
  try:
    df_islem = pd.read_sql_query("SELECT * FROM islemler", conn)
    df_hesap = pd.read_sql_query("SELECT * FROM hesaplar", conn)

    toplam_kasa = df_hesap["bakiye"].sum() if not df_hesap.empty else 0
    toplam_gelir = (
        df_islem[df_islem["tur"] == "Gelir"]["tutar"].sum()
        if not df_islem.empty
        else 0
    )
    toplam_gider = (
        df_islem[df_islem["tur"] == "Gider"]["tutar"].sum()
        if not df_islem.empty
        else 0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Banka / Kasa", f"{toplam_kasa:,.2f} TL")
    col2.metric("Toplam Gelir", f"{toplam_gelir:,.2f} TL", delta="Tahsilatlar")
    col3.metric(
        "Toplam Gider", f"{toplam_gider:,.2f} TL", delta_color="inverse"
    )

    st.markdown("---")
    st.subheader("Son İşlemler")
    if not df_islem.empty:
      st.dataframe(
          df_islem.tail(10), use_container_width=True, hide_index=True
      )
    else:
      st.info("Henüz kayıtlı bir işlem bulunmuyor.")
  except Exception as e:
    st.warning("Henüz veri bulunmuyor. Sol menüden veri ekleyebilirsiniz.")

# 2. GELİR / GİDER EKLE
elif menu == "Gelir / Gider Ekle":
  st.subheader("Yeni Gelir / Gider / Tahsilat Girişi")

  cariler = cursor.execute("SELECT id, ad FROM cariler").fetchall()
  cari_dict = {c[1]: c[0] for c in cariler}

  hesaplar = cursor.execute("SELECT id, ad FROM hesaplar").fetchall()
  hesap_dict = {h[1]: h[0] for h in hesaplar}

  with st.form("islem_formu"):
    col1, col2 = st.columns(2)
    with col1:
      tur = st.selectbox("İşlem Türü", ["Gelir", "Gider"])
      kategori = st.selectbox(
          "Kategori",
          [
              "Satış / Tahsilat",
              "Mal Alımı / Tedarik",
              "Kira",
              "Personel / Sigorta",
              "Reklam / Medya",
              "Diğer",
          ],
      )
      tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)

    with col2:
      secilen_cari = st.selectbox(
          "Cari (Müşteri / Tedarikçi)", list(cari_dict.keys())
      )
      secilen_hesap = st.selectbox("İşlem Yapılacak Hesap", list(hesap_dict.keys()))
      tarih = st.date_input("İşlem Tarihi")
      vade_tarihi = st.date_input("Vade / Ödeme Tarihi")

    aciklama = st.text_area("Açıklama / Not")
    durum = st.selectbox("Durum", ["Ödendi / Tamamlandı", "Bekliyor"])

    submit = st.form_submit_button("İşlemi Kaydet")

    if submit and secilen_cari and secilen_hesap:
      c_id = cari_dict[secilen_cari]
      h_id = hesap_dict[secilen_hesap]
      cursor.execute(
          """
                INSERT INTO islemler (tarih, cari_id, hesap_id, tur, kategori, tutar, vade_tarihi, durum, aciklama)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              str(tarih),
              c_id,
              h_id,
              tur,
              kategori,
              tutar,
              str(vade_tarihi),
              durum,
              aciklama,
          ),
      )

      # Hesap bakiyesini güncelle (Eğer ödendiyse)
      if durum == "Ödendi / Tamamlandı":
        faktor = 1 if tur == "Gelir" else -1
        cursor.execute(
            "UPDATE hesaplar SET bakiye = bakiye + ? WHERE id = ?",
            (tutar * faktor, h_id),
        )

      conn.commit()
      st.success("İşlem başarıyla kaydedildi!")

# 3. CARİ HESAPLAR
elif menu == "Cari Hesaplar":
  st.subheader("Cari Hesap (Müşteri & Tedarikçi) Yönetimi")

  with st.form("yeni_cari"):
    st.write("Yeni Cari Ekle")
    ad = st.text_input("Cari Adı / Firma Ünvanı")
    tur = st.selectbox("Cari Türü", ["Müşteri", "Tedarikçi"])
    telefon = st.text_input("Telefon")
    kaydet = st.form_submit_button("Cari Oluştur")
    if kaydet and ad:
      cursor.execute(
          "INSERT INTO cariler (ad, tur, telefon) VALUES (?, ?, ?)",
          (ad, tur, telefon),
      )
      conn.commit()
      st.success(f"{ad} başarıyla eklendi.")

  st.markdown("---")
  st.subheader("Kayıtlı Cariler")
  df_cari = pd.read_sql_query("SELECT * FROM cariler", conn)
  if not df_cari.empty:
    st.dataframe(df_cari, use_container_width=True, hide_index=True)
  else:
    st.info("Kayıtlı cari bulunmuyor.")

# 4. BANKA / KASALAR
elif menu == "Banka / Kasalar":
  st.subheader("Banka Hesapları ve Kasalar")

  with st.form("yeni_hesap"):
    st.write("Yeni Hesap Ekle")
    hesap_adi = st.text_input(
        "Hesap Adı (Örn: İş Bankası Ticari, Nakit Kasa)"
    )
    baslangic_bakiye = st.number_input(
        "Başlangıç Bakiyesi", value=0.0, step=100.0
    )
    h_kaydet = st.form_submit_button("Hesap Ekle")
    if h_kaydet and hesap_adi:
      cursor.execute(
          "INSERT INTO hesaplar (ad, bakiye) VALUES (?, ?)",
          (hesap_adi, baslangic_bakiye),
      )
      conn.commit()
      st.success(f"{hesap_adi} eklendi.")

  st.markdown("---")
  df_hesap = pd.read_sql_query("SELECT * FROM hesaplar", conn)
  if not df_hesap.empty:
    st.dataframe(df_hesap, use_container_width=True, hide_index=True)
  else:
    st.info("Tanımlı hesap bulunmuyor.")

# 5. VADESİ GELENLER
elif menu == "Vadesi Gelenler":
  st.subheader("Yaklaşan Ödemeler ve Tahsilatlar")
  try:
    df_bekleyen = pd.read_sql_query(
        "SELECT * FROM islemler WHERE durum = 'Bekliyor'", conn
    )
    if not df_bekleyen.empty:
      st.dataframe(df_bekleyen, use_container_width=True, hide_index=True)
    else:
      st.info("Bekleyen ödeme veya tahsilat bulunmuyor.")
  except:
    st.info("Henüz veri yok.")