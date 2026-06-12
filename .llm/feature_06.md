# Feature 06 — Treino Poisson + validação

## Contexto

Esta é a feature central do modelo.

Gols são contagens:

```text
0, 1, 2, 3, ...
```

Por isso, o modelo adequado é uma regressão Poisson, não uma regressão linear comum.

Nesta etapa, serão treinados dois modelos:

```text
modelo_poisson_casa
modelo_poisson_visitante
```

Um modelo aprende a estimar os gols esperados do time da casa.
O outro aprende a estimar os gols esperados do time visitante.

O valor previsto pelo Poisson é chamado de λ.

No contexto do futebol, λ pode ser interpretado como:

```text
gols esperados
```

ou, de forma aproximada:

```text
xG estimado pelo modelo
```

## Objetivo

Treinar, validar e salvar dois modelos Poisson para prever gols esperados de partidas entre seleções.

A feature deve:

1. ler `gold_atributos`;
2. separar treino e teste por data;
3. treinar dois modelos Poisson;
4. calcular métricas de validação;
5. salvar os modelos finais em `.pkl`;
6. criar o módulo compartilhado `src/poisson.py`;
7. gravar a tabela `metricas_validacao`.

## Entrada

Tabela:

```text
gold_atributos
```

Colunas esperadas:

```text
id
ponderado_id
jogo_id
data
time_casa
time_visitante
elo_casa
elo_visitante
dif_elo
neutro
peso_torneio
peso_recencia
peso_amostra
gols_casa
gols_visitante
```

## Saídas

Arquivos:

```text
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

Tabela:

```text
metricas_validacao
```

Módulo compartilhado:

```text
src/poisson.py
```

## Separação conceitual das colunas

Esta feature deve respeitar a separação definida na Feature 05.

### Features preditivas

Somente estas colunas podem entrar no `X` do modelo:

```text
elo_casa
elo_visitante
dif_elo
neutro
```

### Pesos de treino

Estas colunas não são features. Elas servem apenas para ponderar a importância das linhas no treino:

```text
peso_torneio
peso_recencia
peso_amostra
```

A coluna usada no treino será:

```text
peso_amostra
```

Onde:

```text
peso_amostra = peso_torneio × peso_recencia
```

### Alvos do modelo

Estas colunas são as respostas que o modelo tenta prever:

```text
gols_casa
gols_visitante
```

Elas não podem entrar no `X`.

## Correção importante

Não usar como features:

```text
peso_torneio
peso_recencia
peso_amostra
gols_casa
gols_visitante
```

Uso correto:

```python
COLUNAS_ATRIBUTOS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]
```

Uso incorreto:

```python
COLUNAS_ATRIBUTOS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_torneio",
    "peso_recencia",
]
```

Motivo:

```text
peso_torneio e peso_recencia indicam quanto um jogo histórico deve pesar no treino.
Eles não são características reais de uma partida futura.
```

## Requisitos

### 1. Ler `gold_atributos`

Ler:

```sql
SELECT *
FROM gold_atributos
ORDER BY data, ponderado_id;
```

Não usar:

```text
bronze_jogos
silver_jogos
silver_ponderado
```

A Feature 06 deve partir da tabela Gold.

### 2. Validar dados de entrada

Antes de treinar, validar que não existem nulos nas colunas necessárias:

```python
COLUNAS_OBRIGATORIAS = [
    "data",
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_amostra",
    "gols_casa",
    "gols_visitante",
]
```

Validação:

```python
assert df[COLUNAS_OBRIGATORIAS].isna().sum().sum() == 0
```

Também validar:

```python
assert (df["peso_amostra"] > 0).all()
assert (df["gols_casa"] >= 0).all()
assert (df["gols_visitante"] >= 0).all()
```

### 3. Split temporal

Separar treino e teste por data.

Regra:

```text
treino: data < 2024-01-01
teste:  data >= 2024-01-01
```

Exemplo:

```python
DATA_SPLIT = pd.Timestamp("2024-01-01")

treino = df[df["data"] < DATA_SPLIT].copy()
teste = df[df["data"] >= DATA_SPLIT].copy()
```

Esse split é temporal para evitar vazamento de informação do futuro.

Não usar split aleatório.

Errado:

```python
train_test_split(df, test_size=0.2, random_state=42)
```

Certo:

```python
treino = df[df["data"] < "2024-01-01"]
teste = df[df["data"] >= "2024-01-01"]
```

### 4. Montar matriz de atributos

Criar uma função para montar o `X`.

A função deve:

1. selecionar apenas as 4 features;
2. converter `neutro` para inteiro;
3. adicionar constante com `statsmodels`.

Exemplo:

```python
import statsmodels.api as sm

COLUNAS_ATRIBUTOS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]

def montar_X(df):
    X = df[COLUNAS_ATRIBUTOS].copy()
    X["neutro"] = X["neutro"].astype(int)
    X = sm.add_constant(X, has_constant="add")
    return X
