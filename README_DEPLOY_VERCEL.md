# Guia de Implantação do BrainStream na Vercel (Plano Gratuito)

Este guia explica passo a passo como colocar o **BrainStream** no ar usando apenas serviços gratuitos:

- **Vercel (Hobby):** hospedagem da aplicação Django (Python 3.12).
- **TiDB Cloud Starter:** banco de dados compatível com MySQL.
- **Supabase Storage:** armazenamento persistente das fotos de perfil (avatares) via API S3.
- **Google OAuth 2.0:** login com contas Google.
- **Google Gemini:** funcionamento do Tutor Enéas.

> **Importante:** nunca coloque senhas, tokens ou arquivos `.env` reais no GitHub. Todas as credenciais devem ser cadastradas nas **Environment Variables** da Vercel (ou no `.env` local, ignorado pelo `.gitignore`).

---

## 1. Criar o banco de dados no TiDB Cloud Starter

1. Acesse [tidbcloud.com](https://tidbcloud.com/) e crie uma conta gratuita (você pode entrar com GitHub ou Google).
2. No painel, clique em **Create Cluster**.
3. Escolha o plano **Starter** (gratuito, serverless).
4. Selecione o provedor **AWS** e a região mais próxima do Brasil ou dos EUA (ex.: `us-east-1` / Northern Virginia — costuma ter menor latência com a região padrão da Vercel).
5. Dê um nome ao cluster (ex.: `brainstream`) e clique em **Create**.
6. Aguarde o cluster ficar com status **Active** (leva menos de 1 minuto).

## 2. Obter credenciais do TiDB Cloud e configurar TLS

1. Abra o cluster `brainstream` e clique no botão **Connect**.
2. Em **Connect With**, escolha **General** (ou **Python / PyMySQL**).
3. Anote os valores exibidos:
   - **Host** (`DB_HOST`): algo como `gateway01.us-east-1.prod.aws.tidbcloud.com`
   - **Port** (`DB_PORT`): `4000`
   - **User** (`DB_USER`): algo como `2aBcDeFgHiJkLmN.root`
4. Clique em **Generate Password** para gerar a senha (`DB_PASSWORD`) e **copie-a imediatamente** (ela não será exibida novamente).
5. Crie o banco de dados `brainstream`:
   - No menu lateral do cluster, clique em **SQL Editor** (ou conecte via cliente MySQL) e execute:
     ```sql
     CREATE DATABASE IF NOT EXISTS brainstream CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```
6. **Certificado TLS (`DB_SSL_CA`):**
   - O TiDB Cloud exige conexão criptografada via TLS com validação de certificado e identidade.
   - **Na Vercel (Linux):** defina `DB_SSL_CA=/etc/ssl/certs/ca-certificates.crt`. O ambiente Linux da Vercel já inclui os certificados raiz que validam o TiDB Cloud.
   - **No seu computador (para rodar migrações e `createsuperuser`):**
     - No Linux (Ubuntu/Debian): use `/etc/ssl/certs/ca-certificates.crt`.
     - No macOS: use `/etc/ssl/cert.pem` (ou baixe o certificado CA exibido na tela **Connect** do TiDB Cloud).
     - No Windows: baixe o arquivo CA (`isrgrootx1.pem`) no link da tela **Connect** do TiDB Cloud, salve fora do repositório (ou com extensão `.pem`, que já está no `.gitignore`) e informe o caminho completo em `DB_SSL_CA`.

---

## 3. Criar o projeto no Supabase

1. Acesse [supabase.com](https://supabase.com/) e entre com sua conta gratuita.
2. Clique em **New Project**.
3. Escolha sua organização, dê o nome `brainstream`, defina uma senha forte para o banco do Supabase (não será usada pelo Django, pois o banco do projeto é o TiDB) e selecione a região **South America (São Paulo)** ou **East US (North Virginia)**.
4. Clique em **Create new project** e aguarde a criação concluir.
5. Anote o **Project Ref** (`SUPABASE_PROJECT_REF`): ele aparece na URL do painel (`https://supabase.com/dashboard/project/<PROJECT_REF>`) e também em **Project Settings → General → Reference ID**.

## 4. Criar o bucket público `avatars`

1. No menu lateral do Supabase, clique em **Storage**.
2. Clique em **New bucket**.
3. Em **Name of bucket**, digite exatamente: `avatars`.
4. Ative a opção **Public bucket** (obrigatório para que os navegadores carreguem as fotos de perfil por URL pública).
5. (Opcional) Em **Allowed MIME types**, você pode informar `image/webp` e limitar o tamanho a `2 MB` (o Django já valida e converte toda foto para WebP 256×256 sem EXIF antes de enviar).
6. Clique em **Save**.

## 5. Obter as credenciais S3 do Supabase

1. No menu lateral do Supabase, vá em **Project Settings → Storage**.
2. Role até a seção **S3 Access Keys**.
3. Anote:
   - **Endpoint** (`SUPABASE_S3_ENDPOINT`): algo como `https://<PROJECT_REF>.storage.supabase.co/storage/v1/s3`
   - **Region** (`SUPABASE_S3_REGION`): algo como `sa-east-1` ou `us-east-1`
4. Clique em **New access key**, dê uma descrição (ex.: `brainstream-vercel`) e clique em **Create access key**.
5. Copie imediatamente:
   - **Access Key ID** → `SUPABASE_S3_ACCESS_KEY`
   - **Secret Access Key** → `SUPABASE_S3_SECRET_KEY` (nunca exponha no frontend nem no GitHub).

---

## 6. Subir o projeto para o GitHub

Antes de enviar o código, confirme que nenhum segredo está sendo versionado:

```bash
git status
```

Verifique que `.env`, `*.pem`, `*.key`, `media/` e `staticfiles/` **não** aparecem na lista (todos já estão protegidos pelo `.gitignore`).

Depois de revisar as alterações:

```bash
git add .
git commit -m "Prepara infraestrutura do BrainStream para deploy na Vercel"
git push origin main
```

---

## 7. Importar o repositório na Vercel

1. Acesse [vercel.com](https://vercel.com/) e faça login com sua conta do GitHub (plano **Hobby**, gratuito).
2. Clique em **Add New… → Project**.
3. Localize o repositório **BrainStream** e clique em **Import**.

## 8. Selecionar o Root Directory correto

Na tela de configuração do projeto na Vercel:

1. Em **Root Directory**, clique em **Edit** e selecione a pasta:
   ```text
   brainstream
   ```
   *(É onde estão `manage.py`, `requirements.txt` e `.python-version`.)*
2. Em **Framework Preset**, a Vercel deve detectar **Django** automaticamente (ou deixe o padrão detectado).
3. Não é necessário criar `vercel.json` nem `api/index.py`: a Vercel detecta `manage.py`, usa Python `3.12` via `.python-version`, executa `collectstatic` automaticamente usando `STATIC_ROOT` e serve a aplicação WSGI.

---

## 9. Cadastrar as variáveis de ambiente na Vercel

Antes de clicar em **Deploy**, expanda **Environment Variables** e cadastre as variáveis abaixo (para o ambiente **Production** e, se desejar testar prévias, também **Preview**):

| Variável | Exemplo de valor | Observação |
| :--- | :--- | :--- |
| `DJANGO_SECRET_KEY` | *(chave aleatória de 50+ caracteres)* | Gere com: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `False` | Obrigatório `False` em produção (ativa cookies seguros e proteção de erros). |
| `DJANGO_ALLOWED_HOSTS` | `seu-projeto.vercel.app` | Opcional; se omitida, `.vercel.app` já é permitido automaticamente. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://seu-projeto.vercel.app` | Opcional; se omitida, `https://*.vercel.app` já é permitido automaticamente. |
| `DB_NAME` | `brainstream` | Nome do banco criado no TiDB Cloud. |
| `DB_USER` | `2aBcDeF.root` | Usuário exibido na tela Connect do TiDB Cloud. |
| `DB_PASSWORD` | *(senha gerada no TiDB)* | Senha gerada no passo 2. |
| `DB_HOST` | `gateway01.us-east-1.prod.aws.tidbcloud.com` | Host do TiDB Cloud. |
| `DB_PORT` | `4000` | Porta padrão do TiDB Cloud. |
| `DB_SSL_CA` | `/etc/ssl/certs/ca-certificates.crt` | Ativa TLS com validação de certificado e identidade na Vercel. |
| `SUPABASE_PROJECT_REF` | `abcdefghijklmnopqrst` | Reference ID do projeto Supabase. |
| `SUPABASE_S3_ENDPOINT` | `https://abcdefghijklmnopqrst.storage.supabase.co/storage/v1/s3` | Endpoint S3 do Supabase. |
| `SUPABASE_S3_REGION` | `sa-east-1` | Região exibida em Storage → S3. |
| `SUPABASE_S3_BUCKET` | `avatars` | Nome exato do bucket público criado no passo 4. |
| `SUPABASE_S3_ACCESS_KEY` | *(Access Key ID)* | Gerado no passo 5. |
| `SUPABASE_S3_SECRET_KEY` | *(Secret Access Key)* | Gerado no passo 5 (somente servidor). |
| `GOOGLE_CLIENT_ID` | `123456....apps.googleusercontent.com` | Obtido no passo 10. |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | Obtido no passo 10. |
| `GOOGLE_REDIRECT_URI` | `https://seu-projeto.vercel.app/accounts/google/callback/` | Substitua pelo domínio real após o primeiro deploy. |
| `AI_PROVIDER` | `gemini` | Provedor inicial do Tutor Enéas. |
| `AI_API_KEY` | `AIza...` | Chave criada no [Google AI Studio](https://aistudio.google.com/apikey). |
| `AI_MODEL` | *(deixe vazio)* | Vazio usa o padrão do projeto (`gemini-3.5-flash-lite`). |
| `AI_TIMEOUT` | `25` | Timeout conservador (em segundos) adequado ao ambiente serverless. |
| `AI_SEARCH` | `False` | Deixe `False` nos primeiros testes para respostas mais rápidas e previsíveis. |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Ou configure SMTP posteriormente se quiser enviar e-mails reais. |
| `DEFAULT_FROM_EMAIL` | `BrainStream <nao-responda@brainstream.local>` | Remetente padrão. |

Clique em **Deploy** e aguarde o build finalizar. Anote o domínio gerado pela Vercel (ex.: `https://brainstream.vercel.app`).

> Se você ainda não sabia o domínio exato antes do primeiro deploy, atualize `GOOGLE_REDIRECT_URI` (e opcionalmente `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS`) nas configurações da Vercel e clique em **Redeploy**.

---

## 10. Configurar o Google OAuth 2.0

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Selecione ou crie um projeto (ex.: `BrainStream`).
3. Vá em **APIs e serviços → Tela de permissão OAuth** (ou **Google Auth Platform → Branding / Audience**):
   - Tipo de usuário: **Externo**.
   - Preencha o nome do app (`BrainStream`), e-mail de suporte e e-mail do desenvolvedor.
   - Enquanto estiver em modo de teste, adicione os e-mails de quem vai testar (ou publique o app para permitir qualquer conta Google).
4. Vá em **APIs e serviços → Credenciais → Criar credenciais → ID do cliente OAuth**.
5. Tipo de aplicativo: **Aplicativo da Web**.
6. Em **Origens JavaScript autorizadas**, adicione:
   ```text
   https://SEU-DOMINIO.vercel.app
   ```
7. Em **URIs de redirecionamento autorizados**, adicione exatamente:
   ```text
   https://SEU-DOMINIO.vercel.app/accounts/google/callback/
   ```
   *(Atenção à barra `/` no final e ao `https://`.)*
8. Clique em **Salvar** e copie o **ID do cliente** (`GOOGLE_CLIENT_ID`) e a **Chave secreta do cliente** (`GOOGLE_CLIENT_SECRET`) para as variáveis de ambiente da Vercel.

---

## 11. Executar as migrações do banco de dados

As funções serverless da Vercel são somente leitura e não devem rodar migrações automaticamente a cada deploy. Execute as migrações **uma vez a partir do seu computador**, apontando para o TiDB Cloud:

1. No seu terminal local, ative seu ambiente virtual Python (com as dependências de `brainstream/requirements.txt` instaladas).
2. Exporte temporariamente as variáveis do TiDB (ou use um `.env` temporário local — **sem commitar**):
   ```bash
   cd brainstream
   export DJANGO_DEBUG=False
   export DJANGO_SECRET_KEY="sua-chave-secreta"
   export DB_NAME="brainstream"
   export DB_USER="seu-usuario.root"
   export DB_PASSWORD="sua-senha-tidb"
   export DB_HOST="gateway01.us-east-1.prod.aws.tidbcloud.com"
   export DB_PORT="4000"
   export DB_SSL_CA="/etc/ssl/certs/ca-certificates.crt"

   python manage.py migrate
   ```
   *(Isso cria todas as tabelas e popula os 12 temas iniciais da migração `0002_temas_iniciais`.)*

## 12. Criar o superusuário Django

Com as mesmas variáveis de ambiente apontando para o TiDB Cloud:

```bash
python manage.py createsuperuser
```

Informe o **e-mail**, o **nome completo** e a **senha**. Depois você poderá acessar `https://SEU-DOMINIO.vercel.app/admin/`.

---

## 13. Testar a aplicação após o deploy

Siga este roteiro no navegador após o deploy e as migrações:

1. **Página inicial e estáticos:** abra `https://SEU-DOMINIO.vercel.app/`. Confirme que CSS, JS, ícones Bootstrap Icons, fontes e SVGs carregam sem erros `404` no DevTools (aba Network).
2. **Cadastro e login tradicional:** crie uma conta em `/cadastro/`, faça logout e entre novamente em `/login/`. Confirme no DevTools (aba Application → Cookies) que `sessionid` e `csrftoken` estão marcados como `Secure`.
3. **Login com Google (HTTPS):** clique em **Continuar com Google**, autorize a conta e verifique o redirecionamento para `/painel/`.
4. **Avatares no Supabase Storage:**
   - Acesse `/perfil/` e envie uma imagem JPG ou PNG (até 2 MB).
   - Recarregue a página e inspecione a tag `<img>` do avatar: a URL deve ser `https://<PROJECT_REF>.supabase.co/storage/v1/object/public/avatars/avatares/<hash>.webp`.
   - Troque o avatar por outra foto e confirme no painel **Storage → avatars** do Supabase que a foto antiga foi removida e a nova foi gravada.
   - Teste a opção **Remover foto e usar as iniciais** e confirme que o arquivo é removido do bucket.
5. **Tutor Enéas (Gemini) e testes de latência:**
   - **Pergunta simples (Modo Guiado):** inicie uma sessão sobre um tema (ex.: *Fotossíntese*), envie uma resposta curta e meça o tempo de resposta (esperado: ~1–3 s com `gemini-3.5-flash-lite` e `AI_SEARCH=False`).
   - **Pergunta complexa:** envie uma explicação longa ou dúvida aprofundada e observe se responde bem abaixo de `AI_TIMEOUT=25`.
   - **Conversa com histórico:** troque várias mensagens seguidas (até 10–30 mensagens) e verifique se a latência permanece estável e se **Concluir Estudo** gera a síntese corretamente.
   - **Modos Quiz e Speedrun:** inicie um Quiz e um Speedrun e confirme que as 5 questões/afirmações são geradas pela IA (sem o aviso "simuladas").
   - **Erro de conexão / limite de requisições:** se a cota do Gemini for atingida (`429`) ou houver falha de rede, o Enéas deve exibir a mensagem amigável de indisponibilidade sem erro `500` e salvar a mensagem do estudante.
   - **Busca na web (teste separado):** somente depois dos testes acima passarem, se desejar testar grounding, altere `AI_SEARCH=True` na Vercel, faça Redeploy e teste um tema que peça fatos atuais (ex.: *Dados recentes de energia solar em 2026*). Se a latência subir demais ou a cota recusar, volte para `AI_SEARCH=False`.

---

## 14. Como monitorar os limites gratuitos dos serviços

Para evitar surpresas durante a apresentação da faculdade:

- **Vercel Hobby (gratuito):**
  - Acompanhe em **Dashboard → Usage** (uso de funções serverless, largura de banda e logs de execução).
  - O plano Hobby com **Fluid Compute** permite até **300 segundos** de duração máxima por função; ainda assim, mantemos `AI_TIMEOUT=25` para garantir boa experiência ao usuário e folga para retentativas.
- **TiDB Cloud Starter (gratuito):**
  - Acompanhe em **Cluster → Monitoring / Usage**: o plano Starter oferece armazenamento gratuito (5 GiB) e cota mensal de Request Units (RUs).
  - `CONN_MAX_AGE = 0` já está configurado para evitar acúmulo de conexões abertas a partir de funções serverless.
- **Supabase Free:**
  - Acompanhe em **Organization → Billing / Usage**: o plano gratuito inclui 1 GB de armazenamento de arquivos e cota mensal de egress. Como cada avatar é convertido para WebP 256×256 (~5–15 KB), cabem dezenas de milhares de fotos com folga.
  - Projetos gratuitos do Supabase podem pausar após 7 dias sem atividade: faça um acesso na semana anterior à apresentação para garantir que esteja ativo.
- **Google Gemini API (Free Tier):**
  - Acompanhe em [Google AI Studio](https://aistudio.google.com/) o limite de requisições por minuto (RPM) e por dia (RPD) do modelo `gemini-3.5-flash-lite`.
  - Mantenha `AI_SEARCH=False` se a cota de busca na web (grounding) for mais restrita que a cota padrão de geração de texto.
