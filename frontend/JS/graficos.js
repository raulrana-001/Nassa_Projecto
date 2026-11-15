// Chart.js: gráficos reutilizáveis.
const Graficos = {
  _c:{},
  _base(tipo,id,labels,dados,rotulo,cor){
    if(this._c[id]) this._c[id].destroy();
    this._c[id] = new Chart(document.getElementById(id),{type:tipo,
      data:{labels,datasets:[{label:rotulo,data:dados,borderColor:cor,backgroundColor:cor+"99",tension:.3}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:"#F8FAFC"}}},
        scales:{x:{ticks:{color:"#94A3B8"},grid:{color:"#263241"}},y:{ticks:{color:"#94A3B8"},grid:{color:"#263241"}}}}});
  },
  linha(id,l,d,r){ this._base("line",id,l,d,r,"#2563EB"); },
  barras(id,l,d,r){ this._base("bar",id,l,d,r,"#22C55E"); }
};
