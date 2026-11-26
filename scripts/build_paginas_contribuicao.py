#!/usr/bin/env python3
"""Gera as duas páginas novas do site: contribuir.html (formulário único) e
politica-de-contribuicoes.html.

As páginas reaproveitam <head> e CSS de metodologia.html — copiados literalmente, sem
interpretação — para nascerem com a mesma identidade visual. A cópia é feita uma vez por
execução; se o CSS da metodologia mudar, basta rodar de novo.

Uso: python3 scripts/build_paginas_contribuicao.py
"""
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METO = os.path.join(REPO, "metodologia.html")
POLITICA_MD = os.path.join(REPO, "POLITICA_DE_CONTRIBUICOES.md")


# ---------------------------------------------------------------------------
# 1. Cabeçalho compartilhado
# ---------------------------------------------------------------------------
def extrair_base():
    with open(METO, encoding="utf-8") as fh:
        html = fh.read()
    fim_style = html.index("</style>") + len("</style>")
    base = html[:fim_style]
    return base


def cabecalho(titulo, descricao, secao):
    base = extrair_base()
    base = re.sub(r"<title>.*?</title>",
                  "<title>%s | Ilê Axé Map</title>" % titulo, base, flags=re.S)
    base = re.sub(r'<meta name="description" content=".*?">',
                  '<meta name="description" content="%s">' % descricao, base, flags=re.S)
    return base


def header_html(secao):
    return """<body%s>
  <a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
  <header class="site-header">
    <div class="site-header__inner">
      <a class="brand" href="./" aria-label="Ilê Axé Map, página inicial">Ilê Axé <span>Map</span></a>
      <span class="header-rule" aria-hidden="true"></span>
      <span class="header-section">%s</span>
      <span class="header-spacer"></span>
      <a class="map-link" href="./"><span aria-hidden="true">←</span> Voltar ao mapa</a>
    </div>
  </header>
""" % (" data-endpoint=\"\"" if secao == "Contribuir" else "", secao)


