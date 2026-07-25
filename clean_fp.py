#!/usr/bin/env python3
"""Remove falsos positivos do GeoJSON — abordagem simples por substring."""
import json

# === Carregar GeoJSON ===
with open('data/terreiros.geojson') as f:
    geo = json.load(f)

print(f"GeoJSON original: {len(geo['features'])} features")

# === Lista de nomes de falsos positivos (do scan anterior) ===
with open('data/falsos_positivos_suspeitos.json') as f:
    scan = json.load(f)

fp_names = set()
for fp in scan['google_false_positives']:
    fp_names.add(fp['nome'].strip())

print(f"Falsos positivos identificados: {len(fp_names)}")

# === Palavras-chave que indicam NÃO-terreiro (substring, case-insensitive) ===
nao_terreiro_kw = [
    # Comércio
    'hotel', 'pousada', 'hostel', 'albergue', 'restaurante', 'lanchonet',
    'cafeteria', 'quiosque', 'delivery', 'meat house', 'choperia', 'petiscaria',
    'pet shop', 'petshop', 'mascote pet',
    'barbearia', 'cabelele', 'academia', 'crossfit', 'muscula',
    'supermerc', 'mercearia', 'convenien', 'mercad', 'varej', 'atacad',
    'mercadinho', 'bazar', 'padaria', 'laticinios', 'loteria',
    'agencia', 'imobil', 'locac', 'aluguel', 'corretor', 'avaliador',
    'advogad', 'oab', 'ordem dos advogados',
    'material de constru', 'madeireira', 'telhas',
    'enxov', 'moda', 'boutique', 'fashion', 'acabamentos',
    'bar elite', 'bate papo', 'casa do tempero', 'casa de frios',
    'casa do queijo', 'la casa de pastel', 'sabor da casa',
    'tempero da ilha', 'restaurante casa', 'casa delivery',
    'quintal de casa', 'casa de carne', 'acougue', 'açougue',
    'casa de pneu', 'casa do adubo', 'casa do cimento',
    'casa do led', 'casa do pintor', 'casa do som',
    'casa das bebidas', 'casa das embalagens', 'casa das antenas',
    'casa dos radiadores', 'casa da ferramenta', 'casa da fruta',
    'casa da pizza', 'casa da sopa', 'casa das sandalias',
    'casa das sandálias', 'casa do crochê', 'casa do croche',
    'casa do vergalhao', 'casa do vergalhão', 'casa do bol',
    'casa do parabrisa', 'casa do instalador',
    'casa lotérica', 'casa loterica', 'caixa aqui',
    'casa mais fácil', 'casa mais facil',
    # Saúde/instituição
    'hospital', 'clini', 'posto de saude', 'consultor', 'estetica',
    'oftalm', 'prefeitur', 'prefecture', 'santa casa',
    'camara municipal', 'câmara municipal', 'defensoria',
    'department of social', 'embasa', 'eletrosantos', 'enersol',
    'escola municipal', 'ibge', 'sac municipal', 'secretaria',
    # Turismo/lazer
    'shopping', 'airport', 'aeroporto', 'parque shopping',
    'marina', 'lighthouse', 'farol', 'terminal', 'rodoviaria',
    'safe harbor', 'balsa', 'passarela', 'porto seco', 'porto center',
    'vlt', 'orla', 'praia', 'mirante', 'serra do', 'morro do',
    'chapada', 'parque history', 'beco', 'praca', 'praça',
    'alto do cruzeiro', 'monumento', 'cidade historica',
    'city of', 'spring island', 'lagoon',
    'cachoeira do', 'condominio', 'loteamento', 'residencial',
    'ilha society', 'ilha bela', 'ilha do ouro', 'ilha do frade',
    'ilha do urubu', 'ilha das corredeiras', 'ilha pedra',
    'ilha coroa', 'ilha 9', 'ilha verde',
    'casa de campo', 'casa de temporada', 'casa di vó',
    'casa di vo', 'casa arcadia', 'casa design',
    'casa verde', 'casa oliveira', 'casa mascarenhas',
    'casa vasconcelos', 'casa tucano', 'casa valen', 'casa dez',
    'casa tobias', 'casa mariano', 'casa bateia', 'casa popular',
    'casa da pessoa', 'casa do rio', 'casa do espanto',
    'casa de cecília', 'casa de costura',
    'cabana', 'barraca de praia', 'axé beach', 'casa da praia',
    'casa flor itacaré', 'casa de charm', 'pousada',
    'eco resort', 'resort', 'all inclusive',
    # Cultura/memorial (não-terreiro)
    'culture center', 'centro de cultura', 'palacio das artes',
    'museu', 'memorial', 'monument', 'nucleo historico',
    'ruinas', 'afro-brazilian museum', 'cultural afro brazilian',
    'casa de jorge amado', 'foundation', 'fundação',
    'casa de rui barbosa', 'casa de cultura',
    # Igreja católica/evangélica
    'igreja universal', 'igreja catolica', 'igreja católica',
    'igreja batista', 'igreja messianica', 'igreja do evangelho',
    'igreja metodista', 'igreja presbiteriana',
    'assembleia de deus', 'congregação cristã', 'congregacao crista',
    'universal church', 'paroquia', 'parish', 'cathedral',
    'diocese', 'diocesan', 'basilica', 'basílica',
    'capela da serra', 'capela de santo', 'capela de sant',
    'igreja matriz', 'igreja de sant', 'igreja de nossa',
    'igreja nova', 'igreja e convento', 'convento',
    'gruta de', 'gruta da', 'santuário nossa', 'santuario nossa',
    'santuário da santa cruz', 'santuario da santa cruz',
    'santuário de monte santo', 'santuario de monte santo',
    'co-catedral', 'catedral senhora', 'igreja de senhora',
    'igreja de sant ana', 'igreja de santana',
    'church of the third', 'chapel st', 'shop st',
    'st. antônio', 'st. antonio', 'san antonio house',
    'san sebastian cathedral', 'san francisco church',
    'roman catholic diocese', 'igreja da antiga',
    'centro de espiritualidade', 'casa paroquial',
    # Espiritismo/Kardecismo
    'centro kardecista', 'grupo espirita', 'espirita',
    'espírita', 'lar espirita', 'centro espirita',
    'kardecista', 'taize community', 'secal',
    'sociedade espirita', 'centro espiritualista',
    # Cemitério
    'cemiterio', 'cemitério', 'campo santo',
    # Indígena (não-terreiro)
    'aldeia filhos', 'aldeia tupinambá', 'aldeia tupinamba',
    'sitio raio de luz', 'monument to indian',
    # Maçonaria
    'loja maçonica', 'loja maconica', 'maçônica', 'maconica',
    # Outros não-religiosos
    'casa do carnaval', 'casa do carnval',
    'estacionamento', 'estacion',
    'júnior som', 'junior som', 'vini áudio', 'vini audio',
    'audio tec', 'áudio tec',
    'informatica', 'enzo informatica',
    'agua mineral', 'água mineral', 'absa limpa', 'absa loc',
    'fossa', 'cosmeticos', 'industria', 'inpasa',
    'lazo industria', 'matecol', 'absa',
    'bichinhos de casa', 'santo mascote',
    'funeraria', 'funerária', 'funerária santo', 'funeraria santo',
    'funerária deus', 'funeraria deus',
    'casa de fogos', 'casa de rações', 'casa de ração',
    'casa de plantas', 'casa de pneus',
    'casa de antônia', 'casa de antonia', 'casa de antônio', 'casa de antonio',
    'casa de bianca', 'casa de júlia', 'casa de julio', 'casa de junior',
    'casa de júnior', 'casa de mateus', 'casa de cida',
    'casa de mãe', 'casa de mae', 'casa de tope',
    'casa de caçula', 'casa de cacula', 'casa de residência',
    'casa de residencia', 'casa de atendimento',
    'casa de velas', 'casa de isaque',
    'casa 27', 'casa abade', 'casa cacau',
    'casa de oraçao irm', 'casa de oração irm',
    'casa de oraçao maria', 'casa de oração maria',
    'casa de oraçao irmãos', 'casa de oração irmãos',
    'casa de oraçao irmãos em cristo', 'casa de oração irmãos em cristo',
    'comunidade catolica', 'comunidade católica',
    'comunidade divino espirito', 'comunidade divino espírito',
    'espaço catolico', 'espaço católico', 'cantinho do cristão',
    'casa worship', 'casa de oração', 'casa de oraçao',
    'casa de retiro', 'casa ecumênica', 'casa ecumenica',
    'igreja batista canaa', 'igreja do evangelho quadrangular',
    'igreja messiânica', 'casa da paz igreja',
    'igreja casas de oração', 'igreja casa de oraçao',
    'comunidade casa de oração', 'comunidade casa de oraçao',
    'casa de oração tabernaculo', 'casa de oraçao tabernaculo',
    'quilombo erê', 'quilombo zizi',
    'sitio histórico', 'sitio arqueolog', 'sitio do mato',
    'sitio do quinto', 'sitio santo antônio', 'sitio santo antonio',
    'sitio santana', 'sitio histórico governador',
    'casa de antônia fernandes',
    'casa de júnior e zene', 'casa de junior e zene',
    'gilmara santos', 'casa neia', 'casa júnior andrade',
    'casa junior andrade', 'casa ramalho', 'casa mariense',
    'casa gilmara', 'ideal veículos', 'ideal veiculos',
    'casa do parabrisa',
    'embratur', 'turismo',
    'casa de jaci', 'casa de jací',
    'flour house', 'maison', 'vila temão', 'vila de santo andré',
    'do sahy mission',
    'coroa do limo', 'cristo de mário', 'fonte da bica',
    'divisa de estados', 'high city', 'park history',
    'poço do diabo', 'poço do diabo',
    'pé de serra', 'pe de serra',
    'rafael jambeiro', 'riachao do jacuipe',
    'riachão do jacuípe',
    'são desidério', 'sao desiderio',
    'umburanas', 'simões filho', 'simoes filho',
    'eunapolis bahia', 'eunápolis bahia',
    'vitória da conquista bahia', 'vitoria da conquista bahia',
    'varzea do poço', 'varzea do poco',
    'ponto novo', 'serapião', 'tanquinho',
    'mata de são joão', 'mata de sao joao',
    'madre de deus',
    'mar grande', 'vera cruz',
]

