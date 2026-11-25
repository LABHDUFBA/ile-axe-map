# Roteiro do Google Form — Ilê Axé Map

**Formulário:** "Ilê Axé Map — completar, corrigir ou retirar um registro"

Este roteiro substitui a versão anterior (8 perguntas genéricas). O formulário agora reproduz **a mesma ficha campo a campo** que o mapa pré-preenche no link *"Completar estas informações"*: quem chega pelo painel de um registro encontra o nome, o ID e a localização já preenchidos e só completa o que sabe.

O e-mail (`ileaxemap@gmail.com`) continua valendo como caminho alternativo e para anexos.

---

## 1. Princípios do desenho

- **Um formulário, três caminhos.** O tipo de solicitação (completar / corrigir / retirar) é a primeira pergunta e ramifica as seções seguintes. A retirada não herda nenhuma pergunta sobre dados da casa.
- **Mesma ordem da mensagem de e-mail.** Os campos 1–12 abaixo seguem exatamente a numeração do corpo do `mailto` gerado por `contribLink()` no `index.html`. Um único roteiro mental para quem contribui, dois canais.
- **Só o que a pessoa souber.** Nenhum campo de conteúdo é obrigatório além do tipo de solicitação. "Não sei" e "não se aplica" são respostas válidas e explícitas.
- **Multivalorado onde o dado é multivalorado.** 1.504 registros (18,7%) declaram mais de uma tradição ou nação — vertente e nação são *caixas de seleção*, não escolha única.
- **Dado pessoal nunca vira campo público.** Nome de quem responde e nome da liderança entram como texto, ficam na planilha privada e nunca vão para o GeoJSON.
- **Nada de upload de documento.** Foto da fachada entra por e-mail, não pelo formulário (ver §9).

---

## 2. Configurações gerais

| Item | Valor |
|---|---|
| Título | Ilê Axé Map — completar, corrigir ou retirar um registro |
| Descrição | "O Ilê Axé Map é um atlas acadêmico de terreiros de candomblé e espaços religiosos afro-brasileiros. Se você é liderança, membro ou representante de uma comunidade, ou identificou um erro, use este formulário. Você não precisa preencher tudo: uma informação só já corrige o registro. A retirada não exige justificativa. Prazos: retirada em até 7 dias; correções e inclusões em até 30 dias." |
| Coleta de e-mail | **Não** (há campo próprio opcional na §5) |
| Limitar a 1 resposta | **Não** (não exigir login Google) |
| Embaralhar perguntas | Não |
| Barra de progresso | Sim (seções visíveis) |
| Confirmação de envio | "Recebemos sua contribuição. Retiradas: até 7 dias. Correções e inclusões: até 30 dias. Se você deixou um e-mail, respondemos por lá." |

---

## 3. Seção 1 — Registro (pré-preenchida pelo mapa)

Título da seção: **"Registro"**
Descrição: *"Estes campos vêm preenchidos pelo mapa. Se você chegou aqui sem passar por um registro, deixe em branco e descreva na pergunta 3."*

| # | Pergunta | Tipo | Obrigatória | Pré-preenchida |
|---|---|---|---|---|
| 1.0 | ID do registro no mapa | Resposta curta | Não | Sim (`entity_id`) |
| 1.1 | Nome como aparece no mapa | Resposta curta | Não | Sim (`nome`) |
| 1.2 | Município / UF no mapa | Resposta curta | Não | Sim (`municipio` / `uf`) |
| 1.3 | Fonte atual dos dados | Resposta curta | Não | Sim (`fonte_label`) |
| 1.4 | O que já está no mapa | Parágrafo | Não | Sim (tradição, nação, raiz, fundação, orixá) |

**Ajuda de 1.0:** "Preenchido automaticamente (formato `e_xxxxxxxxxxxx_UF`). Não altere — é o que permite aplicar a correção ao registro certo."
**Validação de 1.0:** expressão regular `^e_[0-9a-f]{12}_[A-Z]{2}$` (aceita vazio, para quem chegou direto).

> O Google Forms não tem campo oculto: estes campos aparecem, mas vêm preenchidos. A validação por regex impede que uma edição acidental grave a correção no registro errado.

---

## 4. Seção 2 — Tipo de solicitação

