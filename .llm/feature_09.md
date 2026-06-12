# Feature 09 — Dashboard no Streamlit

## Contexto

As Features 06, 07 e 08 geram o coração preditivo do projeto:

```text
modelos Poisson
função de previsão de partida
simulação Monte Carlo
gold_probabilidades_copa
```

A Feature 09 transforma esses resultados em um produto visual usando Streamlit.

O app deve permitir que qualquer pessoa explore as probabilidades da Copa 2026, rode uma simulação ao vivo e teste confrontos específicos entre seleções.

## Objetivo

Construir o arquivo:

```text
app.py
```

O app deve ter três páginas:

```text
1. Probabilidades pré-computadas
2. Simulação ao vivo
3. Explorador de partidas
```

## Entrada

### Banco de dados

Tabela:

```text
gold_probabilidades_copa
```

Usada na página 1.

### Modelos

Arquivos:

```text
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

Usados nas páginas 2 e 3.

### Dados auxiliares

Arquivos:

```text
data/grupos_copa2026.csv
data/calendario_copa2026.csv
```

Usados na simulação ao vivo.

### Módulos do projeto

Arquivos em `src/`:

```text
db.py
previsao.py
poisson.py
monte_carlo.py
bandeiras.py
```

## Saída

Aplicação Streamlit:

```text
app.py
```

O app deve rodar localmente com:

```bash
streamlit run app.py
```

E deve estar pronto para deploy no Streamlit Cloud.

## Correção principal desta feature

A função `prever_jogo` foi corrigida na Feature 07.

Portanto, o app não deve mais chamar:

```python
prever_jogo(time_casa, time_visitante, neutro, peso_torneio=3)
```

O correto é:

```python
prever_jogo(time_casa, time_visitante, neutro=True)
```

Motivo:

```text
peso_torneio e peso_recencia são usados apenas no treino.
Eles não são features de previsão de uma partida futura.
```

## Estrutura de páginas

## Página 1 — Probabilidades pré-computadas

### Objetivo

Mostrar as probabilidades finais calculadas pela Monte Carlo da Feature 08.

Essa página deve ler a tabela:

```text
gold_probabilidades_copa
```

E exibir as 12 seleções com maior chance de título.

### Requisitos

1. Ler `gold_probabilidades_copa` do banco.

2. Ordenar por `prob_campea` em ordem decrescente.

3. Mostrar apenas as 12 maiores probabilidades de título.

4. Exibir:

   * gráfico de barras;
   * tabela com probabilidades por fase.

5. Usar Altair para o gráfico, não `st.bar_chart`.

Motivo:

```text
st.bar_chart pode reordenar alfabeticamente.
Altair permite ordenar corretamente por probabilidade.
```

### Colunas exibidas

A tabela deve mostrar:

```text
selecao
prob_grupo
prob_oitavas
prob_quartas
prob_semi
prob_final
prob_campea
```

Em porcentagem:

```text
0.153 → 15.3%
```

### Bandeiras

Toda seleção deve aparecer com bandeira:

```text
🇧🇷 Brazil
🇫🇷 France
🇦🇷 Argentina
```

A função deve vir de:

```python
from bandeiras import com_bandeira
```

## Página 2 — Simulação ao vivo

### Objetivo

Rodar uma simulação única da Copa inteira.

Diferente da página 1, essa página não mostra probabilidade agregada. Ela mostra apenas uma realidade possível.

A cada clique, o torneio deve ser simulado novamente.

### Requisitos

1. Usar a função:

```python
simular_torneio_detalhado(...)
```

2. Mostrar:

   * campeã;
   * vice;
   * terceiro lugar;
   * mata-mata completo;
   * fase de grupos;
   * classificação por grupo.

3. Não usar cache na execução da simulação em si.

4. Não usar seed fixa na simulação ao vivo.

5. Usar seed fixa apenas na Feature 08 pré-computada.

### Importante

A página 2 deve mudar a cada clique.

Não fazer dentro da simulação ao vivo:

```python
np.random.seed(42)
```

Também não usar:

```python
rng = np.random.default_rng(42)
```

Para simulação ao vivo, usar:

```python
rng = np.random.default_rng()
```

Ou deixar a função criar um RNG sem seed fixa.

### Pódio

Exibir:

```text
Campeã
Vice
3º lugar
```

Exemplo:

```text
🏆 🇧🇷 Brazil
🥈 🇫🇷 France
🥉 🇦🇷 Argentina
```

### Mata-mata

Mostrar por rodada:

```text
32-avos
Oitavas
Quartas
Semifinais
Disputa de 3º lugar
Final
```

Cada jogo deve mostrar:

```text
time 1
placar
time 2
vencedor destacado
marcação se foi nos pênaltis
```

Exemplo:

```text
🇧🇷 Brazil 1 x 1 🇫🇷 France — Brazil venceu nos pênaltis
```

### Fase de grupos

Mostrar os placares dos jogos e a classificação final de cada grupo.

A tabela de classificação deve ter as colunas em português:

```text
posicao
selecao
jogos
vitorias
empates
derrotas
gols_pro
gols_contra
saldo_gols
pontos
```

Os nomes das seleções permanecem no idioma original, mas com bandeira.

Exemplo:

```text
🇧🇷 Brazil
🇲🇦 Morocco
🇫🇷 France
```

## Página 3 — Explorador de partidas

### Objetivo

Permitir ao usuário escolher duas seleções e ver:

```text
gols esperados
probabilidade de vitória do time 1
probabilidade de empate
probabilidade de vitória do time 2
```

### Requisitos

1. Dois seletores de seleção.
2. `format_func` com bandeira.
3. Checkbox de campo neutro.
4. Botão para prever.
5. Usar a função `prever_jogo` corrigida.

Chamada correta:

```python
prever_jogo(
    time_casa=time_casa,
    time_visitante=time_visitante,
    neutro=neutro
)
```

Não passar:

```text
peso_torneio
peso_recencia
peso_amostra
```

### Seletores

Os seletores devem listar as seleções disponíveis em `silver_elo_atual` ou no preparo dos modelos.

Exemplo:

```python
st.selectbox(
    "Seleção 1",
    selecoes,
    format_func=com_bandeira
)
```

### Validação

Não permitir prever um jogo da seleção contra ela mesma.

Se os dois seletores estiverem iguais, mostrar aviso:

```text
Escolha duas seleções diferentes.
```

### Exibição dos resultados

Exibir:

```text
xG Seleção 1
xG Seleção 2
Probabilidade de vitória da Seleção 1
Probabilidade de empate
Probabilidade de vitória da Seleção 2
```

Exemplo:

```text
🇧🇷 Brazil x 🇫🇷 France

