// Navegação, cabeçalho e utilitários partilhados por todas as páginas.
const $ = s => document.querySelector(s);
(function(){
  const raiz = document.body.dataset.root, pg = document.body.dataset.page;
  const itens = [["index","Dashboard","index.html"],["monitorizacao","Monitorização","pages/monitorizacao.html"],
    ["comparacao","Comparação","pages/comparacao.html"],["relatorios","Relatórios","pages/relatorios.html"],["sobre","Sobre","pages/sobre.html"]];
  $("#nav").innerHTML = '<div class="logo">TERRA<span>WATCH</span> ANGOLA</div>' +
    itens.map(([id,t,h])=>`<a href="${raiz+h}" class="${id===pg?"on":""}">${t}</a>`).join("");
  $("#topo").innerHTML = `<h1>${document.body.dataset.titulo}</h1><span class="tag demo">MODO DEMO · sem backend ligado</span>`;
  fetch(API_BASE+"/saude").then(r=>r.json()).then(j=>{
    const t=$(".topo .tag"); t.className = j.versao ? "tag ok" : "tag demo";
    t.textContent = j.versao ? "BACKEND LIGADO · v"+j.versao : "BACKEND LIGADO · VERSÃO ANTIGA (actualize a pasta backend)";
  }).catch(()=>{});
})();
