#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Taxonomia de três níveis da v4.8 (tradição → nação → raiz), extraída de
build_v4_8_taxonomia.py para uso compartilhado, sem efeitos colaterais.

Uso:
    from taxonomia_v48 import parse, norm, M, MISSING
"""
import re
import unicodedata
import collections

def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()

M = {}
def add(tokens, trad=None, nacoes=(), raiz=None, linhas=(), pratica=None, acao='mapear', nota=''):
    for t in tokens:
        M[norm(t)] = dict(trad=trad, nacoes=list(nacoes), raiz=raiz,
                          linhas=list(linhas), pratica=pratica, acao=acao, nota=nota)

# ---------- nível 2: matrizes / nações ----------
add(['angola', 'angola lokumbata', 'angolao', 'angola bantu'], 'Candomblé', ['Angola'])
add(['bantu', 'muxicongo', 'moxicongo', 'congo', 'kongo', 'mocambique'], 'Candomblé', ['Bantu'])
add(['ketu', 'keto', 'queto', 'ketu keta'], 'Candomblé', ['Ketu'])
add(['alaketo', 'alaketu'], 'Candomblé', ['Ketu'], raiz='Alaketo',
    nota='Alaketo é raiz/família dentro de Ketu, não nação')
add(['jeje', 'mina', 'mina jeje', 'vodum', 'jeje eba', 'jeje egba', 'mina vodum', 'gessa'],
    'Candomblé', ['Jeje'])
add(['jeje savalu'], 'Candomblé', ['Jeje'], raiz='Savalu')
add(['jeje mahin'], 'Candomblé', ['Jeje'], raiz='Mahin')
add(['nago', 'nago eba', 'nago egba', 'yoruba', 'ioruba'], 'Candomblé', ['Nagô'])
add(['oyo'], 'Candomblé', ['Oyó'])
add(['xamba'], 'Candomblé', ['Xambá'])
add(['cabinda', 'nago cabinda'], 'Candomblé', ['Cabinda'])
add(['ijexa', 'ojafurum'], 'Candomblé', ['Ijexá'])
add(['efon'], 'Candomblé', ['Efon'])
add(['nago tedo', 'tedo'], 'Candomblé', ['Nagô'], raiz='Tedô')
add(['omoloco'], 'Omoloko', [])
add(['caboclo'], 'Candomblé', ['Caboclo'])
add(['mina de caboclo'], 'Tambor de Mina', ['Caboclo'])
# ---------- cruzamentos declarados ----------
add(['jeje ijexa'], 'Candomblé', ['Jeje', 'Ijexá'])
add(['jeje nago', 'nago jeje'], 'Candomblé', ['Jeje', 'Nagô'])
add(['jeje nago eba'], 'Candomblé', ['Jeje', 'Nagô'], raiz='Ebá')
add(['oyo jeje', 'oya jeje'], 'Candomblé', ['Oyó', 'Jeje'])
add(['nago vodum', 'vodum nago'], 'Candomblé', ['Nagô', 'Jeje'])
add(['keto angola', 'angola keto'], 'Candomblé', ['Ketu', 'Angola'])
add(['keto jeje', 'jeje keto', 'angola jeje keto', 'jeje nago keto'], 'Candomblé', ['Ketu', 'Jeje'])
add(['keto ijexa', 'ijexa keto'], 'Candomblé', ['Ketu', 'Ijexá'])
add(['keto nago'], 'Candomblé', ['Ketu', 'Nagô'])
add(['nago ijexa'], 'Candomblé', ['Nagô', 'Ijexá'])
add(['keto caboclo'], 'Candomblé', ['Ketu', 'Caboclo'])
add(['angola caboclo'], 'Candomblé', ['Angola', 'Caboclo'])
add(['caboclo jeje'], 'Candomblé', ['Caboclo', 'Jeje'])
add(['caboclo nago'], 'Candomblé', ['Caboclo', 'Nagô'])
add(['angola umbanda'], 'Candomblé', ['Angola'], linhas=['Umbanda'])
add(['keto alaketo'], 'Candomblé', ['Ketu'], raiz='Alaketo')
add(['jeje angola'], 'Candomblé', ['Jeje', 'Angola'])
add(['angola paketan'], 'Candomblé', ['Angola'], raiz='Paketan')
add(['mina nago', 'mina jeje nago'], 'Candomblé', ['Jeje', 'Nagô'])
add(['oyo ijexa'], 'Candomblé', ['Oyó', 'Ijexá'])
add(['nago vodu', 'yoruba eba'], 'Candomblé', ['Nagô'])
add(['ketu nago'], 'Candomblé', ['Ketu', 'Nagô'])
add(['egba'], 'Candomblé', ['Nagô'], raiz='Egba')
add(['amburaxo angola', 'angola muxicongo', 'angola moxicongo'], 'Candomblé', ['Angola'])
add(['jeje mahin savalu'], 'Candomblé', ['Jeje'], raiz='Mahin/Savalu')
add(['ojafurum ijexa'], 'Candomblé', ['Ijexá'], raiz='Ojafurum')
add(['umbanda pura', 'umbanda tracada com xango', 'umbanda e exu', 'espirita umbandista', 'setes linhas de umbanda', 'linha branca pura'], 'Umbanda')
add(['jurema tracada'], 'Jurema')
add(['embanda'], 'Umbanda', acao='revisar')
add(['ketotapa', 'keto tapa'], 'Candomblé', ['Ketu'], raiz='Tapa', acao='revisar')
add(['grono keto', 'keto giro'], 'Candomblé', ['Ketu'], acao='revisar',
    nota='valor não reconhecido; provável erro de digitação na fonte')
# ---------- outras tradições ----------
add(['umbanda', 'unbandaime'], 'Umbanda')
add(['umbanda linha branca', 'umbanda pura linha branca', 'linha branca'],
    'Umbanda', linhas=['Linha Branca'])
add(['umbanda cruzada', 'linha cruzada'], 'Umbanda', linhas=['Linha Cruzada'])
add(['quimbanda'], 'Umbanda', linhas=['Quimbanda'])
add(['umbanda com nago', 'umbanda nativa', 'umbanda moxicongo', 'umbanda lunda kioko',
     'afro umbandista', 'umbandomble'], 'Umbanda', acao='revisar')
add(['sete linhas', 'linha de oxossi', 'linha cigana oriental', 'linha do oriente',
     'povo do oriente', 'cigano'], 'Umbanda', linhas=['Linha Branca'])
add(['jurema', 'jurema sagrada'], 'Jurema')
add(['catimbo'], 'Jurema', nota='Catimbó tratado como variante de Jurema')
add(['jare'], 'Jarê')
add(['tambor de mina', 'tore'], 'Tambor de Mina')
add(['tereco', 'tambor da mata'], 'Terecô')
add(['batuque'], 'Batuque')
add(['xango'], 'Xangô')
add(['pena e maraca', 'encantado', 'encantado pajelanca', 'pajelanca'], 'Encantaria')
add(['mesa branca'], 'Mesa Branca')
add(['espirita', 'espirita linha branca', 'espiritismo', 'kardecista', 'esoterista'],
    'Espiritismo')
add(['matriz africana', 'nacao africana', 'africana', 'africanista', 'afro',
     'afro brasileiro', 'afro brasileira'], 'Matriz Africana')
add(['candomble'], 'Candomblé')
# ---------- práticas (não são nação) ----------
add(['culto a baba egun', 'culta a baba egun', 'baba egun'], 'Candomblé', pratica='Babá Egun')
add(['tradicao de ifa', 'tradicao de ifa com candomble'], 'Candomblé', pratica='Ifá')
# ---------- ruído / administrativo ----------
add(['outro', 'outros', 'outra', 'nao informado', 'nacao', 'todas', 'mista'],
    None, acao='descartar')
add(['centro espirita'], None, acao='mapear',
    nota='rótulo institucional/nome da casa, não declaração de tradição — vai para "Não especificada"')
add(['terreiro'], None, acao='mapear',
    nota='"Terreiro" é tipo de entidade, não tradição — vai para "Não especificada"')
add(['bobo quexa', 'mucurumi', 'guine', 'angola e alma', 'gessa'], None, acao='revisar',
    nota='valor isolado não identificado; revisão humana')

MISSING = collections.Counter()

def convert_token(tok):
    n = norm(tok)
    if n in M:
        return M[n]
    MISSING[n] += 1
    return dict(trad=None, nacoes=[], raiz=None, linhas=[], pratica=None,
                acao='revisar', nota='valor sem correspondência')

def tokens_of(decl):
    """Quebra um valor declarado em pedaços mapeáveis."""
    out = []
    for part in re.split(r'\s*[,;/]\s*|\s+-\s+', str(decl or '')):
        p = norm(part)
        if not p: continue
        if p in M:
            out.append(part); continue
        # tenta " e " só se os dois lados existirem
        if ' e ' in p:
            a, b = p.split(' e ', 1)
            if a in M and b in M:
                out += [a, b]; continue
        out.append(part)
    return out

def parse(decls):
    trad, nac, raiz, lin, pra = [], [], None, [], None
    revisar = []
    for decl in decls:
        if not decl: continue
        for tok in tokens_of(decl):
            d = convert_token(tok)
            if d['acao'] == 'revisar': revisar.append(tok)
            if d['trad'] and d['trad'] not in trad: trad.append(d['trad'])
            for x in d['nacoes']:
                if x not in nac: nac.append(x)
            for x in d['linhas']:
                if x not in lin: lin.append(x)
            raiz = raiz or d['raiz']
            pra = pra or d['pratica']
    # tradição principal: a primeira que não for "Matriz Africana"
    principal = next((t for t in trad if t != 'Matriz Africana'), None) or (trad[0] if trad else None)
    adicionais = [t for t in trad if t != principal]
    return dict(tradicao=principal or 'Não especificada',
                tradicoes_adicionais=adicionais,
                nacoes=nac, raiz=raiz, linhas=lin, pratica=pra,
                cruzamento=len(set(trad)) > 1, revisar=revisar)