Gols esperados:
Brazil: 1.35
France: 1.18

Probabilidades:
Brazil vence: 40.8%
Empate: 27.1%
France vence: 32.1%
```

## Bandeiras

Criar o arquivo:

```text
src/bandeiras.py
```

Ele deve conter um dicionário de nome da seleção para emoji.

Exemplo:

```python
BANDEIRAS = {
    "Brazil": "🇧🇷",
    "France": "🇫🇷",
    "Argentina": "🇦🇷",
    "Spain": "🇪🇸",
    "England": "🏴",
    "Scotland": "🏴",
    "United States": "🇺🇸",
    "Mexico": "🇲🇽",
    "Canada": "🇨🇦",
    "Morocco": "🇲🇦",
}
```

Função:

```python
def bandeira(selecao: str) -> str:
    return BANDEIRAS.get(selecao, "🏳️")

def com_bandeira(selecao: str) -> str:
    return f"{bandeira(selecao)} {selecao}"
```

Observação:

```text
Os nomes devem bater exatamente com os nomes do dataset.
Desconhecidos devem usar 🏳️.
```

## Conexão com banco

A conexão deve usar:

```text
DATABASE_URL
```

Não usar MCP.

Reutilizar:

```python
from db import get_engine
```

## Streamlit Cloud

No Streamlit Cloud, `DATABASE_URL` deve estar em `st.secrets`.

O app deve copiar o valor para `os.environ` antes de chamar `get_engine()`.

Exemplo:

```python
try:
    if "DATABASE_URL" in st.secrets and "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass
```

Motivo:

```text
Localmente, o projeto pode usar .env.
No Streamlit Cloud, usa Secrets.
```

Não hardcodar a connection string no código.

## Imports obrigatórios do `app.py`

Como os módulos ficam em `src/`, o app deve adicionar `src` ao path:

```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
```

Imports esperados:

```python
import os
import sys
import altair as alt
import pandas as pd
import streamlit as st

