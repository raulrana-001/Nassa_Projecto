(async()=>{
  const an = (await API.listar()).filter(a=>a.estado==="concluida");
  $("#tabela").innerHTML = an.length ? `<tr><th>ID</th><th>Região</th><th>Fenómeno</th><th>Período</th><th>Indicador</th><th>Confiança</th><th>Origem</th><th></th></tr>` +
    an.map(a=>`<tr><td>#${a.id}</td><td>${a.regiao}</td><td>${a.fenomeno_nome||a.fenomeno}</td><td>${a.dataInicial} → ${a.dataFinal}</td><td>${a.indicador} dB</td><td>${a.confianca}</td>
      <td>${a.demo?'<i class="tag demo">DEMO</i>':'<i class="tag ok">NISAR</i>'}</td><td><button class="btn sec" data-id="${a.id}">JSON</button></td></tr>`).join("")
    : "<tr><td>Ainda não existem análises concluídas. Execute uma em Monitorização.</td></tr>";
  document.querySelectorAll("button[data-id]").forEach(b=>b.onclick=()=>{
    const a = an.find(x=>x.id==b.dataset.id), l = document.createElement("a");
    l.href = URL.createObjectURL(new Blob([JSON.stringify(a,null,2)],{type:"application/json"}));
    l.download = `relatorio-${a.id}.json`; l.click();
  });
})();
