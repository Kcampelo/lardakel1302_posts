# Configurar acesso e agendamento

## Situação atual

Atualizado em 02/10/2026: executor implementado, mídias públicas validadas e rotina local ativa no Codex às 06h e 18h até 04/10/2026. Cinco publicações futuras. Consulte AGENDAMENTO_ATIVO.md para o calendário, validações e operação. O computador deve ficar ligado, com internet e o aplicativo aberto. Nenhuma publicação ocorreu durante os testes; a Meta confirmou a preparação de um carrossel de cinco páginas.

## 1. Preparar a conta

Use uma conta profissional do Instagram (Empresa ou Criador). Para este projeto vamos usar **Instagram API with Instagram Login**, sem misturar tokens e permissões do fluxo Facebook Login. Confira a elegibilidade específica para Stories no fluxo escolhido; não presuma que todo formato está disponível para toda conta.

## 2. Criar e configurar o aplicativo Meta

Entre em https://developers.facebook.com/apps/ e crie um app com o caso de uso de Instagram. Os nomes das telas podem variar. Escolha a configuração com Instagram Login.

Adicione sua conta profissional à configuração de testes/contas do app e aceite o convite quando solicitado. Contas com função no app podem testar com acesso padrão; para atender contas externas, pode ser necessário acesso avançado, revisão e requisitos adicionais da Meta.

Conceda as permissões **instagram_business_basic** e **instagram_business_content_publish**. Não solicite permissões de mensagens para este uso.

## 3. Obter os valores do .env

Abra o .env no editor e preencha somente no seu computador:

| Campo | Onde obter / finalidade |
|---|---|
| INSTAGRAM_USER_ID | ID numérico da conta profissional retornado pela configuração/API do Instagram; não é o @ nem o ID do app. |
| INSTAGRAM_ACCESS_TOKEN | Token do usuário Instagram autorizado para essa conta e para publicação. Use o fluxo de geração/teste oferecido no painel ou OAuth oficial. |
| META_API_VERSION | Versão suportada selecionada no painel e documentação do app. |
| INSTAGRAM_APP_ID | ID do app Instagram mostrado na configuração do produto. |
| INSTAGRAM_APP_SECRET | Segredo do app Instagram; necessário para operações do fluxo OAuth, não é a senha da conta. |
| INSTAGRAM_REDIRECT_URI | URL HTTPS de callback registrada exatamente no app, caso implemente OAuth. O callback ainda precisa ser implementado e hospedado. Não invente uma URL. |
| INSTAGRAM_TOKEN_EXPIRES_AT | Expiração efetiva informada pela Meta. Tokens precisam de renovação; não são credenciais permanentes. |
| MEDIA_BASE_URL | Endereço HTTPS da hospedagem que servirá as imagens e vídeos finais. |

Se usar um token de teste disponibilizado no painel, siga a validade e as condições mostradas nele. Para uso contínuo, implemente a troca/renovação de tokens conforme o fluxo oficial. Não envie tokens ou segredos no chat.

## 4. Hospedar a mídia

A Meta precisa conseguir baixar cada arquivo final por URL acessível, sem login ou cookies. Um caminho C:/REPO/... não serve. Pode ser armazenamento de objetos ou servidor HTTPS. URLs assinadas precisam continuar válidas durante todo o processamento.

Prepare os arquivos segundo os requisitos atuais da API: imagens para publicação precisam de formato aceito (JPEG no fluxo de publicação de imagens), e Reels precisam atender às especificações de vídeo. Os PNGs gerados devem ser convertidos para JPEG antes do envio quando necessário. Hospede somente a mídia a publicar, nunca o .env.

## 5. Conectar o agendador

Depois de preencher os dados, diga ao agente: **“Configure e teste a conexão do Instagram usando o .env local, sem exibir os segredos.”** Informe também os dias e horários desejados.

A integração ainda deverá ser implementada e validada: conferir a conta, preparar/hospedar a mídia, salvar uma fila com data e hora, criar os contêineres da API perto do horário da publicação, aguardar o processamento e chamar media_publish. Criar um contêiner antecipadamente não equivale a agendar um post no Instagram.

O executor precisa rodar no horário previsto, em computador ligado ou servidor. Deve registrar o ID publicado, impedir duplicações e tratar falhas ambíguas antes de tentar novamente. Não instalar rotina nem habilitar publicação antes de validar credenciais, hospedagem e calendário. INSTAGRAM_PUBLISH_ENABLED permanece false até essa etapa; atualmente é apenas configuração reservada, não uma proteção implementada em código.

## Referências oficiais

- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/content-publishing
- Coleção oficial Meta: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api

## Atualização de 01/10/2026

Conexão de leitura validada para @lardakel1302 e ID da conta corrigido no .env. A permissão de publicação ainda não foi validada por uma publicação de teste. A usuária definiu dois temas diários, às 06:00 e 18:00 (America/Sao_Paulo): dicas pela manhã e receitas à noite, com lanches e sobremesas nas noites de sexta e sábado. O lote de 01 a 04/10 está em entregas/galeria-2026-10-01-a-04.html e o calendário local em agendamento/calendario-2026-10-01-a-04.json. Nenhum item está efetivamente agendado. O item de 01/10 às 06:00 é reserva por horário já passado. Ainda faltam hospedagem de mídia e executor.
