// O site funciona sem este arquivo. Ele só avisa que o LLM está trabalhando,
// porque a resposta pode levar até um minuto, e trava os botões para a mesma
// avaliação não ir duas vezes. Os botões travam depois do envio: travados
// antes, o exemplo clicado não iria junto com o formulário.
(function () {
  "use strict";
  var dica = document.getElementById("dica");
  document.querySelectorAll("form[data-classificar]").forEach(function (form) {
    form.addEventListener("submit", function () {
      if (dica) dica.textContent = "Classificando... o LLM pode levar até 1 minuto.";
      setTimeout(function () {
        document.querySelectorAll("form[data-classificar] button").forEach(function (botao) {
          botao.disabled = true;
        });
      }, 0);
    });
  });
})();