| # | Pergunta | Tipo | Obrigatória |
|---|---|---|---|
| 2 | O que você quer fazer? | Múltipla escolha | **Sim** |

Opções (cada uma ramifica para uma seção):

1. **Completar informações que faltam** → §6
2. **Corrigir uma informação errada** → §6
3. **Retirar este registro do mapa** → §7
4. **Incluir um terreiro que não está no mapa** → §6 (com 1.0 vazio)
5. **Outro assunto** → §6

---

## 5. Seção 3 — Quem responde

| # | Pergunta | Tipo | Obrigatória |
|---|---|---|---|
| 1 | Seu nome | Resposta curta | Não |
| 2 | Sua relação com a casa | Múltipla escolha | Não |
| 5.1 | E-mail para resposta | Resposta curta (regex de e-mail) | Não |

**Ajuda de 1:** "Não é publicado. Serve para registrar quem autorizou a informação e para responder."
**Opções de 2:** liderança · membro da casa · familiar ou representante · pesquisador(a) · vizinho(a) ou pessoa da comunidade · outra pessoa
**Ajuda de 5.1:** "Opcional. Sem e-mail, a correção é aplicada e publicada no mapa, mas você não recebe confirmação individual."

---

## 6. Seção 4 — Dados da casa (campos 3 a 12)

Título da seção: **"Dados do terreiro"**
Descrição: *"Preencha só o que você souber. Deixe em branco o que não se aplica. Os campos marcados (não publicado) não vão para o mapa."*

| # | Pergunta | Tipo | Obrigatória | Vai para o GeoJSON |
|---|---|---|---|---|
| 3 | Nome do terreiro, centro ou casa | Resposta curta | Não | `nome` |
| 4 | Nome da liderança responsável *(não publicado)* | Resposta curta | Não | **não** |
| 5 | Vertente religiosa | **Caixas de seleção** | Não | `tradicao` / `tradicoes_adicionais` |
| 6 | Nação, se houver | **Caixas de seleção** | Não | `nacoes[]` |
| 6b | Raiz ou família, se a casa declara | Resposta curta | Não | `raiz` |
| 7 | Ano de fundação | Resposta curta (número inteiro) | Não | `ano_fundacao` |
| 8 | Endereço ou link do Google Maps | Resposta curta | Não | `municipio`/`uf` + coordenada (revisada) |
| 9 | Ponto de referência *(uso interno)* | Resposta curta | Não | nenhum (insumo de conferência) |
| 10 | Redes sociais da casa | Resposta curta | Não | `redes_sociais[]` |
| 11 | O que está incorreto hoje na ficha | Parágrafo | Não | nenhum (insumo da correção) |
| 12 | Foto da fachada | Múltipla escolha | Não | `foto_thumb` (se enviada) |

**Opções de 5 (vertente):** Candomblé · Umbanda · Jurema · Jarê · Terecô / Tambor da Mata · Tambor de Mina · Batuque · Omoloko · Encantaria / Pena e Maracá · Xangô · Mesa Branca · Espiritismo / Kardecismo · Matriz africana (sem especificar) · **Não sei** · **Outra** (com campo "outra:", resposta curta acionada por "Outra")
**Ajuda de 5:** "Marque todas as que a casa reconhece. Muitas casas se identificam com mais de uma."

**Opções de 6 (nação):** Ketu/Queto · Angola · Jeje · Nagô · Ijexá · Cabinda · Oyó · Xambá · Caboclo · Bantu/Kongo · Efon · **Não tem nação** · **Não sei** · **Outra**
**Ajuda de 6:** "A nação é como a casa nomeia sua linhagem. Se a casa usa uma grafia própria, escreva em 'Outra' — o mapa preserva a forma da casa."
**Ajuda de 6b:** "Exemplos: Alaketo (dentro de Ketu), Savalu e Mahin (dentro de Jeje), Tedô (dentro de Nagô)."

**Ajuda de 7:** "Conforme a memória da casa. Se for estimativa, escreva 'aprox.' junto ao ano."
**Validação de 7:** número inteiro entre 1500 e 2026 (aceita texto livre com "aprox." → validar como texto e conferir na curadoria).