# Termos que indicam POSSÍVEL terreiro — NÃO remover mesmo se tiver "casa"
manter_kw = [
    'casa de santo', 'casa de mina', 'casa de minas',
    'casa de caridade', 'casa de oxal', 'casa de oxum',
    'casa de iemanj', 'casa de xango', 'casa de xangô',
    'casa de ogun', 'casa de ogum', 'casa de exu', 'casa de esu',
    'casa de ossaim', 'casa de logun', 'casa de oxumar',
    'casa de omulu', 'casa de iansa', 'casa de iansã',
    'casa de nana', 'casa de oba', 'casa de oxossi',
    'casa de candombl', 'casa de umband',
    'casa de angola', 'casa de ketu', 'casa de jeje',
    'casa de santo antonio',  # pode ser terreiro umbanda
    'mae de santo', 'mãe de santo', 'pai de santo',
    'casa de ervas pai', 'casa ecumênica pai', 'casa ecumenica pai',
    'imperio do real', 'império do real',
    'templo ogam', 'templo ogun', 'templo do amanhecer',
    'templo atuaro',
    'upaamc', 'união cultural dos sacerdotes',
    'uniao cultural dos sacerdotes',
    'palacio de oya', 'palácio de oya', 'palacio de oyá',
    'palácio de oyá',
    'spiritual center', 'centro de yemanjá', 'centro de yemanja',
    'centro de boiadeiro', 'centro de giro',
    'centro de caboclo',
    'tenda espirit', 'centro espirit',
    'casa de orixá', 'casa de orixa',
    'asé', 'axé', 'abassá', 'roça', 'ile', 'ilê',
    'candombl', 'terreiro', 'tereiro',
    'inzo', 'unzo', 'onzo', 'nzo',
    'mansu', 'manso',
    'dandalunda', 'vodun', 'vodum',
    'nkisi', 'inkisi', 'nkice', 'inkice',
    'ogando', 'ogamor',
    'ogum deui', 'ogun deui',
    'tenda', 'gira de', 'caboclo',
    'centro espirita',  # pode ser umbanda
    # casas de ervas com nomes de orixás
    'casa de ervas santo', 'casa de ervas sao jorge',
    'casa de ervas sao pedro', 'casa de ervas santa barbara',
    'casa de ervas 7 linhas', 'casa de ervas sao',
    'loja reino de ayrà', 'loja reino de ayra',
    'casa do santo dom aquino',
]

