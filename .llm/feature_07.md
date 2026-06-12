# Feature 07 — Previsão de partida + experimentos

## Contexto

Com os modelos Poisson treinados na Feature 06, esta feature transforma o modelo em uma função prática de previsão.

Ela tem dois objetivos:

```text
1. Criar uma função para prever uma partida entre duas seleções.
2. Rodar experimentos comparando diferentes configurações de recência.
```

A função de previsão será usada depois pela simulação Monte Carlo da Copa 2026 e pelo dashboard em Streamlit.

## Objetivo

Construir a função:

```python
prever_jogo(time_casa, time_visitante, neutro=True)
```

Essa função deve retornar:

```text
gols_esperados_casa
gols_esperados_visitante
prob_vitoria
prob_empate
prob_derrota
```

Também deve gerar duas tabelas:

```text
previsoes
experimentos_mae
```

## Entrada

Arquivos:

```text
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

Tabelas:

```text
silver_elo_atual
gold_atributos
silver_copa2026
```

Módulo:

```text
src/poisson.py
```

## Saídas

### 1. Tabela `previsoes`

Contém as previsões dos 72 jogos da fase de grupos da Copa 2026.

Colunas:

```text
id
data
time_casa
time_visitante
neutro
gols_esperados_casa
gols_esperados_visitante
prob_vitoria
prob_empate
prob_derrota
```

Onde:

```text
prob_vitoria = probabilidade de vitória do time_casa
prob_empate = probabilidade de empate
prob_derrota = probabilidade de vitória do time_visitante
```

### 2. Tabela `experimentos_mae`

Contém o resultado dos experimentos de recência.

Colunas:

```text
id
config
mae_casa
mae_visitante
```

## Correção principal desta feature

A função de previsão **não deve receber `peso_torneio` nem `peso_recencia`**.

Errado:

```python
prever_jogo(time_casa, time_visitante, neutro, peso_torneio)
```

Certo:

```python
prever_jogo(time_casa, time_visitante, neutro=True)
```

Motivo:

```text
peso_torneio e peso_recencia são pesos de treino.
Eles não são características reais de uma partida futura.
```

Na previsão, o modelo deve usar apenas as mesmas 4 features salvas em `colunas_atributos.pkl`:

```python
[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]
```

## Requisitos

### 1. Carregar modelos treinados

Carregar os três arquivos gerados na Feature 06:

```python
models/modelo_poisson_casa.pkl
models/modelo_poisson_visitante.pkl
models/colunas_atributos.pkl
```

A lista de colunas deve conter somente:

```python
["elo_casa", "elo_visitante", "dif_elo", "neutro"]
```

Se vier diferente, a feature deve parar com erro.

Validação sugerida:

```python
COLUNAS_ESPERADAS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]

assert colunas_atributos == COLUNAS_ESPERADAS
```

### 2. Carregar ELO atual

Ler:

```sql
SELECT selecao, elo
FROM silver_elo_atual;
```

Transformar em dicionário:

```python
elos = {
    "Brazil": 1800.0,
    "France": 1850.0,
    ...
}
```

Esse ELO representa a força mais recente de cada seleção antes da Copa.

### 3. Função base para montar features

Criar uma função interna para montar uma linha de features:

```python
def montar_features_partida(time_casa, time_visitante, neutro, elos):
    elo_casa = elos[time_casa]
    elo_visitante = elos[time_visitante]

    dados = {
        "elo_casa": elo_casa,
        "elo_visitante": elo_visitante,
        "dif_elo": elo_casa - elo_visitante,
        "neutro": int(neutro),
    }

    X = pd.DataFrame([dados])
    X = X[["elo_casa", "elo_visitante", "dif_elo", "neutro"]]
    X = sm.add_constant(X, has_constant="add")

    return X
```

Não incluir:

```text
peso_torneio
peso_recencia
peso_amostra
gols_casa
gols_visitante
```

### 4. Função `prever_jogo`

Criar a função:

```python
def prever_jogo(time_casa, time_visitante, neutro=True):
    ...