```

A constante é necessária porque o modelo precisa de intercepto.

### 5. Definir alvos

Alvo do modelo da casa:

```python
y_casa = treino["gols_casa"]
```

Alvo do modelo visitante:

```python
y_visitante = treino["gols_visitante"]
```

### 6. Definir peso de amostra

Usar:

```python
peso_treino = treino["peso_amostra"]
```

O peso de amostra vem da Feature 05:

```text
peso_amostra = peso_torneio × peso_recencia
```

Esse peso faz com que jogos recentes e jogos mais importantes influenciem mais o treinamento.

### 7. Treinar os modelos Poisson de validação

Usar `statsmodels` com família Poisson.

Exemplo:

```python
modelo_casa_validacao = sm.GLM(
    y_casa,
    X_treino,
    family=sm.families.Poisson(),
    freq_weights=peso_treino
).fit()

modelo_visitante_validacao = sm.GLM(
    y_visitante,
    X_treino,
    family=sm.families.Poisson(),
    freq_weights=peso_treino
).fit()
```

Observação:

```text
freq_weights é usado para dizer que algumas observações têm mais peso no ajuste.
```

Não passar `peso_amostra` dentro do `X`.

### 8. Prever no teste

Montar:

```python
X_teste = montar_X(teste)
```

Prever λ:

```python
lambda_casa = modelo_casa_validacao.predict(X_teste)
lambda_visitante = modelo_visitante_validacao.predict(X_teste)
```

Esses valores representam os gols esperados de cada lado.

### 9. Calcular MAE

Calcular:

```python
mae_casa = mean_absolute_error(teste["gols_casa"], lambda_casa)
mae_visitante = mean_absolute_error(teste["gols_visitante"], lambda_visitante)
```

Ou manualmente:

```python
mae_casa = abs(lambda_casa - teste["gols_casa"]).mean()
mae_visitante = abs(lambda_visitante - teste["gols_visitante"]).mean()
```

Faixa esperada:

```text
MAE entre aproximadamente 0.9 e 1.3
```

### 10. Criar `src/poisson.py`

Criar um módulo reutilizável para converter λ em probabilidades de resultado.

Arquivo:

```text
src/poisson.py
```

Funções mínimas:

```python
import math
import numpy as np

MAX_GOLS = 10

def poisson_pmf(k, lamb):
    return math.exp(-lamb) * (lamb ** k) / math.factorial(k)

def probabilidades_resultado(lambda_casa, lambda_visitante, max_gols=MAX_GOLS):
    prob_vitoria = 0.0
    prob_empate = 0.0
    prob_derrota = 0.0

    for gols_casa in range(max_gols + 1):
        p_casa = poisson_pmf(gols_casa, lambda_casa)

        for gols_visitante in range(max_gols + 1):
            p_visitante = poisson_pmf(gols_visitante, lambda_visitante)
            p = p_casa * p_visitante

            if gols_casa > gols_visitante:
                prob_vitoria += p
            elif gols_casa == gols_visitante:
                prob_empate += p
            else:
                prob_derrota += p

    soma = prob_vitoria + prob_empate + prob_derrota

    if soma > 0:
        prob_vitoria /= soma
        prob_empate /= soma
        prob_derrota /= soma

    return {
        "prob_vitoria": prob_vitoria,
        "prob_empate": prob_empate,
        "prob_derrota": prob_derrota,
    }

def resultado_previsto(lambda_casa, lambda_visitante, max_gols=MAX_GOLS):
    probs = probabilidades_resultado(lambda_casa, lambda_visitante, max_gols=max_gols)

    mapa = {
        "V": probs["prob_vitoria"],
        "E": probs["prob_empate"],
        "D": probs["prob_derrota"],
    }

    return max(mapa, key=mapa.get)

def resultado_real(gols_casa, gols_visitante):
    if gols_casa > gols_visitante:
        return "V"
    if gols_casa == gols_visitante:
        return "E"
    return "D"
```

Onde:

```text
V = vitória do time da casa
E = empate
D = derrota do time da casa
```

### 11. Calcular acurácia de resultado

Para cada jogo do teste:

1. calcular `resultado_previsto`;
2. calcular `resultado_real`;
3. comparar os dois.

Exemplo:

```python
from poisson import resultado_previsto, resultado_real

previstos = []
reais = []

for lc, lv, gc, gv in zip(
    lambda_casa,
    lambda_visitante,
    teste["gols_casa"],
    teste["gols_visitante"]
):
    previstos.append(resultado_previsto(lc, lv))
    reais.append(resultado_real(gc, gv))

acuracia = np.mean(np.array(previstos) == np.array(reais))
```

Faixa esperada:

```text
aproximadamente 55% a 62%
```

O modelo deve superar um baseline simples como “sempre vitória da casa”.

### 12. Gravar métricas de validação

Criar tabela:

```text
metricas_validacao
```

Schema:

```sql
CREATE TABLE metricas_validacao (
    id bigint generated always as identity primary key,
    data_execucao timestamp default now(),
    mae_casa double precision,
    mae_visitante double precision,
    acuracia double precision,
    n_treino integer,
    n_teste integer
);
```

Gravar uma linha com as métricas calculadas.

A gravação deve ser idempotente:

```sql
DROP TABLE IF EXISTS metricas_validacao;
CREATE TABLE metricas_validacao (...);
COPY ...
```

### 13. Treinar modelo final para produção

Depois de calcular as métricas, treinar novamente os dois modelos usando **todos os dados disponíveis em `gold_atributos`**.

Motivo:

```text
A validação mede desempenho usando treino até 2023 e teste em 2024+.
Mas o modelo usado para simular a Copa deve aproveitar todo o histórico pré-Copa disponível.
```

Treino final:

```python
X_final = montar_X(df)
peso_final = df["peso_amostra"]

