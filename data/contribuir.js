(function () {
  'use strict';
  var EMAIL = 'ileaxemap@gmail.com';
  // Preenchido quando houver um serviço de formulário (Formspree ou equivalente).
  // Vazio = envio por e-mail, com o corpo montado aqui.
  var ENDPOINT = (document.body && document.body.getAttribute('data-endpoint')) || '';
  var V_INDICE = (document.body && document.body.getAttribute('data-indice')) || '';

  var form = document.getElementById('form');
  if (!form) return;

  var tipoCasa = document.querySelectorAll('input[name="tipo_casa"]');
  var blocoNoMapa = document.getElementById('bloco-no-mapa');
  var blocoForaMapa = document.getElementById('bloco-fora-mapa');
  var campoBusca = document.getElementById('registro_busca');
  var listaRegistros = document.getElementById('lista-registros');
  var statusRegistro = document.getElementById('registro-status');
  var idRegistro = document.getElementById('registro');
  var textoManual = document.getElementById('registro_manual');
  var saida = document.getElementById('resultado');
  var btn = document.getElementById('enviar');
  var registros = null;      // [{id, nome, mun, uf}] — carregado sob demanda
  var carregando = false;
  var resultados = [];
  var ativo = -1;
  var selecionado = null;
  var preId = null;

  // ---- busca de registro -----------------------------------------------------
  // O índice é compacto (data/v5/indice_busca.json, ~490 KB contra 5,8 MB do GeoJSON) e só é
  // baixado quando alguém começa a digitar: quem abre o formulário para corrigir o próprio
  // terreiro não deve pagar o download de um seletor com 8 mil opções.

  function normalizar(t) {
    var s = String(t || '');
    if (s.normalize) s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return s.toLowerCase();
  }

  function carregar() {
    if (registros || carregando) return;
    carregando = true;
    status('Carregando a lista de registros…');
    fetch('data/v5/indice_busca.json' + (V_INDICE ? '?v=' + V_INDICE : ''))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.e) return;
        var m = d.m || [];
        registros = d.e.map(function (e) {
          return {
            id: e[0], nome: e[1],
            mun: m[e[2]] || '', uf: e[3] || '',
            alt: e[4] || '',
            _nome: normalizar(e[1]),
            _alvo: normalizar([e[1], m[e[2]] || '', e[3] || '', e[4] || ''].join(' '))
          };
        });
        if (preId) {
          var achado = registros.filter(function (r) { return r.id === preId; })[0];
          if (achado) escolher(achado, true);
        }
        // Se a seleção já veio do link da ficha, o campo está resolvido: não reabrir a lista
        // nem trocar o status de "Selecionado" por uma contagem de resultados.
        if (!selecionado) { status(''); renderizar(); }
      })
      .catch(function () {
        status('A lista de registros não carregou. Escreva o nome da casa no campo acima — ele vai na contribuição.');
      })
      .then(function () { carregando = false; });
  }

  function status(texto, ok) {
    if (!statusRegistro) return;
    statusRegistro.textContent = texto || '';
    statusRegistro.className = 'combo__status' + (ok ? ' combo__status--ok' : '');
  }

  // Ranqueia: nome igual > nome começa > palavra do nome começa > contém no nome > só no
  // município/UF. Assim "salvador" acha as casas de Salvador e "casa de xango" acha o nome.
  function pontuar(r, termos) {
    var total = 0;
    for (var i = 0; i < termos.length; i++) {
      var t = termos[i];
      var p = r._nome.indexOf(t);
      if (p === 0 && r._nome.length === t.length) total += 0;
      else if (p === 0) total += 1;
      else if (p > 0 && r._nome.charAt(p - 1) === ' ') total += 2;
      else if (p > 0) total += 3;
      else if (r._alvo.indexOf(t) >= 0) total += 5;
      else return -1;   // o termo não aparece: fora
    }
    return total;
  }

  function buscar(termo) {
    if (!registros) return [];
    var termos = normalizar(termo).split(/\s+/).filter(Boolean);
    if (!termos.length) return [];
    var achados = [];
    for (var i = 0; i < registros.length; i++) {
      var p = pontuar(registros[i], termos);
      if (p >= 0) achados.push([p, registros[i]]);
    }
    achados.sort(function (a, b) {
      if (a[0] !== b[0]) return a[0] - b[0];
      return a[1].nome.localeCompare(b[1].nome, 'pt-BR');
    });
    return achados.slice(0, 40).map(function (x) { return x[1]; });
  }

  function marcar(texto, termos) {
    var out = '', baixo = normalizar(texto), i = 0;
    var posicoes = [];
    termos.forEach(function (t) {
      var de = 0, p;
      while ((p = baixo.indexOf(t, de)) >= 0) { posicoes.push([p, p + t.length]); de = p + t.length; }
    });
    if (!posicoes.length) return esc(texto);
    posicoes.sort(function (a, b) { return a[0] - b[0]; });
    var ate = 0;
    posicoes.forEach(function (par) {
      if (par[0] < ate) return;             // sobreposição: ignora
      out += esc(texto.slice(i, par[0])) + '<mark>' + esc(texto.slice(par[0], par[1])) + '</mark>';
      i = par[1]; ate = par[1];
    });
    return out + esc(texto.slice(i));
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function renderizar() {
    if (!listaRegistros || !campoBusca) return;
    if (selecionado && campoBusca.value.trim() === selecionado.nome) { fechar(); return; }
    var termo = campoBusca.value.trim();
    var termos = normalizar(termo).split(/\s+/).filter(Boolean);
    resultados = buscar(termo);
    ativo = -1;
    listaRegistros.innerHTML = '';

    if (!termo) { fechar(); status(registros ? '' : ''); return; }
    if (!registros) { fechar(); return; }

    if (!resultados.length) {
      fechar();
      status('Nenhum registro com “' + termo + '”. Deixe assim mesmo: o nome escrito vai na contribuição.');
      return;
    }

    resultados.forEach(function (r, i) {
      var li = document.createElement('li');
      li.className = 'combo__opt';
      li.id = 'opt-' + i;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      var local = [r.mun, r.uf].filter(Boolean).join('/');
      li.innerHTML = '<span class="combo__nome">' + marcar(r.nome, termos) + '</span>' +
        (local ? '<span class="combo__meta">' + esc(local) +
          (r.alt ? ' · antes: ' + esc(r.alt) : '') + '</span>' : '');
      li.addEventListener('mousedown', function (ev) { ev.preventDefault(); escolher(r, true); });
      listaRegistros.appendChild(li);
    });

    var rodape = document.createElement('li');
    rodape.className = 'combo__rodape';
    rodape.setAttribute('role', 'presentation');
    rodape.textContent = resultados.length === 40
      ? 'Mostrando os 40 mais prováveis — refine a busca'
      : resultados.length + (resultados.length === 1 ? ' registro encontrado' : ' registros encontrados');
    listaRegistros.appendChild(rodape);

    listaRegistros.hidden = false;
    campoBusca.setAttribute('aria-expanded', 'true');
    status(resultados.length + (resultados.length === 1 ? ' resultado' : ' resultados') +
      ' — use as setas e Enter para escolher.');
  }

  function fechar() {
    if (listaRegistros) listaRegistros.hidden = true;
    if (campoBusca) {
      campoBusca.setAttribute('aria-expanded', 'false');
      campoBusca.removeAttribute('aria-activedescendant');
    }
    ativo = -1;
  }

  function realcar(i) {
    var itens = listaRegistros.querySelectorAll('.combo__opt');
    Array.prototype.forEach.call(itens, function (el, k) {
      el.setAttribute('aria-selected', k === i ? 'true' : 'false');
    });
    if (i >= 0 && itens[i]) {
      campoBusca.setAttribute('aria-activedescendant', itens[i].id);
      itens[i].scrollIntoView({ block: 'nearest' });
    }
  }

  function escolher(r, fecharLista) {
    selecionado = r;
    if (idRegistro) idRegistro.value = r.id;
    if (textoManual) textoManual.value = '';
    if (campoBusca) campoBusca.value = r.nome;
    var local = [r.mun, r.uf].filter(Boolean).join('/');
    status('Selecionado: ' + r.nome + (local ? ' — ' + local : '') + '.', true);
    if (fecharLista) fechar();
  }

  function limparSelecao() {
    selecionado = null;
    if (idRegistro) idRegistro.value = '';
    if (textoManual) textoManual.value = '';
    if (campoBusca) campoBusca.value = '';
    status('');
    fechar();
  }

  if (campoBusca) {
    var debounce = null;
    campoBusca.addEventListener('focus', carregar);
    campoBusca.addEventListener('input', function () {
      try { tratarDigitacao(); } catch (e) { status('A busca falhou neste navegador (' + e.message + '). Escreva o nome da casa e siga — ele vai na contribuição.'); }
    });
    function tratarDigitacao() {
      carregar();
      // Sem seleção da lista, o texto digitado ainda vale como nome — nada se perde.
      selecionado = null;
      if (idRegistro) idRegistro.value = '';
      if (textoManual) textoManual.value = campoBusca.value.trim();
      if (!campoBusca.value.trim()) status('');
      clearTimeout(debounce);
      debounce = setTimeout(function () {
        try { renderizar(); } catch (e) { status('A busca falhou neste navegador (' + e.message + '). Escreva o nome da casa e siga.'); }
      }, 110);
    }
    campoBusca.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
        if (!resultados.length) return;
        ev.preventDefault();
        ativo = ev.key === 'ArrowDown'
          ? (ativo + 1) % resultados.length
          : (ativo <= 0 ? resultados.length - 1 : ativo - 1);
        realcar(ativo);
      } else if (ev.key === 'Enter') {
        if (ativo >= 0 && resultados[ativo]) { ev.preventDefault(); escolher(resultados[ativo], true); }
        else if (resultados.length === 1) { ev.preventDefault(); escolher(resultados[0], true); }
        else fechar();
      } else if (ev.key === 'Escape') {
        fechar();
      } else if (ev.key === 'Tab') {
        fechar();
      }
    });
    campoBusca.addEventListener('blur', function () { setTimeout(fechar, 120); });
  }

  // ---- estado inicial a partir da URL --------------------------------------
  var qs = new URLSearchParams(location.search);
  preId = qs.get('registro') || qs.get('id');
  if (preId) {
    marcarTipo('no_mapa');
    carregar();   // resolve o nome a partir do id; o campo mostra o nome assim que a lista chega
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
    if (selecionado) {
      var local = [selecionado.mun, selecionado.uf].filter(Boolean).join('/');
      return selecionado.nome + ' [' + selecionado.id + (local ? ' — ' + local : '') + ']';
    }
    var digitado = v('registro_manual');
    if (digitado) return digitado + ' (não escolhido na lista)';
    if (preId) return preId + ' (registro do link, nome não carregado)';
    return '(não informado)';
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
    L.push('E-mail: ' + (v('contato') || '(não informado)'));
    L.push('Telefone: ' + (v('telefone') || '(não informado)'));
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
      abrirMailto(corpo);
      mostrarOk('mailto', corpo);
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Enviando…';
    var dados = new FormData(form);
    dados.append('_subject', assunto());
    dados.append('conteudo', corpo);
    fetch(ENDPOINT, { method: 'POST', body: dados, headers: { Accept: 'application/json' } })
      .then(function (r) {
        if (r.ok) return;
        // O servidor respondeu e recusou. Isso NÃO é falha de conexão — e tratá-la como tal
        // manda a pessoa reenviar à mão um erro que pode ser do próprio serviço.
        var e = new Error('HTTP ' + r.status);
        e.status = r.status;
        throw e;
      })
      .then(function () {
        form.reset(); atualizar(); limparSelecao();
        btn.disabled = false; btn.textContent = 'Enviar contribuição';
        mostrarOk('enviado', corpo);
      })
      .catch(function (err) {
        btn.disabled = false; btn.textContent = 'Enviar contribuição';
        // fetch só rejeita sozinho quando não houve resposta nenhuma; com status, houve resposta.
        mostrarFalha(err && err.status, corpo);
      });
  });

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

  // Dispara o cliente de e-mail num iframe: navegar a própria página para mailto: a deixaria
  // em branco em vários navegadores, escondendo a instrução de enviar.
  function abrirMailto(corpo) {
    var link = 'mailto:' + EMAIL +
      '?subject=' + encodeURIComponent(assunto()) +
      '&body=' + encodeURIComponent(corpo);
    var frame = document.createElement('iframe');
    frame.style.display = 'none';
    frame.setAttribute('aria-hidden', 'true');
    document.body.appendChild(frame);
    frame.src = link;
    setTimeout(function () { frame.remove(); }, 4000);
  }

  // Falha de envio: o formulário continua na tela, com o que a pessoa digitou — nada se perde.
  // E o recado muda conforme a causa: servidor que recusou não é o mesmo problema que rede muda.
  function mostrarFalha(status, corpo) {
    var titulo, texto;
    if (status) {
      titulo = 'O servidor recusou o envio';
      texto = 'A mensagem não foi registrada — o servidor respondeu com o código ' + status +
        '. Costuma ser passageiro. Tente de novo em alguns minutos; se repetir, envie por e-mail, ' +
        'com o texto já preenchido.';
    } else {
      titulo = 'Não conseguimos falar com o servidor';
      texto = 'A mensagem não saiu: o navegador não recebeu resposta nenhuma. Pode ser conexão ' +
        'interrompida, rede que bloqueia o envio ou extensão do navegador. Tente de novo ou envie ' +
        'por e-mail, com o texto já preenchido.';
    }
    saida.hidden = false;
    saida.innerHTML = '<div class="falha" role="alert">' +
      '<h2>' + titulo + '</h2>' +
      '<p>' + texto + '</p>' +
      '<div class="acoes">' +
        '<button type="button" class="btn-primary" id="retentar">Tentar de novo</button>' +
        '<button type="button" class="btn-ghost" id="por-email">Enviar por e-mail</button>' +
        '<button type="button" class="btn-ghost" id="copiar">Copiar a mensagem</button>' +
      '</div>' +
      '<label for="resumo" style="display:block;margin:0 0 6px;font-size:12.5px;font-weight:600;color:var(--text)">Prévia da mensagem</label>' +
      '<textarea id="resumo" readonly>' + esc(corpo) + '</textarea>' +
      '<p style="margin:12px 0 0;font-size:12.5px">Se nada funcionar, escreva para ' +
      '<a href="mailto:' + EMAIL + '">' + EMAIL + '</a>.</p></div>';
    document.getElementById('retentar').addEventListener('click', function () {
      saida.hidden = true; saida.innerHTML = '';
      if (form.requestSubmit) form.requestSubmit(); else btn.click();
    });
    document.getElementById('por-email').addEventListener('click', function () {
      abrirMailto(corpo);
      this.textContent = 'Abrimos seu aplicativo de e-mail';
    });
    var copiar = document.getElementById('copiar');
    copiar.addEventListener('click', function () {
      var ta = document.getElementById('resumo');
      ta.select();
      if (navigator.clipboard) {
        navigator.clipboard.writeText(ta.value).then(function () { copiar.textContent = 'Copiado'; });
      }
    });
    saida.scrollIntoView({ block: 'start' });
  }
})();
