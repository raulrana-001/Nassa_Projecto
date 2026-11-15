(async()=>{
  const regs = await API.regioes(), sel = $("#regiao");
  sel.innerHTML = regs.map(r=>`<option>${r.nome}</option>`).join("");
  const A = Mapa.criar("mapaA"), B = Mapa.criar("mapaB"); let sync=false;
  const espelho=(o,d)=>o.on("move",()=>{ if(sync) return; sync=true; d.setView(o.getCenter(),o.getZoom(),{animate:false}); sync=false; });
  espelho(A,B); espelho(B,A);
  $("#form").onsubmit = e=>{
    e.preventDefault();
    const r = regs.find(x=>x.nome===sel.value), da=$("#da").value, db=$("#db").value;
    if(da>=db){ $("#resumo").textContent="O período A tem de ser anterior ao período B."; return; }
    const ra = resultadoDemo({regiao:r.nome,fenomeno:"vegetacao",dataInicial:da}), rb = resultadoDemo({regiao:r.nome,fenomeno:"vegetacao",dataInicial:db});
    Mapa.sobreposicao(A,r,ra.serie[7].v); Mapa.sobreposicao(B,r,rb.serie[7].v);
    const dif = +(rb.serie[7].v-ra.serie[7].v).toFixed(1);
    $("#resumo").innerHTML = `Diferença B − A em ${r.nome}: <b>${dif>0?"+":""}${dif} dB</b> <i class="tag demo">DEMO</i>`;
    Graficos.barras("graf",["Período A","Período B","Diferença"],[ra.serie[7].v,rb.serie[7].v,dif],"dB (relativo)");
  };
})();
