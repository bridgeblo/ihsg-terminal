import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# 1. KONFIGURASI HALAMAN & TAMPILAN MOBILE-FRIENDLY
# ==============================================================================
st.set_page_config(
    page_title="IHSG Sentimen & Market Terminal", 
    layout="wide", 
    page_icon="📈"
)

# Kustomisasi CSS agar kartu metrik terlihat lebih rapi dan responsif di layar HP
st.markdown("""
<style>
    /* Mengoptimalkan ukuran teks metrik di perangkat seluler */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 800;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600;
        color: #94a3b8;
    }
    /* Mempercantik tampilan box info */
    .stAlert {
        border-radius: 12px;
    }
</style>
""", unsafe_style_allowed=True)

st.title("🖥️ Asia & S&P 500 Market Terminal")
st.caption("Memantau pergerakan bursa saham Asia dan AS secara langsung (real-time) sebagai indikator arah sentimen IHSG.")
st.markdown("---")

# ==============================================================================
# 2. DEFINISI TICKER BURSA GLOBAL
# ==============================================================================
market_tickers = {
    "Indonesia (IHSG)": "^JKSE",
    "Amerika Serikat (S&P 500)": "^GSPC",
    "Jepang (Nikkei 225)": "^N225",
    "Hong Kong (Hang Seng)": "^HSI",
    "Singapura (Straits Times)": "^STI",
    "Malaysia (KLCI)": "^KLSE",
    "Korea Selatan (KOSPI)": "^KS11",
    "Shanghai (Composite)": "000001.SS"
}

# Sidebar untuk Pengaturan Terminal
st.sidebar.header("⚙️ Pengaturan Terminal")
period_choice = st.sidebar.selectbox(
    "Pilih Periode Data:", 
    ["1 Hari (Intraday)", "1 Minggu", "1 Bulan", "3 Bulan", "1 Tahun"], 
    index=2 # Default ke 1 Bulan agar grafik perbandingan terlihat lebih stabil
)

# Pemetaan pilihan waktu untuk pustaka yfinance
period_map = {
    "1 Hari (Intraday)": {"period": "1d", "interval": "1m"},
    "1 Minggu": {"period": "5d", "interval": "15m"},
    "1 Bulan": {"period": "1mo", "interval": "1h"},
    "3 Bulan": {"period": "3mo", "interval": "1d"},
    "1 Tahun": {"period": "1y", "interval": "1d"}
}

selected_period = period_map[period_choice]["period"]
selected_interval = period_map[period_choice]["interval"]

# Tombol paksa perbarui data
if st.sidebar.button("🔄 Segarkan Data Sekarang"):
    st.cache_data.clear()
    st.rerun()

# ==============================================================================
# 3. FUNGSI PENGAMBILAN DATA REAL-TIME (YFINANCE)
# ==============================================================================
@st.cache_data(ttl=120)  # Menyimpan cache selama 2 menit agar performa cepat & menghindari pembatasan Yahoo
def get_market_data():
    data_list = []
    for name, ticker in market_tickers.items():
        try:
            tk = yf.Ticker(ticker)
            # Mengambil data historis 5 hari terakhir untuk mengantisipasi libur akhir pekan
            hist = tk.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                price_change = current_price - prev_price
                pct_change = (price_change / prev_price) * 100
            else:
                current_price = 0.0
                pct_change = 0.0
                
            data_list.append({
                "Pasar / Negara": name,
                "Ticker": ticker,
                "Harga Terakhir": current_price,
                "Perubahan (%)": pct_change
            })
        except Exception as e:
            data_list.append({
                "Pasar / Negara": name, 
                "Ticker": ticker, 
                "Harga Terakhir": 0.0, 
                "Perubahan (%)": 0.0
            })
            
    return pd.DataFrame(data_list)

# Memuat data untuk papan informasi bursa
with st.spinner("Mengambil data pasar terbaru dari satelit Yahoo Finance..."):
    df_market = get_market_data()

# ==============================================================================
# 4. TAMPILAN PAPAN INFORMASI HARGA (TICKER BOARD)
# ==============================================================================
st.subheader("📊 Live Market Ticker Board")

# Membuat grid responsif (4 kolom di layar lebar, otomatis menyesuaikan di HP)
cols = st.columns(4)

for index, row in df_market.iterrows():
    col_idx = index % 4
    with cols[col_idx]:
        price_val = row["Harga Terakhir"]
        pct_val = row["Perubahan (%)"]
        
        # Format teks penanda naik (+) atau turun (-)
        sign = "+" if pct_val >= 0 else ""
        
        if price_val == 0.0:
            value_display = "Delay/Offline"
            delta_display = "0.0%"
        else:
            value_display = f"{price_val:,.2f}"
            delta_display = f"{sign}{pct_val:.2f}%"
            
        st.metric(
            label=row["Pasar / Negara"], 
            value=value_display, 
            delta=delta_display
        )

st.markdown("---")

# ==============================================================================
# 5. KOMPARASI GRAFIK INTERAKTIF (PERTUMBUHAN NORMALISASI %)
# ==============================================================================
st.subheader("📉 Grafik Komparasi & Analisis Pergerakan")

