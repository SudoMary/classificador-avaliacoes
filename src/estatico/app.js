// O site funciona sem este arquivo. Ele faz duas coisas:
// 1. Enquanto o LLM pensa (até um minuto), avisa e trava os botões, para a
//    mesma avaliação não ir duas vezes. Os botões travam depois do envio:
//    travados antes, o exemplo clicado não iria junto com o formulário.
// 2. Mostra a dica dos gráficos, no passar do mouse e no foco do teclado. Os
//    mesmos números estão nas tabelas: a dica ajuda, mas nunca é o único jeito.
(function () {
  "use strict";

  var aviso = document.getElementById("dica");
  document.querySelectorAll("form[data-classificar]").forEach(function (form) {
    form.addEventListener("submit", function () {
      if (aviso) aviso.textContent = "Classificando... o LLM pode levar até 1 minuto.";
      setTimeout(function () {
        document.querySelectorAll("form[data-classificar] button").forEach(function (botao) {
          botao.disabled = true;
        });
      }, 0);
    });
  });

  var marcas = document.querySelectorAll("[data-dica]");
  if (!marcas.length) return;
  var dica = document.createElement("div");
  dica.className = "dica-grafico";
  dica.setAttribute("role", "tooltip");
  dica.hidden = true;
  document.body.appendChild(dica);

  function mostrar(marca) {
    // textContent, e não innerHTML: o texto vem dos dados.
    dica.textContent = marca.getAttribute("data-dica");
    dica.hidden = false;
    var caixa = marca.getBoundingClientRect();
    var largura = dica.offsetWidth;
    var esquerda = Math.min(
      Math.max(8, caixa.left + caixa.width / 2 - largura / 2),
      document.documentElement.clientWidth - largura - 8
    );
    dica.style.left = esquerda + window.scrollX + "px";
    dica.style.top = caixa.top + window.scrollY - dica.offsetHeight - 8 + "px";
  }

  function esconder() {
    dica.hidden = true;
  }

  marcas.forEach(function (marca) {
    marca.addEventListener("pointerenter", function () { mostrar(marca); });
    marca.addEventListener("pointerleave", esconder);
    marca.addEventListener("focus", function () { mostrar(marca); });
    marca.addEventListener("blur", esconder);
  });
})();
