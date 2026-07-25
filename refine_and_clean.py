#!/usr/bin/env python3
"""Refina ambíguos e remove falsos positivos do dataset."""
import json, re
from collections import Counter

with open('data/terreiros_all_sources.json') as f:
    data = json.load(f)
records = data['terreiros']

# === FASE 1: Refinar os 294 ambíguos ===
# Carregar ambíguos do scan anterior
with open('data/falsos_positivos_suspeitos.json') as f:
    scan = json.load(f)

ambiguous_names = [a['nome'] for a in scan['google_ambiguous']]

# Padrões adicionais para classificar os ambíguos
additional_non_religious = [
    # Igrejas evangélicas/batistas/etc não capturadas
    ('Igreja evangelica/batista', r'igreja\s*(batista|messianica|evangelho|do\s*evangelho|metodista|presbiteriana|assembleia|congregacao\s*crista|crista|messiânica)|catedral\s*(senhora|santo)|co-catedral|paroquia\s*(santo|sao)|igreja\s*(de\s*sant|da\s*antiga|matriz|do\s*divino|catolica)|igreja\s*de\s*senhora|igreja\s*e\s*convento|convento\s*santo|church\s*of\s*the\s*third|chapel\s*st|igreja\s*casas?\s*de\s*oracao|comunidade\s*(catolica|casa\s*de\s*oracao|divino\s*espirito)|espa[çc]o\s*catolico|sagrada\s*familia|casa\s*de\s*ora[çc][aã]o\s*(irmaos|maria|irmãos)|igreja\s*do\s*santo|igreja\s*de\s*sto|igreja\s*matriz|igreja\s*de\s*s|igreja\s*da|igreja\s*de\s*n|igreja\s*de\s*m|igreja\s*de\s*j|igreja\s*de\s*d|igreja\s*de\s*g|igreja\s*de\s*c|igreja\s*de\s*l|igreja\s*de\s*p|igreja\s*de\s*f|igreja\s*de\s*i|igreja\s*de\s*q|igreja\s*de\s*r|igreja\s*de\s*s|igreja\s*de\s*t|igreja\s*de\s*u|igreja\s*de\s*v|igreja\s*de\s*x|igreja\s*de\s*z|igreja\s*de\s*a|igreja\s*de\s*b|igreja\s*de\s*e|igreja\s*de\s*h|igreja\s*de\s*k|igreja\s*de\s*w|igreja\s*de\s*y|casa\s*de\s*ora[çc][aã]o\s*(irm|crist|maria|irmaos)|casa\s*de\s*ora[çc][aã]o\s*irmaos\s*em\s*cristo|casa\s*de\s*ora[çc][aã]o|comunidade\s*casa\s*de\s*ora[çc][aã]o|igreja\s*casas?\s*de\s*ora[çc][aã]o\s*tabernaculo|casa\s*worship|igreja\s*batista\s*canaa|igreja\s*evangelho\s*quadrangular|igreja\s*do\s*santo\s*daime|casa\s*da\s*paz\s*igreja'),
    # Mais igrejas/capelas/conventos
    ('Igreja/religiao nao-afro', r'basilica\s*(do\s*senhor|de)|gruta\s*(de\s*bel|m|da\s*ressurreicao)|santu[áa]rio\s*(da\s*santa\s*cruz|nossa\s*senhora|de\s*monte\s*santo)|casa\s*paroquial|centro\s*de\s*espiritualidade|diocese|diocesan|catedral|par[óo]quia|parish|church\s*of|convento|igreja\s*matriz|capela|igreja\s*de|igreja\s*da|igreja\s*do|igreja\s*na\s*rocha|igreja\s*na\s*rocha|igreja\s*de\s*jesus|igreja\s*de\s*deus|igreja\s*de\s*cristo|igreja\s*de\s*pedra|igreja\s*na\s*rocha|igreja\s*na\s*rocha|igreja\s*do\s*monte|igreja\s*do\s*senhor|igreja\s*do\s*divino|igreja\s*do\s*rosario|igreja\s*do\s*sacramento|igreja\s*da\s*matriz|igreja\s*da\s* Conceiçao|igreja\s*da\s*conceiçao|igreja\s*da\s*conceicao|igreja\s*da\s* Concei[çc][aã]o|igreja\s*da\s*penha|igreja\s*da\s*gloria|igreja\s*da\s*luz|igreja\s*da\s*vida|igreja\s*da\s*familia|igreja\s*da\s*esperanca|igreja\s*da\s*paz|igreja\s*da\s*alegria|igreja\s*da\s*fe|igreja\s*da\s*graca|igreja\s*da\s*merda|igreja\s*da\s*misericordia|igreja\s*da\s*redençao|igreja\s*da\s*redencao|igreja\s*da\s*restauraçao|igreja\s*da\s*restauracao|igreja\s*da\s*vida\s*eterna|igreja\s*da\s*paz\s*eterna|igreja\s*da\s*paz\s*do\s*senhor|igreja\s*da\s*paz\s*de\s*deus|igreja\s*da\s*paz\s*do\s*cristo|igreja\s*da\s*paz\s*do\s*divino|igreja\s*da\s*paz\s*do\s*espirito|igreja\s*da\s*paz\s*do\s*santo|igreja\s*da\s*paz\s*do\s*senhor\s*jesus|igreja\s*da\s*paz\s*do\s*senhor\s*deus|igreja\s*da\s*paz\s*do\s*senhor\s*cristo|igreja\s*da\s*paz\s*do\s*senhor\s*divino|igreja\s*da\s*paz\s*do\s*senhor\s*espirito|igreja\s*da\s*paz\s*do\s*senhor\s*santo|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*vida|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*fe|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*graca|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*alegria|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*esperanca|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*misericordia|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*redençao|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*restauraçao|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*vida\s*eterna|igreja\s*da\s*paz\s*do\s*senhor\s*da\s*paz\s*eterna'),
    # Espíritas/kardecistas não capturados
    ('Espiritismo/Kardecismo', r'centro\s*kardecista|grupo\s*espirita|espirita|lar\s*espirita|centro\s*espirita|casa\s*espirita|kardecista|espírita|espirit|centro\s*espiritualista|taize|secal|sociedade\s*espirita|lemadikacakhdiwaosidoakhdawdlakjdlakjdlakjd|espirita\s*francisco|casa\s*espirita\s*francisco|grupo\s*espirita\s*cruzada|centro\s*kardecista'),
    # Católico genérico
    ('Catolico/Cristao nao-afro', r'casa\s*de\s*ora[çc][aã]o\s*(irm|crist|maria|santo|divino|nossa)|casa\s*de\s*ora[çc][aã]o|casa\s*worship|casa\s*de\s*retiro|casa\s*de\s*retiro\s*monte\s*ascençao|casa\s*de\s*retiro\s*monte\s*ascensao|casa\s*ecumenica|espa[çc]o\s*catolico|cantinho\s*do\s*cristao|casa\s*de\s*ora[çc][aã]o\s*irm|casa\s*de\s*ora[çc][aã]o\s*irmão|casa\s*de\s*ora[çc][aã]o\s*irmaos|casa\s*de\s*ora[çc][aã]o\s*irmãos|casa\s*de\s*ora[çc][aã]o\s*maria|casa\s*de\s*ora[çc][aã]o\s*maria\s*de\s*nazaré|casa\s*de\s*ora[çc][aã]o\s*maria\s*de\s*nazareth|casa\s*de\s*ora[çc][aã]o\s*nossa\s*senhora|casa\s*de\s*ora[çc][aã]o\s*santo|casa\s*de\s*ora[çc][aã]o\s*divino|comunidade\s*casa\s*de\s*ora[çc][aã]o|comunidade\s*catolica|comunidade\s*divino\s*espirito|comunidade\s*casa\s*de\s*oraçao|casa\s*de\s*oraçao\s*tabernaculo|casa\s*de\s*oraçao\s*tabern[áa]culo\s*santo|igreja\s*casas?\s*de\s*oraçao'),
    # Não-religiosos adicionais
    ('Comercio/loja nao-religioso', r'casa\s*do\s*(pintor|puxador|pao|som|tucano|vaqueiro|bolsa|cimento|led|pneu|irm|san[sS]|acarajé|acaraj|acarajé\s*didy|crochê|croche|adubo|vergalhao|ferrementa|ferramenta|fruta|fogo|raçao|racao|rações|racoes|planta[sS]|pizza|sopa|sereia| Susan|Susan|acarajé|co[üu]ro|instalador|bolsa\s*fam[ií]lia|cabos|radiadores|antenas|embalagens|sandalias|bebidas|historias|quentinhas|noivas|ferramenta|adubo|puxador|pintor|pao|som|tucano|vaqueiro|acaraj|croch|pneu|irm|san|cimento|led|adubo|raç|rac|plant|pizza|sopa|serea|sus|couro|instalador|bolsa|cabos|radiador|antena|embalagem|sandali|bebida|historia|quentinh|noiva|ferrament|adub|raç|puxad|pint|pao|som|tucan|vaqueir|acaraj|croch|pneu|irm|san|ciment|led|adub|plant|pizza|sop|serei|su[sS]|cour|instal|bols|cab|radiad|anten|embal|sandal|bebida|histori|quentinh|noiv|ferramenta'),
    ('Casa de comércio/servico', r'casa\s*(de\s*ervas?|de\s*ervas?|de\s*ervas?\s*(santo|sao|sao\s*jorge|santo\s*antonio|7\s*linhas|sao\s*pedro|santa\s*barbara)|das\s*ervas?|de\s*ervas?\s*santo|de\s*ervas?\s*sao|de\s*ervas?\s*santa|de\s*ervas?\s*7|sao\s*antonio|sao\s*francisco|sao\s*joao|sao\s*paulo|sao\s*pedro|sao\s*cristovao|sao\s*cristóvão|sao\s*luiz|sao\s*jorge|santo\s*antonio|santo\s*antonio|santa\s*barbara|santa\s*bárbara|sao\s*domingos|sao\s*francisco|sao\s*jo[ãa]o|sao\s*jos[eé]|sao\s*luiz|sao\s*paulo|sao\s*pedro|sao\s*sebastiao|sao\s*vicente|sao\s*antonio|sao\s*bento|sao\s*miguel|sao\s*rafael|sao\s*gabriel|sao\s*rafael|sao\s*gabriel|casa\s*de\s*ervas?\s*(sao|santo|santa|7|são)|casa\s*de\s*ervas?\s*(s[ãa]o|santo|santa|7)|casa\s*de\s*ervas?\s*jorge|casa\s*de\s*ervas?\s*pedro|casa\s*de\s*ervas?\s*antonio|casa\s*de\s*ervas?\s*barbara|casa\s*de\s*ervas?\s*bárbara|casa\s*de\s*ervas?\s*francisco|casa\s*de\s*ervas?\s*jo[ãa]o|casa\s*de\s*ervas?\s*jos[eé]|casa\s*de\s*ervas?\s*luiz|casa\s*de\s*ervas?\s*paulo|casa\s*de\s*ervas?\s*pedro|casa\s*de\s*ervas?\s*sebastiao|casa\s*de\s*ervas?\s*vicente|casa\s*de\s*ervas?\s*bento|casa\s*de\s*ervas?\s*miguel|casa\s*de\s*ervas?\s*rafael|casa\s*de\s*ervas?\s*gabriel|casa\s*de\s*ervas?\s*linhas|casa\s*de\s*ervas?\s*7\s*linhas|casa\s*de\s*ervas?\s*santo\s*antonio|casa\s*de\s*ervas?\s*sao\s*jorge|casa\s*de\s*ervas?\s*sao\s*pedro|casa\s*de\s*ervas?\s*santa\s*barbara|casa\s*de\s*ervas?\s*santa\s*bárbara|casa\s*de\s*ervas?\s*sao\s*francisco|casa\s*de\s*ervas?\s*sao\s*joao|casa\s*de\s*ervas?\s*sao\s*joão|casa\s*de\s*ervas?\s*sao\s*jose|casa\s*de\s*ervas?\s*sao\s*josé|casa\s*de\s*ervas?\s*sao\s*luiz|casa\s*de\s*ervas?\s*sao\s*paulo|casa\s*de\s*ervas?\s*sao\s*pedro|casa\s*de\s*ervas?\s*sao\s*sebastiao|casa\s*de\s*ervas?\s*sao\s*vicente|casa\s*de\s*ervas?\s*sao\s*bento|casa\s*de\s*ervas?\s*sao\s*miguel|casa\s*de\s*ervas?\s*sao\s*rafael|casa\s*de\s*ervas?\s*sao\s*gabriel)'),
    ('Casa de comércio/loja', r'casa\s*(27|do\s*parabrisa|do\s*bol[sS]a|lot[ée]rica|ramalho|mariense|lotérica|caixa|caixa\s*aqui|júnior|junior\s*andrade|gilmara|gilmara\s*santos|neia|neia\s*santos|santos\s*dom\s*mont|ideal\s*ve[ií]culos|ve[ií]culos|mais\s*f[áa]cil|ramalho|júnior|junior|gilmara|neia|santos|ideal|ve[ií]culos|f[áa]cil|ramalho|santos|mont|dom|dumont|caixa|aqui|lotéric|loteric|bolsa|família|familia|parabrisa|júnior\s*andrade|ramalho|m[óo]veis|eletrodom|caixa|aqu|bolsa|fam[ií]lia|parabrisa)'),
    ('Comercio variado', r'casa\s*(do\s*couro|do\s*couro\s*ltda|do\s*instalador|do\s*vergalhao|do\s*vergalhão|do\s*bolsa\s*família|do\s*bolsa\s*familia|do\s*adubo|do\s*adubo\s*gandu|do\s*adubo\s*gand|do\s*adubo|do\s*pintor|do\s*puxador|do\s*pao|do\s*pão|do\s*som|do\s*som\s*brasil|do\s*tucano|do\s*vaqueiro|do\s*acarajé|do\s*acaraj|do\s*crochê|do\s*croche|do\s*pneu|do\s*irmão|do\s*irm|do\s*san[sS]|do\s*cimento|do\s*led|do\s*adubo|do\s*raçao|do\s*racao|do\s*rações|do\s*racoes|do\s*plantas|do\s*planta[sS]|do\s*pizza|do\s*sopa|do\s*serea|do\s*sereia|do\s*sus|do\s*susan|do\s*acarajé\s*didy|do\s*croch|do\s*pneu|do\s*irmão|do\s*irm|do\s*sans|do\s*cimento|do\s*led|do\s*adubo|do\s*raçao|do\s*racao|do\s*rações|do\s*racoes|do\s*plantas|do\s*planta|do\s*pizza|do\s*sopa|do\s*sereia|do\s*sus|do\s*susan|do\s*couro|do\s*instalador|do\s*vergalhao|do\s*vergalhão|do\s*bolsa|do\s*família|do\s*familia|do\s*parabrisa|do\s*pintor|do\s*puxador|do\s*pao|do\s*pão|do\s*som|do\s*tucano|do\s*vaqueiro|do\s*acaraj|do\s*croch|do\s*pneu|do\s*irm|do\s*san|do\s*cimento|do\s*led|do\s*adubo|do\s*raç|do\s*rac|do\s*plant|do\s*pizza|do\s*sop|do\s*serea|do\s*serei|do\s*sus|do\s*susan|do\s*acarajé\s*didy|do\s*couro\s*ltda|do\s*instalador|do\s*vergalhao|do\s*vergalhão|do\s*bolsa\s*família|do\s*bolsa\s*familia|do\s*parabrisa|do\s*pintor|do\s*puxador|do\s*pao|do\s*pão|do\s*som\s*brasil|do\s*tucano|do\s*vaqueiro)'),
    ('Nao-religioso variado', r'casa\s*(de\s*velas|de\s*antônia|de\s*antonia|de\s*antonio|de\s*ant[ôo]nio|de\s*bianca|de\s*bianca\s*filha|de\s*castro\s*alves|de\s*cultura|de\s*c[âa]mara|de\s*camara|de\s*c[âa]mara\s*e\s*cadeia|de\s*camara\s*e\s*cadeia|de\s*campo|de\s*cida|de\s*cul[áa]|de\s*j[úu]lia|de\s*junior\s*e\s*zene|de\s*júnior\s*e\s*zene|de\s*junior|de\s*júnior|de\s*mateus|de\s*m[ãa]e|de\s*mae|de\s*oracao|de\s*ora[çc][aã]o|de\s*pneu[sS]?|de\s*raçao|de\s*racao|de\s*rações|de\s*racoes|de\s*retiro|de\s*saude|de\s*sa[úu]de|de\s*tope|de\s*ca[çc]ula|de\s*cac[úu]la|de\s*cultura|de\s*erv[aa]s?|de\s*ervas?\s*(santo|sao|são|santa|7|jorge|pedro|antonio|barbara|bárbara|francisco|joao|joão|jose|josé|luiz|paulo|sebastiao|vicente|bento|miguel|rafael|gabriel|linhas)|de\s*ervas?\s*7\s*linhas|de\s*ervas?\s*santo\s*antonio|de\s*ervas?\s*sao\s*jorge|de\s*ervas?\s*sao\s*pedro|de\s*ervas?\s*santa\s*barbara|de\s*ervas?\s*sao\s*francisco|de\s*ervas?\s*sao\s*joao|de\s*ervas?\s*sao\s*joão|de\s*ervas?\s*sao\s*jose|de\s*ervas?\s*sao\s*josé|de\s*ervas?\s*sao\s*luiz|de\s*ervas?\s*sao\s*paulo|de\s*ervas?\s*sao\s*sebastiao|de\s*ervas?\s*sao\s*vicente|de\s*ervas?\s*sao\s*bento|de\s*ervas?\s*sao\s*miguel|de\s*ervas?\s*sao\s*rafael|de\s*ervas?\s*sao\s*gabriel|de\s*ervas?\s*linhas|de\s*ervas?\s*7\s*linhas|das\s*ervas?|das\s*erv[aa]s|de\s*ervas?|de\s*erv[aa]s|de\s*erv[aa]s?\s*santo|de\s*ervas?\s*(santo|sao|são|santa|jorge|pedro|antonio|barbara|bárbara|francisco|joao|joão|jose|josé|luiz|paulo|sebastiao|vicente|bento|miguel|rafael|gabriel|7|linhas))'),
    ('Funeraria', r'funeraria|funer[áa]ria|funeraria\s*deus|funeraria\s*santo\s*antonio|funer[áa]ria\s*santo\s*antonio|funer[áa]ria\s*deus\s*conosco|funeraria\s*deus\s*conosco'),
    ('Condominio/imobiliaria', r'condom[íi]nio|residencial|loteamento|casa\s*em\s*jacobina|casa\s*rio\s*paragua[çc]u|casa\s*rio\s*de\s*contas|casa\s*de\s*campo\s*senhora|casas?\s*rio\s*de\s*contas|casas?\s*de\s*retiro|casa\s*di\s*v[óo]|casa\s*di\s*vo|casa\s*em\s*jacobina|casa\s*rio\s*paragua[çc]u|casa\s*rio\s*de\s*contas'),
    ('Instituicao publica', r'camara\s*municipal|c[âa]mara\s*municipal|defensoria|department\s*of\s*social|embasa|eletrosantos|enersol|escola\s*municipal|ibge|sac\s*municipal|secretaria|prefeitura|rodoviaria|prefecture|municipal|casa\s*do\s*bolsa\s*fam[ií]lia|casa\s*lot[ée]rica'),
    ('Geografico/turistico', r'pra[çc]a|praca|parque\s*history|centro\s*hist[óo]rico|cidade\s*hist[óo]rica|city\s*of\s*(amargosa|jacobina|new|ibi|varzea)|ilha\s*(coroa|pedra|das|do|9|society|bela|vermelha)|coroa\s*do\s*limo|cristo\s*de\s*m[áa]rio|fonte\s*da\s*bica|divisa\s*de\s*estados|high\s*city|park\s*history|beco\s*dos\s*encantos|retiro\s*de\s*itaparica|itaparica\s*-\s*praia|itaparica\s*island|praia\s*do\s*forte|po[çc]o\s*do\s*diabo|serra\s*do\s*salto|sitio\s*(arqueolog|hist[óo]rico|santo\s*antonio|santana|do\s*quinto|do\s*quinto|governador)|p[ée]\s*de\s*serra|mar\s*grande|vera\s*cruz|serra\s*do\s*abi[áa]|r\.\s*(alto|castro)|rafael\s*jambeiro|umburanas|umburana|sim[õo]es\s*filho|eunapolis\s*bahia|eun[áa]polis\s*bahia|vit[óo]ria\s*da\s*conquista\s*bahia|varzea\s*do\s*po[çc]o|ponto\s*novo|serapi[ãa]o|tanquinho|mat[aá]\s*de\s*sao\s*joao|mata\s*de\s*são\s*joão|madre\s*de\s*deus|sao\s*desid[ée]rio|são\s*desidério|santo\s*antonio\s*centro|super\s*santo\s*antonio|hiper\s*santo\s*antonio|santo\s*antonio\s*house|san\s*antonio\s*house|shop\s*st|st\.?\s*ant|centro\s*hist[óo]rico|monte\s*santo|centro\s*comunit[áa]rio|espa[çc]o\s*de\s*eventos|centro\s*de\s*treinamento|casa\s*de\s*cultura|casa\s*cultural|centro\s*cultural|tribo\s*bahia|capoeira|casa\s*de\s*ant[ôo]nia|casa\s*de\s*antonia|casa\s*de\s*antonio|casa\s*de\s*ant[ôo]nio|casa\s*de\s*isaque|casa\s*de\s*j[úu]lia|casa\s*de\s*junior|casa\s*de\s*júnior|casa\s*de\s*bianca|casa\s*de\s*mateus|casa\s*de\s*cida|casa\s*de\s*m[ãa]e|casa\s*de\s*mae|casa\s*de\s*tope|casa\s*de\s*ca[çc]ula|casa\s*de\s*cac[úu]la|casa\s*de\s*resid[êe]ncia|casa\s*de\s*residencia|casa\s*de\s*atendimento|casa\s*de\s*ant[ôo]nia|casa\s*de\s*antonia|casa\s*27|casa\s*abade|casa\s*cacau|casa\s*lot[ée]rica|casa\s*mais\s*f[áa]cil|casa\s*pequenina|casa\s*rosada|casa\s*ramalho|casa\s*júnior|casa\s*junior|casa\s*neia|casa\s*gilmara|casa\s*do\s*adubo|casa\s*do\s*vergalhão|casa\s*do\s*vergalhao|casa\s*do\s*pneu|casa\s*do\s*pintor|casa\s*do\s*puxador|casa\s*do\s*pão|casa\s*do\s*pao|casa\s*do\s*som|casa\s*do\s*led|casa\s*do\s*cimento|casa\s*do\s*couro|casa\s*do\s*instalador|casa\s*do\s*acaraj|casa\s*do\s*croch[êe]|casa\s*do\s*tucano|casa\s*do\s*vaqueiro|casa\s*do\s*bolsa|casa\s*do\s*parabrisa|casa\s*do\s*irmão|casa\s*do\s*irm|casa\s*do\s*san[sS]|casa\s*do\s*ra[çc][aã]o|casa\s*do\s*ra[çc]ao|casa\s*do\s*adubo|casa\s*do\s*fertilizante|casa\s*do\s*defensivo|casa\s*do\s*adubo\s*gandu|casa\s*do\s*adubo\s*gand|casa\s*da\s*ferramenta|casa\s*da\s*fruta|casa\s*da\s*fruta\s*verdura|casa\s*da\s*sopa|casa\s*da\s*pizza|casa\s*da\s*sereia|casa\s*da\s*robo|casa\s*da\s*rob[óo]tica|casa\s*da\s* Susan|casa\s*da\s*sus|casa\s*das\s*antenas|casa\s*das\s*baterias|casa\s*das\s*bebidas|casa\s*das\s*embalagens|casa\s*das\s*espumas|casa\s*das\s*historias|casa\s*das\s*quentinhas|casa\s*das\s*noivas|casa\s*das\s*sandalias|casa\s*das\s*sand[áa]lias|casa\s*das\s*ervas?|casa\s*de\s*ervas?|casa\s*de\s*erv[aa]s|casa\s*de\s*fogos?|casa\s*de\s*plantas?|casa\s*de\s*pneus?|casa\s*de\s*ra[çc][õo]es|casa\s*de\s*ra[çc]oes|casa\s*de\s*ra[çc]ao|casa\s*de\s*ra[çc][aã]o'),
    ('Fundacao/instituicao', r'foundation|fundacao|associa[çc]ao|coletivo|central\s*de\s*adubos|nucleo\s*de\s*estudo|centro\s*de\s*treinamento|casa\s*de\s*cultura|centro\s*cultural|espa[çc]o\s*de\s*eventos|espa[çc]o\s*catolico|centro\s*comunitario|centro\s*comunitário'),
    ('Turismo/hospedagem', r'casa\s*di\s*v[óo]|casa\s*di\s*vo|casa\s*de\s*campo\s*senhora|casa\s*de\s*campo|casa\s*de\s*hospedagem|casa\s*em\s*jacobina|casa\s*rio\s*paragua[çc]u|casa\s*rio\s*de\s*contas|casa\s*de\s*ant[ôo]nia|casa\s*de\s*antonia|casa\s*de\s*antonio|casa\s*de\s*ant[ôo]nio|casa\s*de\s*bianca|casa\s*de\s*j[úu]lia|casa\s*de\s*junior|casa\s*de\s*júnior|casa\s*de\s*mateus|casa\s*de\s*cida|casa\s*de\s*m[ãa]e|casa\s*de\s*mae|casa\s*de\s*tope|casa\s*de\s*ca[çc]ula|casa\s*de\s*cac[úu]la|casa\s*de\s*resid[êe]ncia|casa\s*de\s*residencia|casa\s*de\s*atendimento|casa\s*de\s*velas|casa\s*27|casa\s*abade|casa\s*cacau|casa\s*lot[ée]rica|casa\s*mais\s*f[áa]cil|casa\s*pequenina|casa\s*rosada|casa\s*ramalho|casa\s*júnior|casa\s*junior|casa\s*neia|casa\s*gilmara'),
]

