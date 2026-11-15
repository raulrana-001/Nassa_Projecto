// Comunicação com o backend FastAPI. Sem backend, usa dados DEMO (identificados na interface).
const API_BASE = "http://localhost:8000/api";
const REGIOES_DEMO = [
  {id:1,nome:"Cuando Cubango",lat:-15.9,lng:19.8,zoom:7},{id:2,nome:"Moxico",lat:-12.5,lng:20.5,zoom:7},
  {id:3,nome:"Huíla",lat:-14.9,lng:14.6,zoom:8},{id:4,nome:"Benguela",lat:-12.6,lng:13.9,zoom:8},{id:5,nome:"Luanda",lat:-8.9,lng:13.3,zoom:9}];
const MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago"];
let ANALISES = (()=>{try{return JSON.parse(localStorage.getItem("tw_analises"))||[]}catch(e){return[]}})();
const guardar = () => {try{localStorage.setItem("tw_analises",JSON.stringify(ANALISES))}catch(e){}};
async function pedir(caminho, op={}) {
  const r = await fetch(API_BASE+caminho, {headers:{"Content-Type":"application/json"}, ...op});
  if(!r.ok){ let d=""; try{ d=(await r.json()).detail||"" }catch(e){} throw new Error(typeof d==="string"&&d?d:"HTTP "+r.status); }
  return r.json();
}
function resultadoDemo(a) {
  const seed = [...(a.regiao+a.fenomeno+(a.dataInicial||"")+(a.dataFinal||""))].reduce((s,c)=>s+c.charCodeAt(0),0);
  const serie = MESES.map((m,i)=>({m, v:+(((seed*(i+3))%90)/20-2.2).toFixed(1)}));
  return {estado:"concluida", indicador:+(serie[7].v-serie[0].v).toFixed(1), area_km2:200+seed%900, confianca:"Baixa", serie,
    fenomeno_nome:a.fenomeno==="vegetacao"?"vegetação":"zonas húmidas", demo:true};
}
const API = {
  async regioes(){ try{return await pedir("/regioes")}catch(e){if(!(e instanceof TypeError))throw e;return REGIOES_DEMO} },
  async observacoes(f){
    try{return await pedir("/observacoes?"+new URLSearchParams(f))}catch(e){
      if(!(e instanceof TypeError))throw e;
      return ["2026-03-12","2026-06-04","2026-09-18"].map(d=>({produto:"Produto SAR NISAR (exemplo)",data:d,banda:f.banda||"L",qualidade:"não validada",demo:true}));} },
  async criarAnalise(d){
    try{return await pedir("/analises",{method:"POST",body:JSON.stringify(d)})}catch(e){
      if(!(e instanceof TypeError))throw e;
      const a={id:Date.now(),...d,estado:"em_processamento",criada:Date.now(),demo:true}; ANALISES.unshift(a); guardar(); return a;} },
  async analise(id){
    try{return await pedir("/analises/"+id)}catch(e){
      if(!(e instanceof TypeError))throw e;
      const a=ANALISES.find(x=>x.id==id);
      if(a && a.estado!=="concluida" && Date.now()-a.criada>2500){Object.assign(a,resultadoDemo(a)); guardar();}
      return a;} },
  async preparar(d){ return pedir("/processamento/preparar",{method:"POST",body:JSON.stringify(d)}); },
  async locais(){ return pedir("/processamento/dados-locais"); },
  async vista(q){ return pedir("/processamento/vista?"+new URLSearchParams(q)); },
  async listar(){ try{return await pedir("/analises")}catch(e){ if(!(e instanceof TypeError))throw e; return ANALISES; } }
};
