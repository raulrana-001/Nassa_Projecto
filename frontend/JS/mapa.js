// Leaflet: mapa base escuro, marcadores de regiões e sobreposição de resultados.
const Mapa = {
  criar(id){
    const m = L.map(id).setView([-12.3,17.5],5);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",{maxZoom:12,attribution:"© OpenStreetMap, © CARTO"}).addTo(m);
    return m;
  },
  marcadores(m, regs, aoClicar){
    regs.forEach(r=>L.circleMarker([r.lat,r.lng],{radius:8,color:"#2563EB",fillColor:"#2563EB",fillOpacity:.5})
      .addTo(m).bindTooltip(r.nome).on("click",()=>aoClicar&&aoClicar(r.nome)));
  },
  camada(m, url, limites){
    if(m._img) m.removeLayer(m._img);
    m._img = L.imageOverlay(url, limites, {opacity:.9}).addTo(m); m.fitBounds(limites);
  },
  sobreposicao(m, r, valor){
    if(m._res) m.removeLayer(m._res);
    const cor = valor>=0 ? "#22C55E" : "#F59E0B";
    m._res = L.circle([r.lat,r.lng],{radius:60000,color:cor,fillColor:cor,fillOpacity:.25}).addTo(m).bindPopup(`${r.nome}: ${valor} dB (DEMO)`);
    m.setView([r.lat,r.lng],r.zoom);
  }
};