modelo_casa_final = sm.GLM(
    df["gols_casa"],
    X_final,
    family=sm.families.Poisson(),
    freq_weights=peso_final
).fit()

modelo_visitante_final = sm.GLM(
    df["gols_visitante"],
    X_final,
    family=sm.families.Poisson(),
    freq_weights=peso_final
).fit()
```

Esses modelos finais são os que devem ser salvos em `.pkl`.

### 14. Salvar artefatos

Criar a pasta:

```text
models/
```

Salvar:

```text
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

O arquivo `colunas_atributos.pkl` deve conter apenas:

```python
[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]
```

Não salvar:

```python
[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_torneio",
    "peso_recencia",
]
```

### 15. Não usar identificadores como features

Não usar no `X`:

```text
id
ponderado_id
jogo_id
data
time_casa
time_visitante
```

A coluna `data` serve apenas para o split temporal.

Os nomes das seleções servem apenas para identificação.

### 16. Não usar placares como features

Não usar no `X`:

```text
gols_casa
gols_visitante
```

Essas colunas são os alvos.

### 17. Não usar pesos como features

Não usar no `X`:

```text
peso_torneio
peso_recencia
peso_amostra
```

Essas colunas são pesos de treino.

## Critérios de aceite

A Feature 06 será considerada correta quando:

1. Os modelos Poisson forem treinados com `statsmodels`.

2. O split temporal for feito por `data`.

3. O treino de validação usar somente jogos com `data < 2024-01-01`.

4. O teste usar somente jogos com `data >= 2024-01-01`.

5. O `X` tiver somente as 4 features preditivas:

   * `elo_casa`
   * `elo_visitante`
   * `dif_elo`
   * `neutro`

6. `peso_amostra` for usado como peso de treino.

7. `peso_torneio`, `peso_recencia` e `peso_amostra` não entrarem como features.

8. `gols_casa` e `gols_visitante` não entrarem como features.

9. `metricas_validacao` for gravada no banco.

10. Os arquivos `.pkl` forem criados em `models/`.

11. `colunas_atributos.pkl` contiver somente as 4 features corretas.

12. O modelo final salvo for retreinado com todos os dados de `gold_atributos`.

13. A acurácia fique em uma faixa plausível, idealmente acima do baseline.

14. O MAE fique em faixa plausível, aproximadamente entre 0.9 e 1.3.

## Verificação SQL

### Verificar métricas

```sql
SELECT
    mae_casa,
    mae_visitante,
    acuracia,
    n_treino,
    n_teste
FROM metricas_validacao;
```

### Verificar se existe apenas uma linha de métricas

```sql
SELECT COUNT(*)
FROM metricas_validacao;
```

Resultado esperado:

```text
1
```

## Verificação de arquivos

```bash
ls -la models/
```

Resultado esperado:

```text
modelo_poisson_casa.pkl
modelo_poisson_visitante.pkl
colunas_atributos.pkl
```

## Verificação em Python

```python
import pickle

with open("models/colunas_atributos.pkl", "rb") as f:
    colunas = pickle.load(f)

print(colunas)
```

Resultado esperado:

```python
["elo_casa", "elo_visitante", "dif_elo", "neutro"]
```

## Plano de implementação

1. Criar `src/poisson.py`.
2. Ler `gold_atributos`.
3. Validar nulos e pesos.
4. Definir:

```python
COLUNAS_ATRIBUTOS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]
```

5. Criar função `montar_X`.

6. Fazer split temporal:

   * treino `< 2024-01-01`;
   * teste `>= 2024-01-01`.

7. Treinar dois modelos Poisson de validação com o treino.

8. Prever λ no teste.

9. Calcular:

   * `mae_casa`;
   * `mae_visitante`;
   * `acuracia`.

10. Gravar `metricas_validacao`.

11. Retreinar dois modelos finais com todos os dados de `gold_atributos`.

12. Criar pasta `models/`.

13. Salvar:

* `modelo_poisson_casa.pkl`;
* `modelo_poisson_visitante.pkl`;
* `colunas_atributos.pkl`.

## Para explicar enquanto desenvolve

* Gol é contagem, por isso Poisson é mais adequado que regressão linear.
* O modelo estima λ, que representa gols esperados.
* São dois modelos porque o comportamento de mandante e visitante é diferente.
* O split temporal evita aprender com o futuro.
* `gols_casa` e `gols_visitante` são respostas, não entradas.
* `peso_torneio` e `peso_recencia` dizem quanto um jogo pesa no treino, não quem vence uma partida futura.
* Primeiro validamos com dados separados; depois treinamos o modelo final usando todo o histórico disponível antes da Copa.