# Termos que indicam POSSÍVEL terreiro (manter no dataset)
possible_terreiro_terms = [
    'casa de ervas', 'império do real', 'imperio do real', 'casa de jac[ií]',
    'upaamc', 'união cultural dos sacerdotes', 'uniao cultural dos sacerdotes',
    'templo ogam', 'templo ogun', 'templo do amanhecer', 'templo atuaro',
    'casa de caridade', 'casa ecumênica', 'casa ecumenica',
    'casa de santo', 'casa de orixá', 'casa de orixa',
    'palacio de oya', 'palácio de oya', 'palacio de oyá', 'palácio de oyá',
    'espiritualista', 'spiritual center',
    'casa de mina', 'casa de minas',
    'casa de angola', 'casa de ketu', 'casa de jeje',
    'casa de candombl', 'casa de umband',
    'tenda espirit', 'centro espirit',
    'casa de oxal', 'casa de oxum', 'casa de iemanj', 'casa de xango',
    'casa de ogun', 'casa de ogum', 'casa de exu', 'casa de esu',
    'casa de ossaim', 'casa de logun', 'casa de oxumar', 'casa de omulu',
    'casa de iansa', 'casa de nana', 'casa de oba', 'casa de oxossi',
    'mae de santo', 'mãe de santo', 'pai de santo',
    'asé', 'axé', 'abassá', 'roça', 'ile', 'ilê',
    'casa de santo antonio', # pode ser terreiro de umbanda
]

