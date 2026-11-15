# TerraWatch Angola

## Backend (FastAPI)
    cd backend
    python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000                   # documentação: http://localhost:8000/docs

Variáveis opcionais: `DATABASE_URL` (omissão: SQLite `terrawatch.db`; PostgreSQL: `postgresql+psycopg://user:pass@localhost/terrawatch`),
`NISAR_MODE` (omissão `demo`), `DEMO_DELAY` (segundos de atraso simulado), `CORS_ORIGINS` (origens extra, separadas por vírgula).

## Frontend
    cd frontend
    python -m http.server 5500                              # http://localhost:5500

Com o backend ligado, a etiqueta do topo passa a "BACKEND LIGADO". Os resultados continuam DEMO (simulados) até a integração NISAR e o processamento real serem implementados.

## Integração NISAR (ASF DAAC)
Pesquisar produtos NISAR (banda L) não exige conta. Modo por omissão `NISAR_MODE=auto`: usa o ASF e, se estiver inacessível, devolve exemplos marcados DEMO.

    $env:NISAR_MODE="asf"            # PowerShell: só dados reais (erro 502 se o ASF falhar)
    python scripts/testar_nisar.py   # teste ao vivo (precisa de internet)
    python -m pytest -q              # testes sem internet

Endpoints: `GET /api/nisar/estado`, `/api/nisar/produtos`, `/api/nisar/disponibilidade?regiao=Luanda&dataInicial=2026-06-17&dataFinal=2026-11-14`,
`POST /api/nisar/descargas` (precisa de `EARTHDATA_TOKEN`, gerado em https://urs.earthdata.nasa.gov/profile) e `GET /api/nisar/descargas/{id}`.
Os ficheiros HDF5 descarregados ficam em `data/raw`. Limite por ficheiro: `MAX_DOWNLOAD_MB` (omissão 2000).

## Processamento geográfico
`PROCESSAMENTO=auto` (omissão): se existirem em `data/raw` pelo menos 2 produtos GCOV da mesma geometria (órbita, direcção, quadro) a cobrir a região, a análise usa-os (resultado real, sem etiqueta DEMO); caso contrário devolve DEMO com explicação. `real` = só dados reais; `demo` = só simulado.

Fluxo: 1) `POST /api/processamento/preparar` (descarregar=false) mostra a pilha de produtos e o tamanho; 2) com `descarregar=true` (e EARTHDATA_TOKEN) descarrega os que faltam; 3) executar a análise em Monitorização.
Métodos: vegetação = diferença de HV (dB); zonas húmidas = máscara de água por limiar em HH/VV + subida de HH (vegetação inundada). Limiares em `VEG_LIMIAR_DB` (3), `WET_AGUA_DB` (-18), `WET_AUMENTO_DB` (3); resolução `RESOLUCAO_M` (100). `GET /api/processamento/dados-locais` lista o que está em data/raw.

## Ver imagens SAR
Em Monitorização, a secção "Dados SAR descarregados" lista os produtos GCOV de `data/raw`; "Ver HH/HV/VV" mostra no mapa o retroescalonamento (dB, escala de cinzentos) recortado à região escolhida. API: `GET /api/processamento/vista?nome=...&regiao=Luanda&pol=HV`.
Sem descarregar nada, pode explorar os produtos NISAR no ASF Vertex: https://search.asf.alaska.edu/