from db import get_engine
from previsao import carregar_modelos, prever_jogo
from monte_carlo import preparar, simular_torneio_detalhado, NOMES_RODADA
from bandeiras import com_bandeira
```

Não importar usando:

```python
from src.previsao import prever_jogo
```

Usar import flat:

```python
from previsao import prever_jogo
```

## Cache

Usar cache com cuidado.

### Usar `@st.cache_resource`

Para objetos pesados:

```text
engine
modelos
preparar()
```

Exemplo:

```python
@st.cache_resource
def carregar_engine():
    return get_engine()
```

```python
@st.cache_resource
def carregar_recursos():
    return preparar()
```

### Usar `@st.cache_data`

Para leitura estável de dados:

```text
gold_probabilidades_copa
```

Exemplo:

```python
@st.cache_data
def carregar_probabilidades():
    engine = carregar_engine()
    return pd.read_sql("SELECT * FROM gold_probabilidades_copa", engine)
```

### Não cachear

Não cachear a simulação ao vivo.

Errado:

```python
@st.cache_data
def rodar_simulacao_ao_vivo():
    ...
```

Certo:

```python
if st.button("Rodar simulação"):
    resultado = simular_torneio_detalhado(...)
```

## Layout do app

Configuração inicial:

```python
st.set_page_config(
    page_title="IAPredict — Copa 2026",
    layout="wide"
)
```

Criar seletor na barra lateral:

```python
pagina = st.sidebar.radio(
    "Página",
    [
        "Probabilidades pré-computadas",
        "Simulação ao vivo",
        "Explorador de partidas",
    ]
)
```

A página padrão deve ser:

```text
Probabilidades pré-computadas
```

## Esqueleto corrigido do `app.py`

```python
import os
import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    if "DATABASE_URL" in st.secrets and "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:
    pass

from db import get_engine
from previsao import carregar_modelos, prever_jogo
from monte_carlo import preparar, simular_torneio_detalhado, NOMES_RODADA
from bandeiras import com_bandeira

st.set_page_config(
    page_title="IAPredict — Copa 2026",
    layout="wide"
)

TOP_N = 12

@st.cache_resource
def carregar_engine():
    return get_engine()

@st.cache_resource
def carregar_modelos_cache():
    return carregar_modelos()

@st.cache_resource
def preparar_cache():
    return preparar()

@st.cache_data
def carregar_probabilidades():
    engine = carregar_engine()
    query = """
        SELECT *
        FROM gold_probabilidades_copa
        ORDER BY prob_campea DESC
    """
    return pd.read_sql(query, engine)

def formatar_percentual(valor):
    return f"{valor * 100:.1f}%"

def pagina_probabilidades():
    st.title("Probabilidades pré-computadas — Copa 2026")

    df = carregar_probabilidades().copy()
    df_top = df.sort_values("prob_campea", ascending=False).head(TOP_N).copy()

    df_top["selecao_exibicao"] = df_top["selecao"].apply(com_bandeira)
    df_top["pct_campea"] = df_top["prob_campea"] * 100

    chart = (
        alt.Chart(df_top)
        .mark_bar()
        .encode(
            x=alt.X("pct_campea:Q", title="Chance de título (%)"),
            y=alt.Y("selecao_exibicao:N", sort="-x", title="Seleção"),
            tooltip=[
                alt.Tooltip("selecao_exibicao:N", title="Seleção"),
                alt.Tooltip("pct_campea:Q", title="Chance de título", format=".1f"),
            ],
        )
    )

    st.altair_chart(chart, use_container_width=True)

    tabela = df_top[
        [
            "selecao",
            "prob_grupo",
            "prob_oitavas",
            "prob_quartas",
            "prob_semi",
            "prob_final",
            "prob_campea",
        ]
    ].copy()

    tabela["selecao"] = tabela["selecao"].apply(com_bandeira)

    for col in [
        "prob_grupo",
        "prob_oitavas",
        "prob_quartas",
        "prob_semi",
        "prob_final",
        "prob_campea",
    ]:
        tabela[col] = tabela[col].apply(formatar_percentual)

    tabela = tabela.rename(
        columns={
            "selecao": "Seleção",
            "prob_grupo": "Passa do grupo",
            "prob_oitavas": "Chega às oitavas",
            "prob_quartas": "Chega às quartas",
            "prob_semi": "Chega à semi",
            "prob_final": "Chega à final",
            "prob_campea": "Campeã",
        }
    )

    st.dataframe(tabela, use_container_width=True, hide_index=True)

