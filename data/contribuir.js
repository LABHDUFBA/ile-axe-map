(function () {
  'use strict';
  var EMAIL = 'ileaxemap@gmail.com';
  // Preenchido quando houver um serviço de formulário (Formspree ou equivalente).
  // Vazio = envio por e-mail, com o corpo montado aqui.
  var ENDPOINT = (document.body && document.body.getAttribute('data-endpoint')) || '';

  var form = document.getElementById('form');
  if (!form) return;

  var tipoCasa = document.querySelectorAll('input[name="tipo_casa"]');
  var blocoNoMapa = document.getElementById('bloco-no-mapa');
  var blocoForaMapa = document.getElementById('bloco-fora-mapa');
  var selRegistro = document.getElementById('registro');
  var saida = document.getElementById('resultado');
  var btn = document.getElementById('enviar');
  var registros = [];

  // ---- lista de registros, lida do próprio GeoJSON do mapa -------------------
  fetch('data/v5/terreiros_nacional_v5.geojson')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (g) {
      if (!g || !g.features) return;
      registros = g.features.map(function (f) {
        var p = f.properties || {};
        return {
          id: p.entity_id || '',
          nome: p.nome || 'Terreiro sem nome',
          local: [p.municipio, p.uf].filter(Boolean).join('/')
        };
      }).filter(function (r) { return r.id; })
        .sort(function (a, b) { return a.nome.localeCompare(b.nome, 'pt-BR'); });

      registros.forEach(function (r) {
        var o = document.createElement('option');
        o.value = r.id;
        o.textContent = r.nome + (r.local ? ' — ' + r.local : '');
        selRegistro.appendChild(o);
      });
      // A lista chega depois do parse da URL; sem isto, o <select> não aceita um valor que
      // ainda não existe e a pré-seleção do link da ficha se perde.
      if (preIdPendente) selRegistro.value = preIdPendente;
    })
    .catch(function () { /* sem a lista, o campo de texto continua valendo */ });

  // ---- estado inicial a partir da URL --------------------------------------
  var qs = new URLSearchParams(location.search);
  var preId = qs.get('registro') || qs.get('id');
  var preIdPendente = preId;
  if (preId) {
    marcarTipo('no_mapa');
    selRegistro.value = preId;
    var manual = document.getElementById('registro_manual');
    if (manual) manual.value = preId;
    var acao = qs.get('acao');
    if (acao) {
      var alvo = document.querySelector('input[name="acao"][value="' + acao + '"]');
      if (alvo) alvo.checked = true;
    }
  }

  function marcarTipo(v) {
    Array.prototype.forEach.call(tipoCasa, function (r) { r.checked = (r.value === v); });
    atualizar();
  }

  function tipo() {
    var on = document.querySelector('input[name="tipo_casa"]:checked');
    return on ? on.value : '';
  }

  function atualizar() {
    var t = tipo();
    if (blocoNoMapa) blocoNoMapa.hidden = (t !== 'no_mapa');
    if (blocoForaMapa) blocoForaMapa.hidden = (t !== 'fora_mapa');
  }
  Array.prototype.forEach.call(tipoCasa, function (r) { r.addEventListener('change', atualizar); });
  atualizar();

  // ---- leitura dos campos --------------------------------------------------
  function v(id) { var el = document.getElementById(id); return el ? el.value.trim() : ''; }
  function radio(nome) {
    var el = document.querySelector('input[name="' + nome + '"]:checked');
    return el ? el.value : '';
  }
  function checks(nome) {
    return Array.prototype.map.call(
      document.querySelectorAll('input[name="' + nome + '"]:checked'),
      function (el) { return el.value; });
  }

  function rotuloRegistro() {
    var id = selRegistro.value;
    var nomeManual = v('registro_manual');
    if (!id) return nomeManual || '(não informado)';
    var r = registros.filter(function (x) { return x.id === id; })[0];
    return (r ? r.nome : (nomeManual || id)) + ' [' + id + (r && r.local ? ' — ' + r.local : '') + ']';
  }

  function montar() {
    var t = tipo();
    var L = [];
    L.push('ILÊ AXÉ MAP — CONTRIBUIÇÃO');
    L.push('Tipo: ' + (t === 'no_mapa' ? 'casa que já está no mapa' : 'casa que ainda não está no mapa'));
    L.push('');
    L.push('== REGISTRO ==');
    if (t === 'no_mapa') {
      L.push('Registro: ' + rotuloRegistro());
      L.push('Ação pedida: ' + (radio('acao') || '(não informada)'));
    } else {
      L.push('Nome da casa: ' + (v('nome_casa') || '(não informado)'));
    }
    L.push('');
    L.push('== QUEM RESPONDE (NÃO PUBLICADO) ==');
    L.push('Nome: ' + (v('nome_pessoa') || '(não informado)'));
    L.push('Relação: ' + (radio('relacao') || '(não informada)'));
    L.push('Contato: ' + (v('contato') || '(não informado)'));
    L.push('');
    L.push('== TRADIÇÃO ==');
    L.push('Tradição: ' + (checks('tradicao').join(', ') || '(não informada)'));
    L.push('Nação: ' + (v('nacao') || '(não informada)'));
    L.push('Raiz / família: ' + (v('raiz') || '(não informada)'));
    L.push('Linha: ' + (v('linha') || '(não informada)'));
    L.push('Orixá / entidade regente: ' + (v('regente') || '(não informado)'));
    L.push('Ano de fundação: ' + (v('fundacao') || '(não informado)'));
    L.push('');
    L.push('== LOCALIZAÇÃO ==');
    L.push('Município: ' + (v('municipio') || '(não informado)'));
    L.push('UF: ' + (v('uf') || '(não informada)'));
    L.push('Endereço: ' + (v('endereco') || '(não informado)'));
    L.push('Ponto de referência: ' + (v('referencia') || '(não informado)'));
    L.push('Link do Google Maps: ' + (v('maps') || '(não informado)'));
    L.push('');
    L.push('== REDES ==');
    L.push('Perfil: ' + (v('social') || '(não informado)'));
    L.push('');
    L.push('== MENSAGEM ==');
    L.push(v('mensagem') || '(não informado)');
    L.push('');
    L.push('== FOTO ==');
    L.push('Foto da fachada: ' + (radio('foto') || '(não informado)'));
    L.push('');
    L.push('== AUTORIZAÇÃO ==');
    L.push('Uso no mapa: ' + (radio('autorizo') || '(não respondido)'));
    L.push('Representa a casa: ' + (radio('represento') || '(não respondido)'));
    L.push('');
    L.push('---');
    L.push('Enviado pelo formulário em ' + new Date().toLocaleString('pt-BR'));
    return L.join('\r\n');
  }

  function assunto() {
    if (tipo() === 'fora_mapa') {
      return 'Ilê Axé Map — inclusão de casa — ' + (v('nome_casa') || 'sem nome');
    }
    var acao = radio('acao') || 'contribuição';
    return 'Ilê Axé Map — ' + acao + ' de ficha — ' + rotuloRegistro().split(' [')[0];
  }

  // ---- envio ---------------------------------------------------------------
  window.__ileAxeForm = 'iniciado';
  form.addEventListener('submit', function (ev) {
    window.__ileAxeSubmit = 'disparou';
    ev.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    var corpo = montar();

    if (!ENDPOINT) {
      // Dispara o cliente de e-mail num iframe: navegar a própria página para mailto: a
      // deixaria em branco em vários navegadores, escondendo a instrução de enviar.
      var link = 'mailto:' + EMAIL +
        '?subject=' + encodeURIComponent(assunto()) +
        '&body=' + encodeURIComponent(corpo);
      var frame = document.createElement('iframe');
      frame.style.display = 'none';
      frame.setAttribute('aria-hidden', 'true');
      document.body.appendChild(frame);
      frame.src = link;
      setTimeout(function () { frame.remove(); }, 4000);
      mostrarOk('mailto', corpo);
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Enviando…';
    var dados = new FormData(form);
    dados.append('_subject', assunto());
    dados.append('conteudo', corpo);
    fetch(ENDPOINT, { method: 'POST', body: dados, headers: { Accept: 'application/json' } })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); })
      .then(function () {
        form.reset(); atualizar();
        btn.disabled = false; btn.textContent = 'Enviar contribuição';
        mostrarOk('enviado', corpo);
      })
      .catch(function () {
        btn.disabled = false; btn.textContent = 'Enviar contribuição';
        mostrarOk('falhou', corpo);
      });
  });

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function mostrarOk(modo, corpo) {
    form.hidden = true;
    saida.hidden = false;
    var html = '';
    if (modo === 'enviado') {
      html = '<div class="ok"><h2>Contribuição enviada</h2>' +
        '<p>Recebemos sua mensagem. A equipe confere os dados e publica em até 30 dias. ' +
        'Pedidos de retirada saem em até 7 dias.</p>' +
        '<p>Este é o resumo do que você enviou — guarde se precisar falar conosco depois.</p>' +
        '<label for="resumo" style="display:block;margin:0 0 6px;font-size:12.5px;font-weight:600;color:var(--text)">Resumo do que foi enviado</label>' +
        '<textarea id="resumo" readonly style="min-height:280px">' + esc(corpo) + '</textarea></div>';
    } else if (modo === 'mailto') {
      html = '<div class="ok"><h2>Quase pronto — só falta enviar</h2>' +
        '<p>Abrimos seu aplicativo de e-mail com a mensagem preenchida. <strong>É preciso clicar em enviar lá.</strong> ' +
        'Se nada abriu, copie o texto abaixo e envie para <a href="mailto:' + EMAIL + '">' + EMAIL + '</a>.</p>' +
        '<p><button type="button" class="btn-ghost" id="copiar">Copiar a mensagem</button></p>' +
        '<label for="resumo" style="display:block;margin:0 0 6px;font-size:12.5px;font-weight:600;color:var(--text)">Prévia da mensagem</label>' +
        '<textarea id="resumo" readonly style="min-height:280px">' + esc(corpo) + '</textarea></div>';
    } else {
      html = '<div class="ok"><h2>Não foi possível enviar</h2>' +
        '<p>Houve uma falha de conexão. Copie o texto abaixo e envie para ' +
        '<a href="mailto:' + EMAIL + '">' + EMAIL + '</a>.</p>' +
        '<textarea id="resumo" readonly>' + esc(corpo) + '</textarea></div>';
    }
    saida.innerHTML = html;
    var copiar = document.getElementById('copiar');
    if (copiar) {
      copiar.addEventListener('click', function () {
        var ta = document.getElementById('resumo');
        ta.select();
        if (navigator.clipboard) {
          navigator.clipboard.writeText(ta.value).then(function () { copiar.textContent = 'Copiado'; });
        }
      });
    }
    saida.scrollIntoView({ block: 'start' });
  }
})();