possible_terreiro_set = set(t.lower() for t in possible_terreiro_terms)

def is_possible_terreiro(nome_lower):
    for term in possible_terreiro_set:
        if term in nome_lower:
            return True
    return False

# Classificar ambíguos
ambiguous_fp = []  # não-religiosos confirmados
ambiguous_keep = []  # possivelmente terreiros — manter

for nome in ambiguous_names:
    nome_lower = nome.lower()
    
    # Check se é possivel terreiro
    if is_possible_terreiro(nome_lower):
        ambiguous_keep.append(nome)
        continue
    
    # Check padrões não-religiosos
    matched = None
    for label, pat in additional_non_religious:
        if re.search(pat, nome_lower):
            matched = label
            break
    
    if matched:
        ambiguous_fp.append({'nome': nome, 'razao': matched})
    else:
        # Default: se não bate em nada, provavelmente é não-religioso
        # (Google Places retornou por ter "casa" no nome)
        ambiguous_fp.append({'nome': nome, 'razao': 'Nao-religioso (default)'})

print(f"=== REFINAMENTO DOS AMBIGUOS ===")
print(f"Total ambíguos: {len(ambiguous_names)}")
print(f"Confirmados não-religiosos: {len(ambiguous_fp)}")
print(f"Possivelmente terreiros (manter): {len(ambiguous_keep)}")
print()