def pagina_simulacao():
    st.title("Simulação ao vivo")

    st.write(
        "Esta página roda uma única simulação da Copa inteira. "
        "O resultado muda a cada execução."
    )

    recursos = preparar_cache()

    if st.button("Rodar simulação"):
        resultado = simular_torneio_detalhado(
            recursos=recursos,
            seed=None
        )

        campea = resultado["campea"]
        vice = resultado["vice"]
        terceiro = resultado["terceiro"]

        st.subheader("Pódio")
        col1, col2, col3 = st.columns(3)

        col1.metric("🏆 Campeã", com_bandeira(campea))
        col2.metric("🥈 Vice", com_bandeira(vice))
        col3.metric("🥉 3º lugar", com_bandeira(terceiro))

        st.subheader("Mata-mata")

        for rodada, jogos in resultado["mata_mata"].items():
            nome_rodada = NOMES_RODADA.get(rodada, rodada)
            st.markdown(f"### {nome_rodada}")

            dados_jogos = []

            for jogo in jogos:
                texto_penaltis = "Sim" if jogo.get("penaltis") else "Não"

                dados_jogos.append(
                    {
                        "Jogo": jogo["match"],
                        "Time 1": com_bandeira(jogo["time_casa"]),
                        "Placar": f'{jogo["gols_casa"]} x {jogo["gols_visitante"]}',
                        "Time 2": com_bandeira(jogo["time_visitante"]),
                        "Vencedor": com_bandeira(jogo["vencedor"]),
                        "Pênaltis": texto_penaltis,
                    }
                )

            st.dataframe(pd.DataFrame(dados_jogos), use_container_width=True, hide_index=True)

        st.subheader("Fase de grupos")

        for grupo, dados_grupo in resultado["grupos"].items():
            st.markdown(f"### Grupo {grupo}")

            st.markdown("#### Jogos")
            jogos = pd.DataFrame(dados_grupo["jogos"])
            if not jogos.empty:
                jogos["time_casa"] = jogos["time_casa"].apply(com_bandeira)
                jogos["time_visitante"] = jogos["time_visitante"].apply(com_bandeira)

                jogos = jogos.rename(
                    columns={
                        "time_casa": "Time 1",
                        "time_visitante": "Time 2",
                        "gols_casa": "Gols Time 1",
                        "gols_visitante": "Gols Time 2",
                    }
                )

                st.dataframe(jogos, use_container_width=True, hide_index=True)

            st.markdown("#### Classificação")
            classificacao = pd.DataFrame(dados_grupo["classificacao"])

            if not classificacao.empty:
                classificacao["selecao"] = classificacao["selecao"].apply(com_bandeira)

                colunas = [
                    "posicao",
                    "selecao",
                    "jogos",
                    "vitorias",
                    "empates",
                    "derrotas",
                    "gols_pro",
                    "gols_contra",
                    "saldo_gols",
                    "pontos",
                ]

                classificacao = classificacao[colunas]

                st.dataframe(classificacao, use_container_width=True, hide_index=True)

def pagina_explorador():
    st.title("Explorador de partidas")

    modelos, elos, colunas = carregar_modelos_cache()

    selecoes = sorted(elos.keys())

    col1, col2 = st.columns(2)

    with col1:
        time_casa = st.selectbox(
            "Seleção 1",
            selecoes,
            format_func=com_bandeira,
            index=0,
        )

    with col2:
        time_visitante = st.selectbox(
            "Seleção 2",
            selecoes,
            format_func=com_bandeira,
            index=1 if len(selecoes) > 1 else 0,
        )

    neutro = st.checkbox("Campo neutro", value=True)

    if st.button("Prever partida"):
        if time_casa == time_visitante:
            st.warning("Escolha duas seleções diferentes.")
            return

        previsao = prever_jogo(
            time_casa=time_casa,
            time_visitante=time_visitante,
            neutro=neutro,
            modelos=modelos,
            elos=elos,
            colunas_atributos=colunas,
        )

        st.subheader(f"{com_bandeira(time_casa)} x {com_bandeira(time_visitante)}")

        c1, c2 = st.columns(2)

        c1.metric(
            f"xG {com_bandeira(time_casa)}",
            f'{previsao["gols_esperados_casa"]:.2f}',
        )

        c2.metric(
            f"xG {com_bandeira(time_visitante)}",
            f'{previsao["gols_esperados_visitante"]:.2f}',
        )

        st.subheader("Probabilidades")

        p1, p2, p3 = st.columns(3)

        p1.metric(
            f"{com_bandeira(time_casa)} vence",
            formatar_percentual(previsao["prob_vitoria"]),
        )

        p2.metric(
            "Empate",
            formatar_percentual(previsao["prob_empate"]),
        )

        p3.metric(
            f"{com_bandeira(time_visitante)} vence",
            formatar_percentual(previsao["prob_derrota"]),
        )