CSS_FORM = """
    /* ---- formulário ---- */
    .form-wrap { max-width: 800px; margin: 0 auto; padding: 0 24px 80px; }
    fieldset { margin: 0 0 24px; padding: 22px 24px 6px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface); }
    legend { padding: 0 10px; margin-left: -10px; font: 600 12px var(--body); letter-spacing: .1em; text-transform: uppercase; color: var(--warm); }
    .field { margin: 0 0 18px; }
    .field > label, .field > .label { display: block; margin-bottom: 6px; font-size: 14.5px; font-weight: 600; color: var(--text); }
    .field .hint { display: block; margin: 0 0 8px; font-size: 13px; line-height: 1.55; color: var(--faint); }
    .field input[type=text], .field input[type=email], .field input[type=url],
    .field input[type=number], .field select, .field textarea {
      width: 100%; box-sizing: border-box; padding: 10px 12px;
      border: 1px solid var(--border-strong); border-radius: 6px;
      background: var(--bg); color: var(--text); font: 16px var(--body); line-height: 1.45;  /* 16px evita o zoom automático do iOS ao focar */
    }
    .field textarea { min-height: 92px; resize: vertical; }
    .field input:focus, .field select:focus, .field textarea:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
    .choices { display: flex; flex-wrap: wrap; gap: 8px; }
    .choice { display: inline-flex; align-items: center; gap: 7px; min-height: 44px; padding: 9px 14px; border: 1px solid var(--border-strong); border-radius: 100px; background: var(--bg); cursor: pointer; font-size: 14px; color: var(--text); }
    .choice input { margin: 0; accent-color: var(--accent); }
    .choice:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); font-weight: 600; }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 18px; }
    @media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } fieldset { padding: 18px 16px 4px; } .form-wrap { padding: 0 16px 64px; } }
    .priv { margin: 0 0 18px; padding: 11px 13px; border-left: 3px solid var(--warm); background: var(--warm-soft); border-radius: 0 6px 6px 0; font-size: 13.5px; line-height: 1.6; color: var(--muted); }
    .priv strong { color: var(--warm); }
    .required::after { content: " *"; color: var(--warm); }
    .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; margin-top: 26px; }
    .btn-primary { padding: 13px 24px; border: 0; border-radius: 6px; background: var(--accent); color: #fff; font: 600 15px var(--body); cursor: pointer; }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-primary:disabled { opacity: .55; cursor: not-allowed; }
    .btn-ghost { padding: 10px 16px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--bg); color: var(--text); font: 600 14px var(--body); cursor: pointer; }
    .actions__note { margin: 0; font-size: 13px; color: var(--faint); max-width: 380px; }
    .ok { padding: 22px 24px; border: 1px solid var(--accent); border-radius: var(--radius); background: var(--accent-soft); }
    .ok h2 { margin: 0 0 10px; font: 600 22px var(--display); color: var(--text); }
    .ok p { margin: 0 0 12px; font-size: 14.5px; line-height: 1.65; color: var(--muted); }
    .ok a { color: var(--accent); }
    .ok textarea { width: 100%; box-sizing: border-box; min-height: 200px; font: 12.5px ui-monospace, monospace; padding: 10px; border: 1px solid var(--border-strong); border-radius: 6px; background: var(--bg); color: var(--text); }
    /* ---- busca de registro ---- */
    .combo { position: relative; }
    .combo__campo { position: relative; }
    .combo__list { position: absolute; z-index: 40; left: 0; right: 0; top: calc(100% + 4px);
      margin: 0; padding: 4px 4px 6px; list-style: none; max-height: 320px; overflow-y: auto;
      overscroll-behavior: contain; background: var(--bg); border: 1px solid var(--border-strong);
      border-radius: 8px; box-shadow: 0 14px 32px rgba(0,0,0,.16), 0 2px 6px rgba(0,0,0,.06);
      scrollbar-width: thin; scrollbar-color: var(--border-strong) transparent; }
    .combo__list::-webkit-scrollbar { width: 9px; }
    .combo__list::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 9px; }
    .combo__list::-webkit-scrollbar-track { background: transparent; }
    .combo__opt { padding: 9px 11px; border-radius: 5px; cursor: pointer; line-height: 1.35; }
    .combo__opt[aria-selected="true"] { background: var(--accent-soft); }
    .combo__nome { display: block; font-size: 15px; color: var(--text); }
    .combo__meta { display: block; font-size: 12.5px; color: var(--faint); margin-top: 2px; }
    .combo__opt mark { background: #F3D9A8; color: #3A2A16; font-weight: 700; padding: 0 1px; border-radius: 2px; }
    .combo__status { margin: 6px 0 0; font-size: 12.5px; line-height: 1.5; color: var(--faint); min-height: 1.2em; }
    .combo__status--ok { color: var(--accent); font-weight: 600; }
    .combo__rodape { position: sticky; bottom: -6px; margin: 2px 0 0; padding: 7px 11px 6px;
      font-size: 12px; line-height: 1.4; color: var(--faint); background: var(--bg);
      border-top: 1px solid var(--border); }
    .combo__vazio { padding: 14px 12px; font-size: 13.5px; line-height: 1.55; color: var(--muted); }
    .combo__vazio strong { color: var(--text); }
    [hidden] { display: none !important; }
"""