def should_remove(nome):
    """Retorna (True, razao) se deve remover, (False, None) se manter."""
    nl = nome.lower().strip()

    # 1. Se está na lista explícita de FPs do scan
    if nome.strip() in fp_names:
        return True, 'Lista FP scan'

    # 2. Se tem keyword de POSSÍVEL terreiro, manter
    for kw in manter_kw:
        if kw in nl:
            return False, None

    # 3. Se tem keyword de NÃO-terreiro
    for kw in nao_terreiro_kw:
        if kw in nl:
            return True, f'KW: {kw}'

    # 4. Se é nome de município baiano puro
    ba_municipios = [
        'alagoinhas', 'amargosa', 'barreiras', 'barrocas', 'biritinga',
        'bonito', 'brumado', 'buerarema', 'cabaceiras', 'caetite',
        'caldeirao grande', 'camacan', 'camacari', 'camamu', 'canapolis',
        'canarana', 'candido sales', 'candeias', 'cansancao',
        'capela do alto alegre', 'caravelas', 'cardeal da silva',
        'carinhanha', 'castro alves', 'catu', 'cerrolina',
        'conde', 'conceição da feira', 'conceiçao da feira',
        'conceição do jacuípe', 'conceiçao do jacuipe',
        'contendas do sincora', 'coribe', 'correntina',
        'cotegipe', 'cravolandia', 'cristopolis',
        'dario meira', 'dias d avila', 'dias davila',
        'dom basilio', 'elisio medrado', 'encruzilhada',
        'esplanada', 'eunapolis', 'eunápolis',
        'filadelfia', 'firmiano alves', 'floresta azul',
        'formosa do rio preto', 'galeao', 'gameleira',
        'gau', 'gongogi', 'governador mangabeira',
        'guanambi', 'handomand', 'iaruba', 'ibirapitanga',
        'ibirapuã', 'ibirataia', 'ibipeba', 'ibitita',
        'ichu', 'igapo', 'iguaraci', 'ipecaeta', 'ipiaú', 'ipiau',
        'ipira', 'iramaia', 'irara', 'irará',
        'itaberaba', 'itaete', 'itaguacu da bahia',
        'itaju do colonia', 'itaju do colônia',
        'itamaraju', 'itamaru', 'itapitanga',
        'itaquara', 'itiruca', 'itirucu', 'ituacu', 'itubera', 'ituberá',
        'jacaraci', 'jaguaquara', 'jaguaripe', 'jandaira',
        'jequie', 'jequié', 'joao dourado', 'joão dourado',
        'jussara', 'lajedao', 'lajedinho', 'lajedo',
        'lapao', 'lencois', 'lençóis', 'licinio de almeida',
        'livramento', 'luís eduardo', 'luis eduardo',
        'macajuba', 'macarani', 'machacalis', 'macaubas', 'macaúbas',
        'madre de deus', 'maetinga', 'malhada', 'malhada de pedras',
        'manoel vitorino', 'marau', 'maracas', 'maraçás', 'maragogipe',
        'marco', 'mascote', 'mata de sao joao', 'mata de são joao',
        'medeiros neto', 'morpara', 'morpará', 'mucuri',
        'mundo novo', 'muritiba', 'mutuipe', 'mutuípe',
        'nazaré', 'nazare', 'nova vicosa', 'nova viçosa',
        'olindina', 'oliveira dos brejinhos', 'ouricana',
        'palmas de monte alto', 'paratinga', 'paripiranga',
        'pedrao', 'pedrão', 'pedro alexandre',
        'pilao arcado', 'pilão arcado', 'pirai do norte', 'piraí do norte',
        'planaltino', 'planalto', 'pocoes', 'poções',
        'potiragua', 'potiraguá', 'prado', 'presidente janio quadros',
        'quijingue', 'quixabeira', 'randolandia',
        'ribeira do pombal', 'ribeirao do largo',
        'riachao do jacuipe', 'riachão do jacuípe',
        'rosangela', 'rui barbosa', 'sapeacu', 'sapeaçu',
        'santa barbara', 'santa cruz cabralia', 'santa cruz cabrália',
        'santa luzia', 'santa maria da vitoria', 'santa maria da vitória',
        'santana', 'santanopolis', 'santo amaro',
        'santo antonio de jesus', 'santo antônio de jesus',
        'sao felipe', 'são felipe', 'sao felix', 'são félix',
        'sao francisco do conde', 'são francisco do conde',
        'sao gabriel', 'são gabriel', 'sao jose da vitoria',
        'são josé da vitória', 'sao miguel das matas',
        'sao sebastiao do passe', 'são sebastião do passe',
        'satiro dias', 'sátiro dias', 'saude', 'saúde',
        'seabra', 'senhor do bonfim', 'serapião', 'serapiao',
        'serrinha', 'sento se', 'sento sé', 'simoes filho', 'simões filho',
        'sitio do quinto', 'sitio do mato',
        'tanhaçu', 'tanquinho', 'tapiramuta', 'tapiramutá',
        'teixeira de freitas', 'teixeirinha',
        'teolandia', 'teolândia', 'terluz', 'tremedal',
        'tucano', 'uaua', 'uauá', 'ubaraba', 'ubata',
        'uirapuru', 'umburanas', 'urandi',
        'valenca', 'valença', 'varzea da roca', 'varzea do poco',
        'varzea do poço', 'varzea nova', 'varzedo',
        'vera cruz', 'vitoria da conquista', 'vitória da conquista',
        'xique xique', 'xique-xique',
        'lira', 'luar', 'pax santos', 'santos divino',
        'santos de fe', 'matrix square',
        'agazetabahia', 'ceak', 'ceasa', 'abapa',
        'fucabase', 'site iguanambi', 'iel eunapolis',
    ]
    for mun in ba_municipios:
        if nl == mun or nl == mun + ' ba' or nl == mun + ' bahia' or nl == mun + '-ba' or nl == mun + ', bahia' or nl == mun + ' bahia' or nl == mun + ' ba.':
            return True, 'Município BA'

    return False, None