```

Ela deve:

1. buscar o ELO atual de cada seleção;
2. calcular `dif_elo`;
3. montar o `X` com as 4 features;
4. prever os lambdas dos dois modelos;
5. transformar os lambdas em probabilidades usando `src/poisson.py`.

Exemplo de retorno:

```python
{
    "time_casa": "Brazil",
    "time_visitante": "France",
    "gols_esperados_casa": 1.38,
    "gols_esperados_visitante": 1.21,
    "prob_vitoria": 0.41,
    "prob_empate": 0.27,
    "prob_derrota": 0.32,
}
```

### 5. Usar `src/poisson.py`

As probabilidades devem vir da função:

```python
probabilidades_resultado(lambda_casa, lambda_visitante)
```

Não reimplementar a grade de Poisson nesta feature.

Uso esperado:

```python
from poisson import probabilidades_resultado

probs = probabilidades_resultado(lambda_casa, lambda_visitante)
```

### 6. Simetrizar jogos neutros

Como os jogos da Copa são em campo neutro, é importante reduzir o viés artificial causado pela ordem `time_casa` e `time_visitante`.

Mesmo com `neutro=True`, ainda existem dois modelos separados:

```text
modelo_poisson_casa
modelo_poisson_visitante
```

Por isso, para jogos neutros, a previsão deve ser simetrizada.

#### Regra para jogo neutro

Para `time_a` contra `time_b`:

1. prever `time_a` como casa e `time_b` como visitante;
2. prever `time_b` como casa e `time_a` como visitante;
3. tirar a média dos lambdas equivalentes.

Exemplo:

```python
def prever_lambdas_sem_simetria(time_casa, time_visitante, neutro, modelos, elos):
    X = montar_features_partida(time_casa, time_visitante, neutro, elos)

    lambda_casa = float(modelos["casa"].predict(X)[0])
    lambda_visitante = float(modelos["visitante"].predict(X)[0])

    return lambda_casa, lambda_visitante
```

Para jogo neutro:

```python
lambda_a_casa, lambda_b_visitante = prever_lambdas_sem_simetria(
    time_a,
    time_b,
    True,
    modelos,
    elos
)

lambda_b_casa, lambda_a_visitante = prever_lambdas_sem_simetria(
    time_b,
    time_a,
    True,
    modelos,
    elos
)

