# Política de contribuições

O Ilê Axé Map recebe correções, complementos e pedidos de inclusão e de retirada vindos
das próprias casas. Esta política diz o que chega, o que é publicado, o que nunca é
publicado, por quanto tempo o resto é guardado e como se pede para sair.

Página espelhada no site: `contribuir.html`.

## 1. Princípio

Quem decide o que aparece sobre uma casa é a casa. O mapa parte de dados públicos e de
fontes de terceiros; a ficha só se torna confiável quando a própria comunidade a confirma,
corrige ou completa. Por isso a contribuição não é um "comentário": é a via pela qual o
registro pode passar a ter autoridade própria.

## 2. O que pode ser pedido

| Pedido | O que acontece |
|---|---|
| **Completar** ficha existente | Campos públicos são preenchidos no registro |
| **Corrigir** informação errada | Campo apontado é substituído; o valor anterior fica registrado |
| **Incluir** casa que não está no mapa | Novo registro é criado, com coordenada a partir do endereço |
| **Retirar** registro | O registro sai do mapa em até 7 dias, **sem exigir justificativa** |

A retirada é um direito, não um pedido a ser avaliado. Não há negociação, não há
"verificar se é mesmo a casa" antes de tirar.

## 3. O que é publicado

Só o que descreve a casa:

- nome do terreiro, centro ou casa;
- tradição, nação, raiz/linhagem, linha, orixá regente;
- ano de fundação;
- município, UF, endereço (quando a casa autoriza), ponto de referência;
- redes sociais do terreiro (Instagram e similares);
- foto da fachada, quando enviada com autorização.

Toda ficha que passou por contribuição recebe a marca **"dados confirmados pela
liderança da casa"**, com a data. Quando é inclusão, a marca é **"registro incluído pela
própria casa"**.

## 4. O que nunca é publicado

- **nome civil** de quem respondeu;
- **nome da liderança responsável** (a casa é publicada; a pessoa não é obrigada a aparecer);
- e-mail, telefone, endereço residencial, CPF ou qualquer dado de contato;
- o texto integral da mensagem enviada;
- qualquer informação marcada como "não publicada" no formulário.

Esses itens servem apenas para responder a quem enviou e para resolver dúvidas sobre o
registro.

## 5. Onde o dado pessoal fica guardado

O repositório do mapa é **público** — tudo que está nele é visível, inclusive o histórico.
Por isso:

- dados públicos da ficha ficam no repositório, em `data/contribuicoes/*.json`;
- **dados pessoais não entram no repositório em nenhuma hipótese**, nem em arquivo morto;
- eles ficam fora do controle de versão, em `data/contribuicoes/_privado/`, que está no
  `.gitignore`, numa máquina administrada pela equipe;
- a mensagem original, se contiver dado pessoal, é apagada da caixa de e-mail depois do
  registro, ficando só a ficha anonimizada;
- quando o envio é feito pelo formulário do site, a submissão passa pelo **Formspree**, que
  atua como operador: recebe, filtra spam e encaminha por e-mail para a equipe. Ele guarda
  uma cópia por até 30 dias, prazo que o plano gratuito mantém. Nada é usado para outro fim,
  e o formulário não cria perfil de quem responde.

## 6. Por quanto tempo

| Item | Prazo |
|---|---|
| Ficha pública (dados da casa) | indefinido, enquanto a casa quiser |
| Dado pessoal de quem contribuiu | até 12 meses após a publicação, ou imediatamente se pedido |
| Mensagem original no e-mail | apagada em até 30 dias após o registro |
| Registro de que houve contribuição (data, canal, tipo) | indefinido — é o que sustenta a marca de confiabilidade |

O registro de que *houve* uma contribuição não é dado pessoal: é a procedência da ficha.

## 7. Como pedir retirada de dado pessoal

Basta escrever para **ileaxemap@gmail.com** dizendo o que deve sair. Não é preciso
justificar. O prazo é de até 7 dias, e o pedido se aplica também a dados publicados antes
desta política existir.

## 8. Contribuições recebidas antes desta política

Mensagens que chegaram por e-mail, WhatsApp ou redes sociais antes da existência do
formulário são tratadas com as mesmas regras, com uma diferença: nem sempre há
autorização explícita registrada. Nesses casos:

- o que for de fonte pública (CNPJ, CEAO, cadastros) já está publicado e não depende disso;
- o que veio de mensagem pessoal só entra no mapa com autorização identificável;
- sem autorização localizável, o material fica registrado como *pendente de confirmação*
  e não é publicado.

## 9. Como enviar agora

O formulário fica em `contribuir.html` do site. Se preferir, a mesma estrutura está
disponível por e-mail em **ileaxemap@gmail.com** — mas o formulário evita os três
problemas mais comuns das mensagens recebidas: campo faltando, autorização ausente e
informação sem saber a qual registro se refere.