# === Filtrar features ===
clean_features = []
removed = []
for feat in geo['features']:
    nome = (feat['properties'].get('nome') or
            feat['properties'].get('name') or '').strip()
    fonte = feat['properties'].get('fonte', '')

    # Só filtrar Google e OSM (CEAO e SEFAZ são curados)
    if fonte in ('google', 'osm'):
        remove, razao = should_remove(nome)
        if remove:
            removed.append({'nome': nome, 'fonte': fonte, 'razao': razao})
            continue

    clean_features.append(feat)

print(f"\nRemovidos: {len(removed)}")
print(f"Restantes: {len(clean_features)}")

# Razões
from collections import Counter
razoes = Counter(r['razao'] for r in removed)
print("\nPor razão:")
for razao, count in razoes.most_common(20):
    print(f"  {razao}: {count}")

# Por fonte
fontes_rem = Counter(r['fonte'] for r in removed)
print("\nPor fonte removida:")
for f, c in fontes_rem.most_common():
    print(f"  {f}: {c}")

# === Salvar GeoJSON limpo ===
geo['features'] = clean_features
if 'metadata' not in geo:
    geo['metadata'] = {}
geo['metadata']['scan_fp'] = {
    'original': len(geo['features']) + len(removed),
    'removidos': len(removed),
    'limpo': len(clean_features),
}
with open('data/terreiros.geojson', 'w') as f:
    json.dump(geo, f, ensure_ascii=False, indent=2)