lambda_a = (lambda_a_casa + lambda_a_visitante) / 2
lambda_b = (lambda_b_visitante + lambda_b_casa) / 2
```

Assim, inverter a ordem dos times não muda drasticamente a previsão.

#### Regra para jogo não neutro

Se `neutro=False`, não simetrizar.

Nesse caso, a ordem importa porque o primeiro time é mandante.

### 7. Garantir lambdas válidos

Os lambdas devem ser positivos.

Validar:

```python
lambda_casa = max(lambda_casa, 0.01)
lambda_visitante = max(lambda_visitante, 0.01)
```

Isso evita problemas numéricos em casos extremos.

### 8. Gerar `previsoes` para a Copa 2026

Ler:

```sql
SELECT *
FROM silver_copa2026
ORDER BY data, id;
```

Aplicar `prever_jogo` a cada uma das 72 partidas.

Importante:

```text
Não passar peso_torneio = 3.
Não passar peso_recencia = 1.0.
```

A função deve receber apenas:

```python
prever_jogo(
    time_casa=row["time_casa"],
    time_visitante=row["time_visitante"],
    neutro=row["neutro"],
)
```

A tabela `previsoes` deve ter aproximadamente 72 linhas.

### 9. Validar soma das probabilidades

Para cada jogo:

```text
prob_vitoria + prob_empate + prob_derrota ≈ 1
```

Validação sugerida:

```python
soma = prob_vitoria + prob_empate + prob_derrota
assert abs(soma - 1) < 0.001
```

### 10. Rodar experimentos de recência

A segunda parte da Feature 07 compara diferentes configurações de peso por recência.

Configurações:

```text
sem_recencia
meia_vida_3
meia_vida_5
meia_vida_10
```

### 11. Regra dos experimentos

Nos experimentos, a recência deve alterar apenas o peso de treino.

Ou seja:

```text
peso_recencia muda
peso_amostra muda
X não muda
```

O `X` continua sempre com as mesmas 4 features:

```python
[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]
```

Não fazer:

```text
recalcular peso_recencia e colocar dentro do X
```

Fazer:

```text
recalcular peso_recencia e usar em peso_amostra
```

### 12. Configurações dos experimentos

#### `sem_recencia`

```python
peso_recencia_config = 1.0
peso_amostra_config = peso_torneio
```

#### `meia_vida_3`

```python
peso_recencia_config = 0.5 ** (idade_anos / 3)
peso_amostra_config = peso_torneio * peso_recencia_config
```

#### `meia_vida_5`

```python
peso_recencia_config = 0.5 ** (idade_anos / 5)
peso_amostra_config = peso_torneio * peso_recencia_config
```

#### `meia_vida_10`

```python
peso_recencia_config = 0.5 ** (idade_anos / 10)
peso_amostra_config = peso_torneio * peso_recencia_config
```

A data de referência deve ser:

```python
DATA_REF = pd.Timestamp("2026-06-11")
```

Proteger contra idade negativa:

```python
idade_anos = ((DATA_REF - df["data"]).dt.days / 365.25).clip(lower=0)
```

### 13. Split temporal dos experimentos

Usar o mesmo split da Feature 06:

```text
treino: data < 2024-01-01
teste:  data >= 2024-01-01
```

Não usar split aleatório.

### 14. Treinamento dos experimentos

Para cada configuração:

1. recalcular `peso_amostra_config`;
2. fazer split temporal;
3. treinar dois GLM Poisson;
4. prever no teste;
5. calcular `mae_casa` e `mae_visitante`;
6. gravar uma linha em `experimentos_mae`.

O modelo dos experimentos não precisa sobrescrever os `.pkl` de produção.

### 15. Função auxiliar para montar `X` nos experimentos

Usar a mesma função da Feature 06:

```python
def montar_X(df):
    X = df[["elo_casa", "elo_visitante", "dif_elo", "neutro"]].copy()
    X["neutro"] = X["neutro"].astype(int)
    X = sm.add_constant(X, has_constant="add")
    return X
```

### 16. Gravação idempotente

As tabelas devem ser recriadas do zero:

```sql
DROP TABLE IF EXISTS previsoes;
DROP TABLE IF EXISTS experimentos_mae;
CREATE TABLE ...
COPY ...
```

## Schema das tabelas

### `previsoes`

```sql
CREATE TABLE previsoes (
    id bigint generated always as identity primary key,
    data date,
    time_casa text,
    time_visitante text,
    neutro boolean,
    gols_esperados_casa double precision,
    gols_esperados_visitante double precision,
    prob_vitoria double precision,
    prob_empate double precision,
    prob_derrota double precision
);
```

### `experimentos_mae`

```sql
CREATE TABLE experimentos_mae (
    id bigint generated always as identity primary key,
    config text,
    mae_casa double precision,
    mae_visitante double precision
);
```

## Critérios de aceite

A Feature 07 será considerada correta quando:

1. `prever_jogo` usar somente as 4 features corretas.
2. `prever_jogo` não receber `peso_torneio`.
3. `prever_jogo` não receber `peso_recencia`.
4. `prever_jogo` usar `silver_elo_atual`.
5. Jogos neutros forem simetrizados para reduzir viés de casa/visitante.
6. As probabilidades vierem de `src/poisson.py`.
7. A tabela `previsoes` tiver aproximadamente 72 jogos.
8. A soma `prob_vitoria + prob_empate + prob_derrota` for aproximadamente 1 em todos os jogos.
9. `experimentos_mae` tiver 4 linhas.
10. Os experimentos alterarem apenas o peso de treino, não as features.
11. Nenhum experimento sobrescrever os modelos finais salvos em `models/`.

## Verificação SQL

### Verificar previsões

```sql
SELECT
    time_casa,
    time_visitante,
    ROUND(gols_esperados_casa::numeric, 2) AS xg_casa,
    ROUND(gols_esperados_visitante::numeric, 2) AS xg_visitante,
    ROUND(prob_vitoria::numeric, 3) AS prob_vitoria,
    ROUND(prob_empate::numeric, 3) AS prob_empate,
    ROUND(prob_derrota::numeric, 3) AS prob_derrota