**Ajuda de 8:** "Pode ser o endereço, o bairro ou apenas o link do Google Maps do local. Não é necessário número."
**Ajuda de 9:** "Não é publicado. Ajuda a conferir a coordenada ('ao lado da praça', 'depois da igreja')."
**Ajuda de 10:** "Somente perfis institucionais da casa (Instagram, Facebook, site). Não envie perfil pessoal de terceiros."

**Opções de 12:** "Sim, envio a foto por e-mail depois" · "Não tenho foto" · "Podem usar a foto que já está no mapa" · "Não autorizo foto"

---

## 7. Seção 5 — Retirada (só para o caminho 3)

Título: **"Retirada do registro"**
Descrição: *"A retirada não exige justificativa. O registro sai da exibição em até 7 dias."*

| # | Pergunta | Tipo | Obrigatória |
|---|---|---|---|
| R1 | Confirmo que quero retirar este registro do mapa | Múltipla escolha (Sim / Não) | **Sim** |
| R2 | Quem solicita | Múltipla escolha (liderança ou membro · familiar ou representante · outra pessoa) | Não |
| R3 | Motivo (opcional) | Parágrafo | Não |
| R4 | Nome e contato para retorno *(não publicado)* | Resposta curta | Não |

Sem pergunta sobre tradição, nação, endereço ou foto: a retirada é assimétrica por desenho.

---

## 8. Seção 6 — Autorização e envio

| # | Pergunta | Tipo | Obrigatória |
|---|---|---|---|
| A1 | Autorizo o uso dessas informações no mapa | Múltipla escolha (Sim / Sim, exceto os itens marcados não publicados / Não) | **Sim** |
| A2 | Como você quer ser creditado(a) pela contribuição | Múltipla escolha (nome · "Comunidade do terreiro X" · anônimo) | Não |

**Ajuda de A1:** "Só publicamos o que for autorizado. Nome da liderança e seu contato nunca são publicados, mesmo com autorização."
Se A1 = "Não", a resposta é registrada, mas a informação **não** entra no mapa — e a pessoa é respondida por e-mail quando houver.

### Pré-visualização da confirmação
> "Recebemos sua contribuição. Retiradas: até 7 dias. Correções e inclusões: até 30 dias. Se você deixou um e-mail, respondemos por lá. Obrigado por cuidar deste mapa."

---

## 9. Pré-preenchimento por link (o que muda no mapa)

O botão do painel já monta uma mensagem de e-mail completa. Quando o formulário existir, o mesmo botão passa a abrir o Form com o bloco §3 preenchido.

**Como o Google Forms preenche:** cada pergunta tem um identificador próprio (`entry.NNNNNNNNN`), obtido em *⋮ → Obter link pré-preenchido*. A URL final é:

```
https://docs.google.com/forms/d/e/<ID>/viewform?usp=pp_url
  &entry.<ID_1_0>=e_7f3c2b66f0d0_BA
  &entry.<ID_1_1>=Rei%20de%20Macambira
  &entry.<ID_1_2>=Chame-Chame%20%2F%20BA
  &entry.<ID_1_3>=CEAO%2FUFBA
  &entry.<ID_1_4>=Tradi%C3%A7%C3%A3o%3A%20Candombl%C3%A9%20%C2%B7%20Na%C3%A7%C3%A3o%3A%20Keto%20Angola
  &entry.<ID_2>=Completar%20informa%C3%A7%C3%B5es%20que%20faltam
```

**Passos manuais (uma vez, no Console do Google):**
1. Criar o formulário com as seções §3–§8.
2. *Obter link pré-preenchido* → anotar os cinco `entry.*` da seção "Registro" e o da pergunta 2.
3. Preencher a tabela abaixo e me passar os IDs — eu ajusto o `index.html`.
4. Testar cada um dos cinco caminhos da pergunta 2 com um link real.

| Campo | Variável no `index.html` | `entry.*` |
|---|---|---|
| ID do registro | `p.entity_id` | *(a preencher)* |
| Nome | `getName(p)` | *(a preencher)* |
| Município/UF | `municipio` + `uf` | *(a preencher)* |
| Fonte | `getFonteLabel(p)` | *(a preencher)* |
| O que já está no mapa | `rotuloTrad` + `rotuloNacao` + `raiz` + ano + regente | *(a preencher)* |
| Tipo de solicitação | fixo por botão (`completar` / `corrigir` / `retirar`) | *(a preencher)* |

