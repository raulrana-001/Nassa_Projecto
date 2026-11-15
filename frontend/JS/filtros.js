// Página Monitorização: filtros, criação da tarefa e acompanhamento do estado.
(async()=>{
  const regs = await API.regioes(), sel = $("#regiao");
  sel.innerHTML = regs.map(r=>`<option>${r.nome}</option>`).join("");
  const mapa = Mapa.criar("mapa"); Mapa.marcadores(mapa, regs, n=>{sel.value=n; obs();});
  async function obs(){
    let o;
    try{ o = await API.observacoes({regiao:sel.value, banda:$("#banda").value}); }
    catch(e){ $("#obs").textContent = "Não foi possível consultar os produtos: "+e.message; return; }
    $("#obs").innerHTML = o.map(x=>`<div class="item"><b>${x.produto}</b><span>${x.data} · banda ${x.banda} · ${x.qualidade} ${x.demo?'<i class="tag demo">DEMO</i>':""}</span></div>`).join("") || "Sem produtos adequados para estes filtros.";
    const r = regs.find(x=>x.nome===sel.value); if(r) mapa.setView([r.lat,r.lng],r.zoom);
  }
  sel.onchange = $("#banda").onchange = obs; obs();
  function mostrar(a){
    const r = regs.find(x=>x.nome===a.regiao);
    $("#estado").innerHTML = `<div class="res"><div><small>Indicador</small><b class="${a.indicador>=0?"pos":""}">${a.indicador>0?"+":""}${a.indicador} dB</b></div><div><small>Área analisada</small><b>${a.area_km2} km²</b></div><div><small>Confiança</small><b>${a.confianca}</b></div>${a.area_alterada_km2!=null?`<div><small>Área alterada</small><b>${a.area_alterada_km2} km²</b></div>`:""}${(a.metricas||[]).map(m=>`<div><small>${m.rotulo}</small><b>${m.valor}</b></div>`).join("")}</div>
      <p class="nota">${a.metodo?a.metodo+" ":""}Indicador compatível com alterações em ${a.fenomeno_nome||a.fenomeno}; não prova a causa. ${a.demo?'<i class="tag demo">DEMO</i> Valores simulados. '+(a.mensagem||""):"Fonte: NISAR GCOV (banda L)."}</p>`;
    Graficos.linha("graf", a.serie.map(s=>s.m), a.serie.map(s=>s.v), "Retroespalhamento relativo (dB)");
    if(a.mapa_url) Mapa.camada(mapa, API_BASE.replace(/\/api$/,"")+a.mapa_url+"?t="+Date.now(), a.mapa_limites);
    else if(r) Mapa.sobreposicao(mapa, r, a.indicador);
  }
  $("#form").onsubmit = async e=>{
    e.preventDefault();
    const d = {regiao:sel.value, fenomeno:$("#fenomeno").value, dataInicial:$("#di").value, dataFinal:$("#df").value, banda:$("#banda").value};
    if(d.dataInicial>=d.dataFinal){ $("#estado").textContent="A data inicial tem de ser anterior à data final."; return; }
    try{
      let a = await API.criarAnalise(d);
      while(a && a.estado!=="concluida" && a.estado!=="erro"){
        $("#estado").innerHTML = `<span class="spin"></span> Tarefa #${a.id}: ${a.estado.replace("_"," ")}${a.mensagem?" — "+a.mensagem:""}…`;
        await new Promise(r=>setTimeout(r,800)); a = await API.analise(a.id);
      }
      if(!a||a.estado==="erro") throw new Error("a análise falhou");
      mostrar(a);
    }catch(err){ $("#estado").textContent = "Erro: "+err.message; }
  };
  // Dados SAR descarregados: mostrar a imagem de retroescalonamento (dB) no mapa
  async function locais(){
    const el = $("#locais");
    try{
      const d = await API.locais();
      el.innerHTML = d.produtos.map(p=>`<div class="item"><b>${p.nome}</b><span>${(p.inicio||"").slice(0,10)} · ${p.tamanho_mb} MB · órbita ${p.pilha?p.pilha.orbita:"?"}</span>
        <span>${["HH","HV","VV"].map(k=>`<button class="btn sec" type="button" data-nome="${p.nome}" data-pol="${k}">Ver ${k}</button>`).join(" ")}</span></div>`).join("")
        || 'Ainda não há produtos em data/raw. Descarregue com o botão acima, ou explore os produtos no <a href="https://search.asf.alaska.edu/" target="_blank" rel="noopener">ASF Vertex</a>.';
    }catch(e){ el.textContent = "Não foi possível listar os dados locais: "+e.message; }
  }
  $("#locais").onclick = async e=>{
    const b = e.target.closest("button[data-nome]"); if(!b) return;
    const r = $("#vistaRes"); r.textContent = "A preparar a imagem SAR… (pode demorar)";
    try{
      const v = await API.vista({nome:b.dataset.nome, regiao:sel.value, pol:b.dataset.pol});
      Mapa.camada(mapa, API_BASE.replace(/\/api$/,"")+v.url+"?t="+Date.now(), v.limites);
      r.textContent = `Retroescalonamento ${v.pol} em dB (preto = ${v.db_min} dB, branco = ${v.db_max} dB), ${v.resolucao_m} m. Região: ${sel.value}.`;
    }catch(err){ r.textContent = "Não foi possível: "+err.message; }
  };
  locais();
})();

// Botões do plano de dados: ligados já no arranque da página
async function preparar(desc){
  const r = $("#planoRes"); r.textContent = "A consultar o ASF… (pode demorar até 30 s)";
  try{
    const p = await API.preparar({regiao:$("#regiao").value, dataInicial:$("#di").value, dataFinal:$("#df").value, maxCenas:3, descarregar:desc});
    r.innerHTML = `Órbita ${p.pilha.orbita} (${p.pilha.direccao}), quadro ${p.pilha.quadro}: ${p.cenas.length} cenas, ${p.total_a_descarregar_mb} MB por descarregar${p.tamanho_desconhecido?" (tamanho de alguns ficheiros desconhecido)":""}`
      + (desc ? ` — descargas iniciadas: ${p.descargas.length?"#"+p.descargas.join(", #"):"nenhuma (já estavam locais)"}.` : "")
      + "<br>" + p.cenas.map(c=>`${(c.inicio||"").slice(0,10)} ${c.local?"✓ local":"por descarregar"}`).join(" · ");
  }catch(e){ r.textContent = "Não foi possível: "+e.message; }
}
$("#plano").onclick = ()=>preparar(false); $("#descarregar").onclick = ()=>preparar(true);
