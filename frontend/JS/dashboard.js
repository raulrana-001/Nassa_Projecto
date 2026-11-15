(async()=>{
  const regs = await API.regioes(), an = await API.listar(), ok = an.filter(a=>a.estado==="concluida");
  $("#kpis").innerHTML = [["Análises",an.length],["Concluídas",ok.length],["Regiões",regs.length],["Fenómenos (MVP)",2]]
    .map(([t,v])=>`<div class="kpi card"><small>${t}</small><b>${v}</b></div>`).join("");
  const ref = ok[0] || resultadoDemo({regiao:"Luanda",fenomeno:"vegetacao"});
  Graficos.linha("graf", ref.serie.map(s=>s.m), ref.serie.map(s=>s.v), "Retroespalhamento relativo (dB)");
  $("#recentes").innerHTML = an.slice(0,5).map(a=>`<div class="item"><b>${a.regiao} · #${a.id}</b><span>${a.fenomeno} · ${a.estado.replace("_"," ")}</span></div>`).join("")
    || '<div class="item"><span>Ainda sem análises. Execute uma em Monitorização.</span></div>';
  $("#regioes").innerHTML = regs.map(r=>`<a href="pages/monitorizacao.html">${r.nome}</a>`).join("");
})();
