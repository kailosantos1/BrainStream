# Contas e autenticação

Código: `brainstream/accounts/` (model, forms, views, urls), `templates/accounts/`, `static/css/auth.css`, `static/js/auth.js`, `tests/test_accounts.py`.

## Decisões

- **Usuário customizado `Estudante`** (`AbstractUser` sem `username`, `first_name`, `last_name`; campo `nome`). `USERNAME_FIELD = 'email'`, `REQUIRED_FIELDS = ['nome']`. O e-mail é normalizado para minúsculas no manager, no `clean()` e nos formulários; `get_by_natural_key` usa `iexact`, então login é case-insensitive.
- **Views em função** (`cadastro`, `entrar`, `sair`) para cadastro/login/logout; recuperação de senha usa as class-based views nativas do Django com forms e templates próprios (`RecuperarSenhaForm`, `RedefinirSenhaForm`).
- Cadastro tem **um só campo de senha** (fiel à Figura 6); a força vem de `AUTH_PASSWORD_VALIDATORS`, aplicada em `_post_clean` para que a checagem de similaridade veja nome/e-mail.
- Após cadastro ou login: `?next=` seguro ou `LOGIN_REDIRECT_URL = core:painel`. `/painel/` é o painel do estudante (ver [[painel-e-metricas]]).
- `LANGUAGE_CODE = 'pt-br'` e `TIME_ZONE = 'America/Sao_Paulo'` para mensagens de validação em português.
- E-mail: `EMAIL_BACKEND` padrão é console (configurável no `.env`). Nos testes o Django usa locmem.

## Google

O botão "Continuar com Google" está **desativado com selo "Em breve"**. OAuth exigiria um pacote novo (ex.: django-allauth) e credenciais do Google Cloud, o que precisa de autorização (`AGENTS.md`). Ao implementar, reaproveitar `templates/accounts/_google.html`.

## Visual (Figuras 6 e 7 × identidade da landing)

As figuras usam botão em gradiente azul/violeta; a identidade da landing (decidida pelo usuário, ver [[landing-e-identidade-visual]]) proíbe violeta e gradiente decorativo. Ficou: estrutura, textos e conteúdo das figuras + tokens da landing (acento teal, Hanken Grotesk, superfícies). Ícones dos cartões de sessão em Bootstrap Icons, não emoji. Status nos cartões usam as cores de dado: Concluído = verde, Revisar = âmbar, Em progresso = azul. A coluna lateral some abaixo de 992px.

`base.html` ganhou os blocos `site_header`, `main` e `site_footer` para telas sem a navegação da landing.

## Armadilha: troca de AUTH_USER_MODEL

Um banco que já rodou `migrate` com `auth.User` dá `InconsistentMigrationHistory` (admin.0001 aplicado antes de accounts.0001). Em 2026-10-31 o banco local estava vazio e precisou ser recriado (drop + `migrate`). Nunca trocar o user model de novo em banco com dados sem plano de migração.

## Meu Perfil (`/perfil/`)

- View `accounts.views.perfil`: dois formulários na mesma página, distinguidos pelo campo oculto `acao` (`perfil` ou `senha`); cada um com PRG e `messages.success`. Formulário inválido devolve 400 e mantém o colapso de senha aberto (`senha_aberta`).
- `PerfilForm`: nome (espaços normalizados) e `avatar` opcional. A foto **sempre** é reprocessada com Pillow: rotação do EXIF aplicada, recorte central quadrado de 256 px, gravada como WebP com nome UUID em `avatares/`. Regravar descarta o EXIF (inclui GPS). Limites: 2 MB, até 6000 px de lado, só JPEG/PNG/WebP (formato real lido pelo Pillow, não pela extensão). Trocar ou remover a foto apaga o arquivo antigo.
- `TrocarSenhaForm` = `PasswordChangeForm` + validadores do Django; após salvar, `update_session_auth_hash` mantém a sessão.
- E-mail não é editável no perfil (é o login; mudar exigiria confirmação por e-mail).
- Rodapé da lateral (`{% rodape_perfil %}` em `painel_tags`) é o mesmo no painel, nas telas de estudo e no perfil: avatar (`{% avatar %}`, foto ou iniciais), nome, pontos totais, link para o perfil e o botão de sair (POST).
- Mídia: `MEDIA_ROOT = BASE_DIR / 'media'` (já no `.gitignore`); `static()` nas URLs só serve com DEBUG. Em produção, o servidor web precisa servir `/media/`. Pillow 11.3.0 é a última versão com Python 3.9.
- Desempenho: ver `metricas.desempenho` em [[painel-e-metricas]].

## Login com Google (OAuth 2.0 / OpenID Connect)

- Rotas `/accounts/google/login/` e `/accounts/google/callback/` (as demais rotas de conta ficam na raiz; o prefixo segue o `GOOGLE_REDIRECT_URI` pedido). Serviço em `accounts/google.py`, views em `accounts/views.py`.
- Sem `GOOGLE_CLIENT_ID` **e** `GOOGLE_CLIENT_SECRET`, o início avisa "Login com Google não configurado neste ambiente" e volta ao login. As telas de autenticação agora exibem `messages` (erro em vermelho, demais em azul).
- **Segurança:** `state` (32 bytes) e verificador PKCE (S256) guardados na sessão, de uso único (`pop`) e válidos por 10 min, comparados com `compare_digest`; `next` validado no início e de novo no retorno; troca do código e leitura do userinfo feitas pelo servidor via `httpx` (por isso não é preciso validar a assinatura do id_token); logs nunca registram código, token ou corpo das respostas.
- **Vínculo de conta:** busca por e-mail (iexact, normalizado). Só aceita `email_verified is True` — sem isso, uma conta Google com e-mail não verificado poderia entrar na conta de outra pessoa. Conta inativa é recusada. Conta existente não tem o nome sobrescrito.
- **Conta nova:** `create_user` sem senha (`has_usable_password() == False`), nome do Google. No perfil, essas contas veem "Definir senha" (`DefinirSenhaForm`, sem senha atual). Atenção: o "Esqueci a senha" do Django ignora contas sem senha utilizável, então elas só recuperam acesso pelo Google até definirem uma senha.
- **Foto:** se o estudante não tem avatar, baixa `picture` só de `https://*.googleusercontent.com`, sem seguir redirecionamentos, até 2 MB (troca `=s96-c` por `=s256-c`) e passa por `accounts/avatar.processar_avatar` (o mesmo do upload). Falha não impede o login.
- `httpx` agora é dependência direta (já vinha pelos SDKs de IA).
- **Configurar:** Google Cloud Console → credenciais → ID do cliente OAuth (Aplicativo da Web) → URI de redirecionamento autorizado = `GOOGLE_REDIRECT_URI` exatamente (padrão `http://localhost:8000/accounts/google/callback/`). Não verificado contra o Google real: o `.env` local ainda não tem credenciais.