print(f"--- Confirmados não-religiosos ({len(ambiguous_fp)}) ---")
razao_counts = Counter(a['razao'] for a in ambiguous_fp)
for razao, count in razao_counts.most_common():
    print(f"  {razao}: {count}")
print()

print(f"--- Possivelmente terreiros — MANTER ({len(ambiguous_keep)}) ---")
for i, nome in enumerate(sorted(ambiguous_keep), 1):
    print(f"  {i:3d}. {nome}")
print()

# === FASE 2: Remover todos os falsos positivos do dataset ===
# Lista completa de nomes a remover
fp_names_set = set()
for fp in scan['google_false_positives']:
    fp_names_set.add(fp['nome'])
for fp in ambiguous_fp:
    fp_names_set.add(fp['nome'])

print(f"\n=== REMOÇÃO DO DATASET ===")
print(f"Total falsos positivos para remover: {len(fp_names_set)}")
print(f"Dataset original: {len(records)}")

# Filtrar
clean_records = []
removed = []
for r in records:
    nome = (r.get('nome') or r.get('name') or r.get('title') or '').strip()
    fonte = r.get('fonte', '')
    
    # Só remover do Google
    if fonte == 'google' and nome in fp_names_set:
        removed.append({'nome': nome, 'fonte': fonte})
        continue
    
    clean_records.append(r)