FROM previsoes
ORDER BY data, id
LIMIT 10;
```

### Verificar soma das probabilidades

```sql
SELECT
    time_casa,
    time_visitante,
    ROUND((prob_vitoria + prob_empate + prob_derrota)::numeric, 3) AS soma
FROM previsoes
ORDER BY data, id
LIMIT 10;
```

Resultado esperado:

```text
soma ≈ 1.000
```

### Verificar todos os jogos com soma correta

```sql
SELECT COUNT(*)
FROM previsoes
WHERE ABS((prob_vitoria + prob_empate + prob_derrota) - 1) > 0.001;
```

Resultado esperado:

```text
0
```

### Verificar quantidade de previsões

```sql
SELECT COUNT(*)
FROM previsoes;
```

Resultado esperado:

```text
aproximadamente 72
```

### Verificar experimentos

```sql
SELECT
    config,
    ROUND(mae_casa::numeric, 3) AS mae_casa,
    ROUND(mae_visitante::numeric, 3) AS mae_visitante
FROM experimentos_mae
ORDER BY mae_casa;
```

Resultado esperado:

```text
4 configurações
```

### Verificar quantidade de experimentos

```sql
SELECT COUNT(*)
FROM experimentos_mae;
```

Resultado esperado:

```text
4
```

## Testes manuais recomendados

Testar confrontos fortes contra médios:

```python
prever_jogo("France", "Scotland", neutro=True)
prever_jogo("Brazil", "Scotland", neutro=True)
prever_jogo("Argentina", "Scotland", neutro=True)
prever_jogo("Spain", "Scotland", neutro=True)
```

Depois inverter:

```python
prever_jogo("Scotland", "France", neutro=True)
prever_jogo("Scotland", "Brazil", neutro=True)
prever_jogo("Scotland", "Argentina", neutro=True)
prever_jogo("Scotland", "Spain", neutro=True)
```

Com campo neutro, inverter a ordem não deve alterar drasticamente o favoritismo.

Se alterar muito, a simetrização não está funcionando.

## Plano de implementação

1. Carregar modelos `.pkl`.
2. Validar `colunas_atributos.pkl`.
3. Carregar `silver_elo_atual`.
4. Criar função `montar_features_partida`.
5. Criar função auxiliar para prever lambdas sem simetria.
6. Criar função `prever_jogo`.
7. Em jogos neutros, aplicar simetrização dos lambdas.
8. Usar `probabilidades_resultado` de `src/poisson.py`.
9. Ler `silver_copa2026`.
10. Gerar a tabela `previsoes`.
11. Ler `gold_atributos`.
12. Rodar os 4 experimentos de recência.
13. Gravar `previsoes` e `experimentos_mae` com `DROP + CREATE + COPY`.

## Para explicar enquanto desenvolve

* O modelo Poisson gera λ, que representa gols esperados.
* Com dois λ, um para cada seleção, a grade de Poisson calcula vitória, empate e derrota.
* A previsão usa ELO atual porque estamos prevendo jogos futuros.
* Os pesos de torneio e recência já foram usados no treino; eles não entram na previsão.
* Em campo neutro, simetrizar reduz o viés artificial de quem aparece como mandante na tabela.
* Os experimentos mostram que mudar a recência pode melhorar ou piorar o MAE.