# Dropdown untuk memilih bursa pembanding (selain Indonesia)
comp_markets = [m for m in market_tickers.keys() if m != "Indonesia (IHSG)"]
selected_market = st.selectbox("Pilih Pasar Global untuk dibandingkan dengan IHSG:", comp_markets)

@st.cache_data(ttl=120)
def get_chart_data(ticker_ihsg, ticker_target, p, i):
    try:
        # Mengunduh data historis kedua bursa secara bersamaan
        df_ihsg = yf.download(ticker_ihsg, period=p, interval=i)['Close']
        df_target = yf.download(ticker_target, period=p, interval=i)['Close']
        
        # Bersihkan data dari nilai kosong (NaN)
        df_ihsg = df_ihsg.dropna()
        df_target = df_target.dropna()
        
        if not df_ihsg.empty and not df_target.empty:
            # Normalisasi performa ke 0% pada awal titik waktu bursa dimulai
            ihsg_norm = (df_ihsg / df_ihsg.iloc[0] - 1) * 100
            target_norm = (df_target / df_target.iloc[0] - 1) * 100
            
            # Satukan data ke dalam satu DataFrame berdasarkan indeks waktu bursa
            df_combined = pd.DataFrame({
                "IHSG": ihsg_norm,
                "Pembanding": target_norm
            })
            return df_combined.dropna()
    except Exception as e:
        pass
    return None

df_chart = get_chart_data(
    market_tickers["Indonesia (IHSG)"], 
    market_tickers[selected_market], 
    selected_period, 
    selected_interval
)

if df_chart is not None and not df_chart.empty:
    fig = go.Figure()
    
    # Garis Pergerakan IHSG
    fig.add_trace(go.Scatter(
        x=df_chart.index, 
        y=df_chart['IHSG'], 
        mode='lines', 
        name='IHSG (Indonesia)', 
        line=dict(color='#3b82f6', width=2.5)
    ))
    
    # Garis Pergerakan Bursa Pembanding
    fig.add_trace(go.Scatter(
        x=df_chart.index, 
        y=df_chart['Pembanding'], 
        mode='lines', 
        name=f'{selected_market}', 
        line=dict(color='#f97316', width=2)
    ))
    
    fig.update_layout(
        title=f"Performa IHSG vs {selected_market} ({period_choice})",
        xaxis_title="Garis Waktu",
        yaxis_title="Pertumbuhan / Penurunan (%)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Data grafik komparasi sementara tidak tersedia untuk periode ini atau sedang mengalami hambatan jaringan.")

# ==============================================================================
# 6. RINGKASAN RAMALAN OTOMATIS (LOGIKA ARITMATIKA BURSA)
# ==============================================================================
st.subheader("🤖 Kesimpulan Filter & Forecast")

try:
    sp500_pct = df_market[df_market["Pasar / Negara"] == "Amerika Serikat (S&P 500)"]["Perubahan (%)"].values[0]
    nikkei_pct = df_market[df_market["Pasar / Negara"] == "Jepang (Nikkei 225)"]["Perubahan (%)"].values[0]
except IndexError:
    sp500_pct = 0.0
    nikkei_pct = 0.0

# Indikator pembobotan sentimen gabungan (AS 60%, Regional Asia 40%)
composite_sentiment = (sp500_pct * 0.6) + (nikkei_pct * 0.4)

st.markdown("### **Panduan Arah Pembukaan IHSG Hari Ini:**")

if composite_sentiment > 0.4:
    st.success(
        f"🟢 **SENTIMEN: BIAS BULLISH (POTENSI MENGIKUTI KENAIKAN GLOBAL).** \n\n"
        f"Indeks S&P 500 AS ({sp500_pct:+.2f}%) dan bursa utama Asia Pasifik Nikkei ({nikkei_pct:+.2f}%) "
        f"menunjukkan penguatan yang solid. Hal ini memberikan dorongan modal asing masuk (foreign inflow) "
        f"yang positif bagi bursa Indonesia saat jam pembukaan pagi hari."
    )
elif composite_sentiment < -0.4:
    st.error(
        f"🔴 **SENTIMEN: BIAS BEARISH (WASPADA SENTIMEN TEKANAN JUAL).** \n\n"
        f"Terjadi koreksi atau pelemahan signifikan pada S&P 500 ({sp500_pct:+.2f}%) dan Nikkei ({nikkei_pct:+.2f}%). "
        f"Waspadai adanya potensi aksi lepas portofolio (panic selling) jangka pendek di pasar modal dalam negeri saat bel pembukaan berbunyi."
    )
else:
    st.warning(
        f"🟡 **SENTIMEN: KONSOLIDASI / FLAT.** \n\n"
        f"Pergerakan indeks S&P 500 AS ({sp500_pct:+.2f}%) dan bursa Asia cenderung bergerak mendatar. "
        f"Arah laju IHSG hari ini kemungkinan besar akan bergerak *sideways* dan akan lebih didominasi oleh "
        f"kabar laporan keuangan korporasi domestik atau keputusan suku bunga bank sentral dalam negeri."
    )