pagina = st.sidebar.radio(
    "Página",
    [
        "Probabilidades pré-computadas",
        "Simulação ao vivo",
        "Explorador de partidas",
    ],
)

if pagina == "Probabilidades pré-computadas":
    pagina_probabilidades()
elif pagina == "Simulação ao vivo":
    pagina_simulacao()
else:
    pagina_explorador()
```

## Observações sobre o esqueleto

O esqueleto assume que:

```python
carregar_modelos()
```

retorna:

```python
modelos, elos, colunas
```

E que:

```python
prever_jogo(...)
```

aceita injeção de dependências:

```python
prever_jogo(
    time_casa,
    time_visitante,
    neutro,
    modelos,
    elos,
    colunas_atributos
)
```

Caso sua implementação use outro formato, adaptar apenas essa chamada, mantendo a regra principal:

```text
não passar peso_torneio
não passar peso_recencia
```

## Arquivos necessários no repositório

Para o deploy funcionar, o repositório deve conter:

```text
app.py
requirements.txt
src/db.py
src/previsao.py
src/poisson.py
src/monte_carlo.py
src/bandeiras.py
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
data/grupos_copa2026.csv
data/calendario_copa2026.csv
```

## Secrets no Streamlit Cloud

Configurar em:

```text
App → Settings → Secrets
```

Adicionar:

```toml
DATABASE_URL = "postgresql://usuario:senha@host:porta/database"
```

Não commitar `.env`.

Não deixar senha no código.

## Requirements

O `requirements.txt` deve conter pelo menos:

```text
streamlit
pandas
sqlalchemy
psycopg2-binary
altair
numpy
scipy
statsmodels
python-dotenv
```

## Critérios de aceite

A Feature 09 será considerada correta quando:

1. `streamlit run app.py` abrir sem erro.
2. A barra lateral mostrar as 3 páginas.
3. A página 1 carregar `gold_probabilidades_copa`.
4. A página 1 mostrar as 12 maiores chances de título.
5. O gráfico da página 1 estiver ordenado da maior para a menor probabilidade.
6. A tabela da página 1 mostrar probabilidades por fase.
7. Todas as seleções aparecerem com bandeira.
8. A página 2 rodar uma simulação completa até a campeã.
9. A página 2 mudar a cada nova simulação.
10. A página 2 mostrar pódio, mata-mata e grupos.
11. A classificação dos grupos usar colunas em português.
12. A página 3 permitir escolher duas seleções.
13. A página 3 não permitir seleção contra ela mesma.
14. A página 3 mostrar xG e probabilidades.
15. A página 3 chamar `prever_jogo` sem `peso_torneio`.
16. O app funcionar localmente e no Streamlit Cloud.
17. Nenhuma connection string ficar hardcoded no código.

## Validação manual

Rodar:

```bash
streamlit run app.py
```

Testar:

```text
Página 1 → conferir top 12
Página 2 → clicar em rodar simulação
Página 3 → testar Brazil x France
Página 3 → testar France x Scotland
Página 3 → testar Scotland x France em campo neutro
```

Em campo neutro, inverter os times não deve mudar drasticamente o favoritismo.

## Validação headless

Usar:

```python
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py").run()
assert not at.exception

at.sidebar.radio[0].set_value("Simulação ao vivo").run()
assert not at.exception

at.sidebar.radio[0].set_value("Explorador de partidas").run()
at.button[0].click().run()
assert not at.exception
```

## SQL de conferência da página 1

A página 1 deve bater com:

```sql
SELECT
    selecao,
    ROUND((prob_campea * 100)::numeric, 1) AS pct
FROM gold_probabilidades_copa
ORDER BY prob_campea DESC
LIMIT 12;
```

## Para explicar enquanto desenvolve

* Streamlit transforma um script Python em um app web.
* A página 1 mostra probabilidades estáveis já pré-computadas.
* A página 2 mostra apenas uma simulação aleatória possível.
* A página 3 permite explorar confrontos específicos.
* Bandeiras melhoram a leitura visual.
* O banco entra por `DATABASE_URL`, sem expor senha no código.
* O app não calcula o modelo do zero; ele consome os modelos e tabelas já gerados pelas features anteriores.