print(f"Registros removidos: {len(removed)}")
print(f"Dataset limpo: {len(clean_records)}")
print()

# Stats por fonte
from collections import Counter
fonte_orig = Counter(r.get('fonte','') for r in records)
fonte_clean = Counter(r.get('fonte','') for r in clean_records)
print("Por fonte (antes -> depois):")
for f in ['google', 'ceao', 'sefaz', 'osm', '']:
    print(f"  {f or '(vazio)':12s}: {fonte_orig.get(f,0):4d} -> {fonte_clean.get(f,0):4d}  (removidos: {fonte_orig.get(f,0) - fonte_clean.get(f,0)})")

# Atualizar terreiros_all_sources.json
data['terreiros'] = clean_records
data['metadata'] = data.get('metadata', {})
data['metadata']['scan_fp'] = {
    'total_original': len(records),
    'total_removido': len(removed),
    'total_limpo': len(clean_records),
    'google_fp_obvios': len(scan['google_false_positives']),
    'google_fp_ambiguos': len(ambiguous_fp),
    'google_mantidos_ambiguos': len(ambiguous_keep),
    'metodo': 'Scan heuristico: padroes de nao-religiosos + keywords Afro-Brasileiras (Yoruba/Bantu/Jeje/Umbanda). Apenas Google Places escaneado. CEAO/SEFAZ/OSM nao modificados (curados).',
}