print(f"\nSalvo: data/terreiros.geojson ({len(clean_features)} features)")

# Salvar lista de removidos
with open('data/falsos_positivos_removidos.json', 'w') as f:
    json.dump({'removidos': removed, 'total': len(removed)}, f, ensure_ascii=False, indent=2)
print(f"Salvo: data/falsos_positivos_removidos.json ({len(removed)} removidos)")

# === Atualizar terreiros_all_sources.json também ===
with open('data/terreiros_all_sources.json') as f:
    all_data = json.load(f)
all_records = all_data['terreiros']
fp_names_all = set(r['nome'] for r in removed)
clean_all = []
for r in all_records:
    nome = (r.get('nome') or r.get('name') or '').strip()
    fonte = r.get('fonte', '')
    if fonte in ('google', 'osm') and nome in fp_names_all:
        continue
    clean_all.append(r)
all_data['terreiros'] = clean_all
with open('data/terreiros_all_sources.json', 'w') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)
print(f"Salvo: data/terreiros_all_sources.json ({len(clean_all)} registros)")

print(f"\n=== RESUMO ===")
print(f"GeoJSON: {len(geo['features']) + len(removed)} -> {len(clean_features)} ({len(removed)} removidos)")
print(f"JSON:    {len(all_records)} -> {len(clean_all)} ({len(all_records) - len(clean_all)} removidos)")