**O que muda no código:** `contribLink(p, kind)` já centraliza a montagem. Basta substituir o retorno `mailto:` por `CONTRIB_FORM_URL + '?usp=pp_url&entry...'` quando os IDs existirem — nenhum outro ponto do mapa chama o e-mail diretamente. Enquanto o formulário não existir, o `mailto` permanece como caminho válido.

---

## 10. Planilha de respostas (privada)

- Google Sheets vinculado: **`respostas-ile-axe-map`** — privado, nunca publicado, sem link público de download.
- Notificação por e-mail para `ileaxemap@gmail.com` a cada resposta.
- Colunas de trabalho na planilha (além das respostas brutas): `entity_id`, `aplicado_em`, `versao_aplicada`, `decisao` (`aplicado` / `recusado` / `pendente`), `motivo_recusa`, `origem_dado`.

---

## 11. Fluxo interno de tratamento

| Caminho | Prazo | Regra |
|---|---|---|
| Retirada | 7 dias | Aplicar sem exigir justificativa; verificar identidade só sob sinal claro de má-fé; registrar `geo_status=retirado_solicitacao` e ocultar — **nunca apagar** o registro |
| Correção | 30 dias | Aplicar a informação da comunidade; se contrariar fonte anterior, a comunidade prevalece e a divergência fica registrada |
| Inclusão | 30 dias | Avaliar contra os critérios metodológicos (evidência religiosa, coordenada de precisão forte, sem duplicata); se aprovada, entra com fonte `solicitacao-comunitaria` |
| Completar | 30 dias | Aplicar campo a campo; nunca preencher por dedução os campos que a pessoa deixou em branco |

Toda decisão vai para `data/solicitacoes_aplicadas.json` **sem dados pessoais**: só `entity_id`, campos alterados, data, e o identificador da resposta na planilha.

---

## 12. Privacidade e LGPD

- **Minimização:** só se pede o que tem uso declarado. Nome e contato existem para autorização e retorno, não para publicação.
- **Finalidade explícita** no topo do formulário: correção do mapa e retorno à pessoa; nada além disso.
- **Retenção:** respostas mantidas enquanto a informação estiver no mapa + 24 meses para comprovar a autorização; depois, anonimizar ou excluir.
- **Direito de retirada da própria contribuição:** pedido por e-mail, atendido em 7 dias, sem justificativa.
- **Nunca entram no GeoJSON:** nome de liderança, nome/contato de quem responde, endereço com número, CEP, telefone, e-mail.
- **Nunca publicados:** a planilha de respostas e os anexos recebidos por e-mail.

---

## 13. Checklist de publicação (quando o formulário existir)

- [ ] Criar o Form com as seções §3–§8 e a planilha privada (§10)
- [ ] Preencher os `entry.*` na tabela §9 e ajustar `contribLink()` no `index.html`
- [ ] Substituir o `mailto` do topbar ("Solicitações") pelo Form — **nos três pontos de uma vez**: `index.html` (topbar + painel Sobre), `colaborar.html` e o destaque de `metodologia.html` §8.1
- [ ] Trocar em `colaborar.html` a frase "em breve haverá um formulário online" pelo link direto
- [ ] Testar os cinco caminhos da pergunta 2 por celular (390px), incluindo o link pré-preenchido de um registro real
- [ ] Confirmar que a planilha **não** está pública e que nenhuma resposta aparece no site

---

## 14. Decisões em aberto

1. **Upload de foto no formulário:** o Google Forms exige login Google para anexos, o que contraria "não exigir login". Recomendação: manter o envio de foto por e-mail (opção 12 = "envio por e-mail depois"). Se você preferir o upload, o caminho é um formulário separado só para fotos, com aviso explícito de que é preciso conta Google.
2. **Inclusão de terreiro novo:** hoje compartilha a seção de dados com a correção. Se o volume crescer, vale uma seção própria com pergunta de evidência ("como você conhece esta casa?").
3. **Anti-spam:** sem login, o Forms não tem captcha. Se aparecer volume falso, habilitar "limitar a 1 resposta" como último recurso — antes disso, filtrar na planilha por `entity_id` inválido.
