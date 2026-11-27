import math
import random
import uuid
import httpx

API_URL = "http://127.0.0.1:8000/ocorrencias"

PHOTO_URL = (
    "https://zwwnqppthazgaibvvrdn.supabase.co/storage/v1/object/public/"
    "UrbInclusiva/ff5d5e77-49b6-4832-829f-cb4acde7f805.webp"
)

CATEGORIAS = [
    "calcada_quebrada",
    "piso_tatil",
    "rampa_ausente",
    "rampa_inadequada",
    "degrau_elevado",
    "obstaculo_fixo",
    "bloqueio_temporario",
    "semaforo_sonoro",
    "boca_de_lobo",
    "obra_sem_rota",
    "outra_barreira",
]

# Centros aproximados em Cuiabá - MT
CENTROS = {
    "Yumit Hub": (-15.5823, -56.0772),
    "UFMT Cuiabá": (-15.6083, -56.0632),
}


def gerar_coordenada_proxima(lat_centro: float, lng_centro: float, raio_metros: float = 650.0) -> tuple[float, float]:
    """Gera uma coordenada aleatória uniformemente distribuída dentro de um raio em metros."""
    raio_graus = raio_metros / 111320.0
    u = random.random()
    v = random.random()
    w = raio_graus * math.sqrt(u)
    t = 2 * math.pi * v

    delta_lat = w * math.cos(t)
    delta_lng = (w * math.sin(t)) / math.cos(math.radians(lat_centro))

    return round(lat_centro + delta_lat, 6), round(lng_centro + delta_lng, 6)


def popular_ocorrencias():
    # 150 pinos para cada região = 300 pinos no total
    tarefas = [("Yumit Hub", CENTROS["Yumit Hub"])] * 150 + [
        ("UFMT Cuiabá", CENTROS["UFMT Cuiabá"])
    ] * 150
    random.shuffle(tarefas)

    sucessos = 0
    erros = 0
    device_id_atual = str(uuid.uuid4())

    with httpx.Client(timeout=15.0) as client:
        for i, (regiao, (lat_base, lng_base)) in enumerate(tarefas):
            # Troca o X-Device-Id a cada 3 requisições para não bater no rate limit (429)
            if i % 3 == 0:
                device_id_atual = str(uuid.uuid4())

            lat, lng = gerar_coordenada_proxima(lat_base, lng_base, raio_metros=650.0)
            payload = {
                "category": random.choice(CATEGORIAS),
                "latitude": lat,
                "longitude": lng,
                "photo_url": PHOTO_URL,
            }
            headers = {"X-Device-Id": device_id_atual}

            try:
                resp = client.post(API_URL, json=payload, headers=headers)
                if resp.status_code == 201:
                    sucessos += 1
                    print(f"[{i + 1:03d}/300] OK ({regiao}) -> {payload['category']} ({lat}, {lng})")
                else:
                    erros += 1
                    print(f"[{i + 1:03d}/300] ERRO {resp.status_code}: {resp.text}")
            except httpx.RequestError as exc:
                erros += 1
                print(f"[{i + 1:03d}/300] FALHA DE CONEXÃO: {exc}")

    print(f"\nFinalizado! Criados: {sucessos} | Falhas: {erros}")


if __name__ == "__main__":
    popular_ocorrencias()