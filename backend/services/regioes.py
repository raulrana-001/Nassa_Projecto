# bbox = [oeste, sul, este, norte] em graus. São caixas APROXIMADAS para consultar o catálogo,
# não os limites administrativos oficiais. Ajustar se for preciso maior rigor.
ANGOLA_BBOX = [11.6, -18.1, 24.1, -4.3]
REGIOES = [
    {"id": 1, "nome": "Cuando Cubango", "lat": -15.9, "lng": 19.8, "zoom": 7, "bbox": [16.5, -18.0, 23.4, -14.0]},
    {"id": 2, "nome": "Moxico", "lat": -12.5, "lng": 20.5, "zoom": 7, "bbox": [18.8, -14.8, 23.8, -10.6]},
    {"id": 3, "nome": "Huíla", "lat": -14.9, "lng": 14.6, "zoom": 8, "bbox": [13.0, -16.3, 16.3, -13.5]},
    {"id": 4, "nome": "Benguela", "lat": -12.6, "lng": 13.9, "zoom": 8, "bbox": [12.4, -13.9, 14.9, -11.5]},
    {"id": 5, "nome": "Luanda", "lat": -8.9, "lng": 13.3, "zoom": 9, "bbox": [12.9, -9.6, 14.0, -8.6]},
]

def existe(nome: str) -> bool:
    return any(r["nome"] == nome for r in REGIOES)

def obter(nome: str) -> dict | None:
    return next((r for r in REGIOES if r["nome"] == nome), None)
