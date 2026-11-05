# Roteiro do Google Form — Ilê Axé Map

Formulário: "Solicitar alteração, inclusão ou exclusão no Ilê Axé Map"

## Configurações gerais
- Título: Ilê Axé Map — Solicitação de alteração, inclusão ou exclusão
- Descrição: "O Ilê Axé Map é um atlas acadêmico de terreiros de candomblé e espaços religiosos afro-brasileiros. Se você é liderança, membro ou representante de uma comunidade, ou identificou um erro, use este formulário. A exclusão não exige justificativa. Respostas em até 7 dias (exclusões) ou 30 dias (demais casos)."
- Coleta de e-mail: Não (opcional, ver pergunta 4)
- Limite de 1 resposta por pessoa: NÃO (não exigir login Google)
- Confirmação de envio: "Recebemos sua solicitação. Exclusões: até 7 dias. Alterações e inclusões: até 30 dias."

## Perguntas

1. **Tipo de solicitação** (obrigatória, múltipla escolha)
   - Excluir um terreiro do mapa
   - Alterar/corrigir informações de um terreiro
   - Incluir um terreiro no mapa
   - Outro

2. **Nome do terreiro como aparece no mapa** (opcional, resposta curta)
   Ajuda: "Deixe em branco se for inclusão ou não souber o nome exato."

3. **Localização — município e estado (UF)** (opcional, resposta curta)

4. **E-mail para resposta** (opcional, resposta curta, validação de e-mail)
   Ajuda: "Não é obrigatório. Sem e-mail, a alteração é aplicada e publicada no mapa, mas você não recebe confirmação individual."

5. **Você se identifica como** (opcional, múltipla escolha)
   - Liderança ou membro da comunidade
   - Familiar ou representante
   - Pesquisador(a)
   - Outra pessoa

6. **Descrição da solicitação** (resposta longa, obrigatória para alteração/inclusão)
   Ajuda: "Para exclusão, basta indicar o terreiro. Para alteração, diga o que deve mudar (nome, endereço, tradição, coordenada). Para inclusão, descreva o terreiro e a localização. Justificativa não é exigida para exclusão."

7. **Fonte da informação** (opcional, para inclusões)
   - Sou da comunidade
   - Conheço a comunidade
   - Registro público (site, CNPJ, jornal)
   - Outra

8. **Anexo/foto** (opcional, upload)
   Ajuda: "Opcional. Não envie documentos de identidade."

## Planilha de respostas (privada)
- Criar Google Sheets vinculado: "respostas-ile-axe-map" (PRIVADO, nunca publicar)
- Notificação por e-mail para leofn@ufba.br a cada resposta nova

## Fluxo de tratamento (interno)
- Exclusão: ocultar o registro na próxima compilação do GeoJSON; prazo 7 dias; sem exigência de justificativa; só verificar identidade em sinal claro de má-fé
- Alteração: aplicar a correção informada; prazo 30 dias
- Inclusão: verificar contra os critérios metodológicos (evidência religiosa, geocodificação com precisão forte); prazo 30 dias; se aprovada, entra com fonte "solicitação-comunitaria"
- Registrar toda decisão em data/solicitacoes_aplicadas.json (sem dados pessoais)

## E-mail alternativo
Assunto sugerido: "[Ilê Axé Map] solicitação — EXCLUSÃO/ALTERAÇÃO/INCLUSÃO — nome do terreiro"