# ---------------------------------------------------------------------------
# 2. contribuir.html
# ---------------------------------------------------------------------------
CORPO_FORM = """<body data-endpoint="">
  <a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
  <header class="site-header">
    <div class="site-header__inner">
      <a class="brand" href="./" aria-label="Ilê Axé Map, página inicial">Ilê Axé <span>Map</span></a>
      <span class="header-rule" aria-hidden="true"></span>
      <span class="header-section">Contribuir</span>
      <span class="header-spacer"></span>
      <a class="map-link" href="./"><span aria-hidden="true">←</span> Voltar ao mapa</a>
    </div>
  </header>

  <main id="conteudo">
    <section class="hero">
      <div class="hero__inner">
        <p class="eyebrow">Contribuição</p>
        <h1>Contribuir com uma ficha</h1>
        <p class="hero__subtitle">Completar, corrigir, incluir ou retirar um registro do Ilê Axé Map</p>
        <div class="document-meta">
          <p>Quem conhece a casa é a própria casa. Preencha só o que souber — campo em branco não atrapalha.
          Publicamos em até 30 dias; <strong>pedidos de retirada saem em até 7 dias, sem exigir justificativa</strong>.
          O que acontece com cada informação está na <a href="politica-de-contribuicoes.html">política de contribuições</a>.</p>
        </div>
      </div>
    </section>

    <div class="form-wrap">
      <form id="form" novalidate>

        <fieldset>
          <legend>A casa</legend>
          <p style="margin:0 0 14px;font-size:12.5px;color:var(--faint)">Os campos com <span style="color:var(--warm)">*</span> são obrigatórios. Todo o resto é opcional.</p>
          <div class="field">
            <span class="label required">A casa já está no mapa?</span>
            <span class="hint">Em dúvida, procure o nome do terreiro no mapa antes de responder.</span>
            <div class="choices" role="radiogroup" aria-label="A casa já está no mapa">
              <label class="choice"><input type="radio" name="tipo_casa" value="no_mapa"> Sim, já está</label>
              <label class="choice"><input type="radio" name="tipo_casa" value="fora_mapa"> Não, ainda não está</label>
            </div>
          </div>
        </fieldset>

        <div id="bloco-no-mapa" hidden>
          <fieldset>
            <legend>Qual registro</legend>
            <div class="field">
              <label for="registro_busca">Terreiro, centro ou casa</label>
              <span class="hint">Digite parte do nome, do município ou a sigla do estado. Acentos e maiúsculas não atrapalham.</span>
              <div class="combo">
                <div class="combo__campo">
                  <input type="text" id="registro_busca" name="registro_busca" role="combobox"
                         aria-expanded="false" aria-controls="lista-registros" aria-autocomplete="list"
                         aria-describedby="registro-status" autocomplete="off" spellcheck="false"
                         placeholder="ex.: tolori, mapele, salvador">
                  <ul id="lista-registros" class="combo__list" role="listbox" aria-label="Registros encontrados" hidden></ul>
                </div>
                <p id="registro-status" class="combo__status" aria-live="polite"></p>
                <input type="hidden" id="registro" name="registro">
                <input type="hidden" id="registro_manual" name="registro_manual">
              </div>
            </div>
            <div class="field">
              <span class="label required">O que você quer fazer</span>
              <div class="choices" role="radiogroup" aria-label="O que você quer fazer">
                <label class="choice"><input type="radio" name="acao" value="completar"> Completar dados que faltam</label>
                <label class="choice"><input type="radio" name="acao" value="corrigir"> Corrigir algo errado</label>
                <label class="choice"><input type="radio" name="acao" value="retirar"> Retirar do mapa</label>
              </div>
            </div>
          </fieldset>
        </div>

        <div id="bloco-fora-mapa" hidden>
          <fieldset>
            <legend>Identificação da casa</legend>
            <div class="field">
              <label for="nome_casa" class="required">Nome do terreiro, centro ou casa</label>
              <span class="hint">Como a casa é conhecida. Se houver nome na língua da tradição, use esse.</span>
              <input type="text" id="nome_casa" name="nome_casa" autocomplete="off">
            </div>
          </fieldset>
        </div>

        <fieldset>
          <legend>Quem está respondendo</legend>
          <div class="priv">
            <strong>Estes campos não são publicados.</strong> Servem para confirmar a contribuição e responder a você.
            Não aparecem no mapa, não entram no repositório público e são apagados em até 12 meses.
          </div>
          <div class="grid2">
            <div class="field">
              <label for="nome_pessoa">Seu nome</label>
              <input type="text" id="nome_pessoa" name="nome_pessoa" autocomplete="name">
            </div>
            <div class="field">
              <label for="contato">E-mail ou telefone para retorno</label>
              <input type="text" id="contato" name="contato" autocomplete="email">
            </div>
          </div>
          <div class="field">
            <span class="label required">Sua relação com a casa</span>
            <div class="choices" role="radiogroup" aria-label="Sua relação com a casa">
              <label class="choice"><input type="radio" name="relacao" value="lideranca"> Liderança</label>
              <label class="choice"><input type="radio" name="relacao" value="membro"> Membro</label>
              <label class="choice"><input type="radio" name="relacao" value="familiar"> Familiar</label>
              <label class="choice"><input type="radio" name="relacao" value="pesquisador"> Pesquisador(a)</label>
              <label class="choice"><input type="radio" name="relacao" value="outra"> Outra</label>
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Tradição</legend>
          <div class="field">
            <span class="label">Vertente religiosa</span>
            <span class="hint">Pode marcar mais de uma, se a casa se reconhece em mais de uma.</span>
            <div class="choices">
              <label class="choice"><input type="checkbox" name="tradicao" value="Candomblé"> Candomblé</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Umbanda"> Umbanda</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Jurema"> Jurema</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Tambor de Mina"> Tambor de Mina</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Batuque"> Batuque</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Omoloko"> Omoloko</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Encantaria"> Encantaria</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Xangô"> Xangô</label>
              <label class="choice"><input type="checkbox" name="tradicao" value="Outra"> Outra</label>
            </div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="nacao">Nação</label>
              <span class="hint">No candomblé: Ketu, Jeje, Angola, Nagô-Vodun…</span>
              <input type="text" id="nacao" name="nacao" autocomplete="off">
            </div>
            <div class="field">
              <label for="raiz">Raiz ou família</label>
              <span class="hint">Se a casa declara: Alaketo, Savalu, Mahin, Bogum…</span>
              <input type="text" id="raiz" name="raiz" autocomplete="off">
            </div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="linha">Linha</label>
              <span class="hint">Na umbanda e em outras tradições, o equivalente à nação: Almas e Angola, Caboclo…</span>
              <input type="text" id="linha" name="linha" autocomplete="off">
            </div>
            <div class="field">
              <label for="regente">Orixá, inquice ou entidade regente</label>
              <input type="text" id="regente" name="regente" autocomplete="off">
            </div>
          </div>
          <div class="field">
            <label for="fundacao">Ano de fundação</label>
            <span class="hint">Só o ano. Se não souber, deixe em branco.</span>
            <input type="number" id="fundacao" name="fundacao" min="1500" max="2026" inputmode="numeric" style="max-width:170px">
          </div>
        </fieldset>

        <fieldset>
          <legend>Onde fica</legend>
          <div class="grid2">
            <div class="field">
              <label for="municipio">Município</label>
              <input type="text" id="municipio" name="municipio" autocomplete="address-level2">
            </div>
            <div class="field">
              <label for="uf">Estado</label>
              <select id="uf" name="uf">
                <option value="">—</option>
                <option>AC</option><option>AL</option><option>AM</option><option>AP</option><option>BA</option>
                <option>CE</option><option>DF</option><option>ES</option><option>GO</option><option>MA</option>
                <option>MG</option><option>MS</option><option>MT</option><option>PA</option><option>PB</option>
                <option>PE</option><option>PI</option><option>PR</option><option>RJ</option><option>RN</option>
                <option>RO</option><option>RR</option><option>RS</option><option>SC</option><option>SE</option>
                <option>SP</option><option>TO</option>
              </select>
            </div>
          </div>
          <div>
            <div class="field">
              <label for="endereco">Endereço</label>
              <span class="hint">Rua, número, bairro e CEP. Se preferir não publicar o número, escreva só a rua e o bairro.</span>
              <input type="text" id="endereco" name="endereco" autocomplete="street-address">
            </div>
            <div class="field">
              <label for="maps">Link do Google Maps</label>
              <span class="hint">No celular: abra o mapa, toque em “Compartilhar” e cole o link aqui. É a forma mais segura de acertar o ponto.</span>
              <input type="url" id="maps" name="maps" inputmode="url">
            </div>
          </div>
          <div class="field">
            <label for="referencia">Ponto de referência</label>
            <span class="hint">Algo que ajude a chegar: “em frente ao campo”, “ao lado da escola”.</span>
            <input type="text" id="referencia" name="referencia">
          </div>
        </fieldset>

        <fieldset>
          <legend>Mais informações</legend>
          <div class="field">
            <label for="social">Instagram ou outro perfil da casa</label>
            <input type="url" id="social" name="social" inputmode="url" placeholder="https://instagram.com/…">
          </div>
          <div class="field">
            <label for="mensagem">O que precisa ser corrigido ou informado</label>
            <span class="hint">Se for correção, diga o que está errado hoje e como deveria ser.</span>
            <textarea id="mensagem" name="mensagem"></textarea>
          </div>
          <div class="field">
            <span class="label">Foto da fachada</span>
            <span class="hint">De preferência sem pessoas. Fotos enviadas pelas casas têm prioridade.</span>
            <div class="choices" role="radiogroup" aria-label="Foto da fachada">
              <label class="choice"><input type="radio" name="foto" value="envio por e-mail"> Vou enviar por e-mail</label>
              <label class="choice"><input type="radio" name="foto" value="não tenho"> Não tenho</label>
            </div>
          </div>
        </fieldset>

        <fieldset>
          <legend>Autorização</legend>
          <div class="field">
            <span class="label required">Autorizo o uso destas informações no mapa, exceto os campos marcados como não publicados</span>
            <div class="choices" role="radiogroup" aria-label="Autorização de uso">
              <label class="choice"><input type="radio" name="autorizo" value="sim" required> Sim</label>
              <label class="choice"><input type="radio" name="autorizo" value="sem número do endereço"> Sim, mas não publiquem o número</label>
              <label class="choice"><input type="radio" name="autorizo" value="não"> Não autorizo</label>
            </div>
          </div>
          <div class="field">
            <span class="label required">Sou liderança, membro, familiar ou representante desta casa</span>
            <div class="choices" role="radiogroup" aria-label="Você representa a casa">
              <label class="choice"><input type="radio" name="represento" value="sim" required> Sim</label>
              <label class="choice"><input type="radio" name="represento" value="não"> Não — envio como pesquisador(a) ou outra pessoa</label>
            </div>
          </div>
          <div class="priv" style="margin-top:16px">
            Ao enviar, você concorda com a <a href="politica-de-contribuicoes.html">política de contribuições</a>.
            Seu nome e contato não são publicados e podem ser apagados a qualquer momento, a seu pedido.
          </div>
        </fieldset>

        <div class="actions">
          <button type="submit" class="btn-primary" id="enviar">Enviar contribuição</button>
          <p class="actions__note">O envio abre seu aplicativo de e-mail com a mensagem já preenchida — e nada em branco.</p>
        </div>
      </form>

      <div id="resultado" hidden></div>
    </div>
  </main>

  <script src="data/contribuir.js"></script>
</body>
</html>
"""