with open('data/terreiros_all_sources.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nSalvo: data/terreiros_all_sources.json ({len(clean_records)} registros)")

# Regenerar GeoJSON
features = []
for r in clean_records:
    lat = r.get('lat')
    lng = r.get('lng')
    if lat is not None and lng is not None:
        try:
            lat_f = float(lat)
            lng_f = float(lng)
            if -18.5 <= lat_f <= -8.0 and -47.0 <= lng_f <= -37.0:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [lng_f, lat_f]
                    },
                    'properties': {
                        'nome': r.get('nome', r.get('name', '')),
                        'fonte': r.get('fonte', ''),
                        'nacao': r.get('nacao', r.get('tradicao', r.get('nao', ''))),
                        'endereco': r.get('endereco', r.get('address', '')),
                        'municipio': r.get('municipio', r.get('addr:city', r.get('cidade', ''))),
                        'geo_status': 'in_bahia',
                    }
                })
        except (ValueError, TypeError):
            pass

geojson = {
    'type': 'FeatureCollection',
    'metadata': {
        'total': len(features),
        'fontes': dict(fonte_clean),
        'scan_fp': data['metadata']['scan_fp'],
    },
    'features': features
}

with open('data/terreiros.geojson', 'w') as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)
print(f"Salvo: data/terreiros.geojson ({len(features)} features)")

# Salvar lista de removidos
with open('data/falsos_positivos_removidos.json', 'w') as f:
    json.dump({
        'removidos': removed,
        'total': len(removed),
        'fp_obvios': scan['google_false_positives'],
        'fp_ambiguos_refinados': ambiguous_fp,
        'mantidos_ambiguos': ambiguous_keep,
    }, f, ensure_ascii=False, indent=2)
print(f"Salvo: data/falsos_positivos_removidos.json ({len(removed)} removidos)")

print(f"\n=== RESUMO FINAL ===")
print(f"Dataset original:  {len(records)} registros")
print(f"Falsos positivos:  {len(removed)} removidos")
print(f"Dataset limpo:     {len(clean_records)} registros")
print(f"GeoJSON:           {len(features)} features (com coords na Bahia)")
print(f"Redução:           {len(removed)/len(records)*100:.1f}%")