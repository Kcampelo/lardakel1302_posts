# Publicação programada do Lar da Kel

A rotina local **Lar da Kel — publicar às 06h e 18h** está ativa no Codex até domingo, 4 de outubro de 2026, no fuso America/Sao_Paulo. O computador precisa ficar ligado, com internet e o aplicativo aberto. A execução começa nesses horários e a publicação depende do processamento da Meta.

## Fila atual

| Data | Hora | Tema |
|---|---|---|
| 02/10/2026 | 18:00 | Pizza de pão |
| 03/10/2026 | 06:00 | Despensa organizada |
| 03/10/2026 | 18:00 | Mousse de limão |
| 04/10/2026 | 06:00 | Jogos de cama |
| 04/10/2026 | 18:00 | Cuscuz com legumes |

Os três horários anteriores à ativação são reserva, sem publicação retroativa. O formato programado é carrossel de cinco páginas; Reels silenciosos e Stories estão disponíveis como adaptações.

## O que foi validado

- Conexão e identidade de @lardakel1302 pela API Instagram Login v25.0.
- Quarenta JPEGs públicos, verificados por tipo e hash SHA-256.
- A Meta aceitou e processou um carrossel completo de cinco imagens (status READY). Esse teste criou um contêiner, sem publicar.
- Cinco testes do publicador: tarefas futuras, horários passados, ativação, duplicação e reconciliação após resposta inconclusiva.
- Oito Reels H.264, 1080 × 1920, 40 segundos, sem faixa de áudio, com as mesmas cinco páginas na ordem.
- O executor ativo foi chamado fora dos horários da fila e não publicou nada.

## Como funciona

O arquivo `agendamento/fila.json` contém os temas autorizados, horários, legendas e URLs imutáveis de imagens em um commit do repositório público. O token fica somente no `.env` local.

A cada execução, `scripts/publicar_instagram.py run` confirma a conta, escolhe somente um item dentro da janela de até dez minutos após seu horário e prepara/publica o carrossel. Itens antigos não são compensados em outro horário. A rotina registra IDs e estados em `agendamento/estado/`, ignorado pelo Git. Uma resposta inconclusiva de publicação fica para reconciliação, sem repetir o envio.

Um contêiner READY não é um agendamento nativo do Instagram. Quem executa a publicação é a rotina local do Codex. Os registros de mídia publicada só surgem depois de a API confirmar a publicação.

## Pausar ou corrigir

- Pause a rotina na seção de agendamentos do aplicativo.
- Para desativar o publicador, altere `INSTAGRAM_PUBLISH_ENABLED=false` no `.env` e `enabled=false` em `agendamento/fila.json`.
- Se o token deixar de funcionar, renove-o no painel da Meta e atualize somente o arquivo local.
- Se houver bloqueio de rede ou solicitação de permissão na execução, conceda acesso apenas ao comando específico do publicador. A rotina avisa sobre falhas ou ações necessárias.

## Segurança dos arquivos públicos

O `.env`, os tokens e o estado local não foram enviados ao GitHub. Mídias, scripts e documentação estão no repositório público por autorização da usuária. Não mova credenciais para arquivos versionados nem para URLs de mídia.

## Referências

- [Publicação de conteúdo — Meta](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing/)
- [Agendamentos locais — documentação OpenAI](https://learn.chatgpt.com/docs/automations?surface=app)