def endpoint_configurado():
    """Lê data/formspree.json. Vazio = o formulário envia por mailto, com o corpo montado."""
    caminho = os.path.join(REPO, "data", "formspree.json")
    if not os.path.exists(caminho):
        return ""
    try:
        with open(caminho, encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("endpoint") or ""
    except (ValueError, OSError):
        return ""


def gerar_contribuir():
    html = cabecalho(
        "Contribuir",
        "Formulário de contribuição do Ilê Axé Map: completar, corrigir, incluir ou retirar um registro.",
        "Contribuir")
    html = html[:html.index("</style>")] + CSS_FORM + "  </style>" + html[html.index("</style>") + len("</style>"):]
    ep = endpoint_configurado()
    corpo = CORPO_FORM.replace('data-endpoint=""', 'data-endpoint="%s"' % ep)
    if ep:
        corpo = corpo.replace(
            "<p class=\"actions__note\">O envio abre seu aplicativo de e-mail com a mensagem já preenchida — e nada em branco.</p>",
            "<p class=\"actions__note\">A contribuição é enviada direto por aqui. Você vê o resumo antes de confirmar.</p>")
    return html + "\n" + corpo


# ---------------------------------------------------------------------------
# 3. politica-de-contribuicoes.html (a partir do .md)
# ---------------------------------------------------------------------------
def md_para_html(md):
    """Conversor mínimo: títulos, parágrafos, listas, tabelas e negrito. Não é um parser
    genérico — é o suficiente para este documento, e o que ele não cobre quebra visivelmente
    na inspeção."""
    linhas = md.split("\n")
    out, i = [], 0
    while i < len(linhas):
        ln = linhas[i]
        if ln.startswith("# "):
            out.append('<p class="eyebrow">Política · contribuições</p>')
            out.append("<h1>%s</h1>" % ln[2:].strip())
            i += 1
            continue
        if ln.startswith("## "):
            texto = ln[3:].strip()
            slug = re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-")
            out.append('<h2 id="%s">%s</h2>' % (slug, inline(texto)))
            i += 1
            continue
        if ln.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].startswith("|"):
                bloco.append(linhas[i])
                i += 1
            out.append(tabela(bloco))
            continue
        if ln.strip() == "":
            i += 1
            continue
        if ln.startswith("- "):
            itens = []
            while i < len(linhas) and (linhas[i].startswith("- ") or linhas[i].startswith("  ")):
                itens.append(linhas[i])
                i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % inline(x[2:].strip()) for x in itens) + "</ul>")
            continue
        par = []
        while i < len(linhas) and linhas[i].strip() and not linhas[i].startswith(("#", "|", "- ")):
            par.append(linhas[i].strip())
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(par)))
    return "\n".join(out)


def inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return s


def tabela(bloco):
    linhas = [l.strip().strip("|").split("|") for l in bloco]
    cab = [c.strip() for c in linhas[0]]
    corpo = [[c.strip() for c in l] for l in linhas[2:] if not re.match(r"^[\s|:-]+$", "|".join(l))]
    html = ['<table><thead><tr>' + "".join("<th>%s</th>" % inline(c) for c in cab) + "</tr></thead><tbody>"]
    for l in corpo:
        html.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in l) + "</tr>")
    html.append("</tbody></table>")
    return "".join(html)


def gerar_politica():
    with open(POLITICA_MD, encoding="utf-8") as fh:
        md = fh.read()
    # remove a primeira linha de título e o frontmatter de trabalho
    md = md.replace("Página espelhada no site: `contribuir.html`.\n", "")
    corpo = md_para_html(md)
    html = cabecalho(
        "Política de contribuições",
        "Como o Ilê Axé Map trata as contribuições recebidas: o que é publicado, o que nunca é publicado e por quanto tempo.",
        "Política")
    html += """
  <style>
    .doc-wrap { max-width: 820px; margin: 0 auto; padding: 0 24px 90px; }
    .doc-hero { max-width: 820px; margin: 0 auto; padding: 56px 24px 30px; }
    .doc-hero h1 { margin: 6px 0 12px; font: 600 clamp(30px,5vw,44px)/1.12 var(--display); letter-spacing: -.02em; color: var(--text); text-wrap: balance; }
    .doc-hero .eyebrow { margin: 0; font: 600 11.5px var(--body); letter-spacing: .16em; text-transform: uppercase; color: var(--warm); }
    .doc-wrap h2 { margin: 44px 0 14px; padding-top: 26px; border-top: 1px solid var(--border); font: 600 25px/1.25 var(--display); letter-spacing: -.012em; color: var(--text); }
    .doc-wrap h2:first-child { margin-top: 0; border-top: 0; padding-top: 0; }
    .doc-wrap p { margin: 0 0 16px; font-size: 15.5px; line-height: 1.72; color: var(--muted); text-wrap: pretty; }
    .doc-wrap strong { color: var(--text); font-weight: 600; }
    .doc-wrap code { padding: 1px 5px; border-radius: 4px; background: var(--accent-soft); font-size: 13px; }
    .doc-wrap ul { margin: 0 0 16px; padding-left: 22px; }
    .doc-wrap li { margin: 0 0 8px; font-size: 15.5px; line-height: 1.68; color: var(--muted); }
    .doc-wrap table { width: 100%; border-collapse: collapse; margin: 0 0 20px; font-size: 14.5px; }
    .doc-wrap th { text-align: left; padding: 10px 12px; background: #4A6E9F; color: #fff; font-weight: 600; }
    .doc-wrap td { padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--muted); vertical-align: top; }
    .doc-wrap tr:nth-child(even) td { background: rgba(0,0,0,.02); }
    .doc-wrap a { color: var(--accent); }
    .back { display: inline-block; margin-top: 10px; font-weight: 600; color: var(--accent); text-decoration: none; }
  </style>
</head>
<body>
  <a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
  <header class="site-header">
    <div class="site-header__inner">
      <a class="brand" href="./" aria-label="Ilê Axé Map, página inicial">Ilê Axé <span>Map</span></a>
      <span class="header-rule" aria-hidden="true"></span>
      <span class="header-section">Política de contribuições</span>
      <span class="header-spacer"></span>
      <a class="map-link" href="./"><span aria-hidden="true">←</span> Voltar ao mapa</a>
    </div>
  </header>
  <main id="conteudo">
    <div class="doc-hero">
      <p class="eyebrow">Política · contribuições</p>
      <h1>Política de contribuições</h1>
      <p style="margin:14px 0 0;font-size:15.5px;line-height:1.7;color:var(--muted);max-width:640px">
        O que chega, o que é publicado, o que nunca é publicado, por quanto tempo o resto fica guardado
        e como se pede para sair.</p>
    </div>
    <div class="doc-wrap">
""" + corpo + """
      <p style="margin-top:36px"><a class="back" href="contribuir.html">Ir para o formulário de contribuição →</a></p>
    </div>
  </main>
</body>
</html>
"""
    # o h1 do markdown vira o do hero
    html = html.replace('<p class="eyebrow">Política · contribuições</p>\n<h1>Política de contribuições</h1>\n', "", 1)
    return html


def main():
    for nome, conteudo in (("contribuir.html", gerar_contribuir()),
                           ("politica-de-contribuicoes.html", gerar_politica())):
        caminho = os.path.join(REPO, nome)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
        print(f"escrito: {nome} ({len(conteudo)} bytes)")

    # JS separado, para poder ser cacheado e não inflar o HTML
    js_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_contribuir.js")
    with open(js_src, encoding="utf-8") as fh:
        js = fh.read()
    destino = os.path.join(REPO, "data", "contribuir.js")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write(js)
    print(f"escrito: data/contribuir.js ({len(js)} bytes)")


if __name__ == "__main__":
    main()
