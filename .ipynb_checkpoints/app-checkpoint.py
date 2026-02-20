import simpy
import random
import pandas as pd
import streamlit as st
import plotly.express as px

# ==========================
# PARAMETER
# ==========================

st.sidebar.header("⚙ Parameter Simulasi")

jumlah_meja = st.sidebar.number_input("Jumlah Meja", 1, 200, 60)
mahasiswa_per_meja = st.sidebar.number_input("Mahasiswa per Meja", 1, 10, 3)

petugas_lauk = st.sidebar.number_input("Petugas Lauk", 1, 7, 3)
petugas_angkut = st.sidebar.number_input("Petugas Angkut", 1, 7, 2)
petugas_nasi = st.sidebar.number_input("Petugas Nasi", 1, 7, 2)

total_ompreng = jumlah_meja * mahasiswa_per_meja

# Distribusi waktu (dalam menit)
min_lauk = 0.5
max_lauk = 1.0

min_angkut = 0.33
max_angkut = 1.0

min_nasi = 0.5
max_nasi = 1.0

# ==========================
# MODEL DES
# ==========================

class SistemPiket:
    def __init__(self, env):
        self.env = env

        self.lauk = simpy.Resource(env, capacity=petugas_lauk)
        self.angkut = simpy.Resource(env, capacity=petugas_angkut)
        self.nasi = simpy.Resource(env, capacity=petugas_nasi)

        self.store_lauk = simpy.Store(env)   # selesai lauk
        self.store_meja = simpy.Store(env)   # sudah di meja

        self.log = []

        self.total_lauk_time = 0
        self.total_angkut_time = 0
        self.total_nasi_time = 0

    # Tahap 1: Lauk
    def proses_lauk(self, id_ompreng):
        with self.lauk.request() as req:
            yield req
            waktu = random.uniform(min_lauk, max_lauk)
            self.total_lauk_time += waktu
            yield self.env.timeout(waktu)
        yield self.store_lauk.put((id_ompreng, self.env.now))

    # Tahap 2: Angkut (BATCH 4-7)
    def proses_angkut(self):
        while True:
            if len(self.store_lauk.items) == 0:
                yield self.env.timeout(0.1)
                continue

            batch_size = random.randint(4,7)
            batch = []

            for _ in range(min(batch_size, len(self.store_lauk.items))):
                item = yield self.store_lauk.get()
                batch.append(item)

            with self.angkut.request() as req:
                yield req
                waktu = random.uniform(min_angkut, max_angkut)
                self.total_angkut_time += waktu
                yield self.env.timeout(waktu)

            for item in batch:
                yield self.store_meja.put(item)

    # Tahap 3: Nasi
    def proses_nasi(self):
        while True:
            if len(self.store_meja.items) == 0:
                yield self.env.timeout(0.1)
                continue

            id_ompreng, waktu_mulai = yield self.store_meja.get()

            with self.nasi.request() as req:
                yield req
                waktu = random.uniform(min_nasi, max_nasi)
                self.total_nasi_time += waktu
                yield self.env.timeout(waktu)

            selesai = self.env.now

            self.log.append({
                "Ompreng": id_ompreng,
                "Mulai": waktu_mulai,
                "Selesai": selesai,
                "Durasi Total": selesai - waktu_mulai
            })


def run_simulation():
    env = simpy.Environment()
    sistem = SistemPiket(env)

    # generate ompreng
    for i in range(total_ompreng):
        env.process(sistem.proses_lauk(i))

    # proses angkut & nasi berjalan terus
    env.process(sistem.proses_angkut())
    env.process(sistem.proses_nasi())

    env.run(until=1000)
    return sistem


# ==========================
# STREAMLIT UI
# ==========================

st.title("🍱 Simulasi Sistem Piket IT Del")
st.write("Discrete Event Simulation - Studi Kasus 2.1 (Batch Angkut 4-7 Ompreng)")

if st.button("▶ Jalankan Simulasi"):

    sistem = run_simulation()

    df = pd.DataFrame(sistem.log)

    rata_rata = df["Durasi Total"].mean()
    total_waktu = df["Selesai"].max()

    jam_selesai = 7 + int(total_waktu // 60)
    menit_selesai = int(total_waktu % 60)

    total_petugas = petugas_lauk + petugas_angkut + petugas_nasi

    # Utilisasi
    utilisasi_lauk = sistem.total_lauk_time / (petugas_lauk * total_waktu)
    utilisasi_angkut = sistem.total_angkut_time / (petugas_angkut * total_waktu)
    utilisasi_nasi = sistem.total_nasi_time / (petugas_nasi * total_waktu)

    st.success(f"Simulasi selesai! {total_ompreng} ompreng diproses.")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Ompreng", total_ompreng)
    col2.metric("Rata-rata Durasi", f"{rata_rata:.2f} menit")
    col3.metric("Waktu Selesai", f"{jam_selesai:02d}:{menit_selesai:02d}")
    col4.metric("Total Petugas", total_petugas)

    st.subheader("📊 Utilisasi Petugas")

    st.write(f"Lauk: {utilisasi_lauk*100:.2f}%")
    st.write(f"Angkut: {utilisasi_angkut*100:.2f}%")
    st.write(f"Nasi: {utilisasi_nasi*100:.2f}%")

    st.subheader("📈 Visualisasi")

    fig1 = px.histogram(df, x="Durasi Total",
                        title="Distribusi Durasi Total Ompreng")
    st.plotly_chart(fig1)

    fig2 = px.scatter(df,
                      x="Selesai",
                      y="Ompreng",
                      title="Timeline Penyelesaian Ompreng")
    st.plotly_chart(fig2)

    st.dataframe(df)
