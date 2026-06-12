# Feature 04 — ELO: força dinâmica das seleções

## Contexto

O ELO é uma medida dinâmica de força. Ele começa igual para todas as seleções e vai sendo atualizado jogo a jogo, em ordem cronológica.

Nesta feature, cada seleção começa com ELO 1500. Antes de cada partida, o ELO atual das duas equipes é registrado. Depois do resultado, o ELO é atualizado.

O ponto mais importante é evitar **data leakage**: para cada jogo histórico, o modelo só pode enxergar o ELO que a seleção tinha **antes** daquela partida.

## Objetivo

Calcular o ELO pré-jogo de cada partida de `silver_ponderado` e gravar duas tabelas:

```text
silver_elo_pre_jogo
silver_elo_atual
```

A primeira guarda o ELO de cada seleção antes de cada partida.

A segunda guarda o ELO final mais recente de cada seleção após processar todo o histórico disponível.

## Entrada

Tabela:

```text
silver_ponderado
```

Colunas esperadas:

```text
id
jogo_id
data
time_casa
time_visitante
gols_casa
gols_visitante
torneio
cidade
pais
neutro
eh_amistoso
peso_torneio
peso_recencia
```

Observação:

```text
id = identificador próprio de silver_ponderado
jogo_id = identificador original vindo de silver_jogos
```

## Saídas

### 1. `silver_elo_pre_jogo`

Tabela com uma linha por jogo de `silver_ponderado`.

Colunas:

```text
id
ponderado_id
jogo_id
data
time_casa
time_visitante
elo_casa
elo_visitante
```

Onde:

```text
ponderado_id = silver_ponderado.id
jogo_id = silver_ponderado.jogo_id
```

A coluna `ponderado_id` será usada na próxima feature para fazer join com `silver_ponderado`.

### 2. `silver_elo_atual`

Tabela com o ELO final de cada seleção.

Colunas:

```text
id
selecao
elo
```

## Constantes da feature

```python
ELO_INICIAL = 1500
HFA = 100

K_POR_TORNEIO = {
    1: 20,
    2: 40,
    3: 60,
}
```

Onde:

```text
HFA = home field advantage, vantagem de mando
```

## Requisitos

### 1. Ler dados de `silver_ponderado`

A Feature 04 deve usar somente:

```sql
SELECT *
FROM silver_ponderado
ORDER BY data, id;
```

Não usar:

```text
bronze_jogos
silver_jogos
silver_copa2026
```

A tabela `silver_ponderado` já contém o histórico limpo, sem jogos antigos demais e sem a Copa 2026 futura.

### 2. Processar em ordem cronológica

Os jogos devem ser processados em ordem:

```text
data
id
```

Isso garante resultado determinístico quando há mais de um jogo no mesmo dia.

Exemplo:

```python
df = df.sort_values(["data", "id"]).reset_index(drop=True)
```

A ordem cronológica é obrigatória, porque o ELO de um jogo depende dos jogos anteriores.

### 3. Todo time começa com ELO 1500

Usar um dicionário com valor padrão:

```python
from collections import defaultdict

elos = defaultdict(lambda: 1500.0)
```

Quando uma seleção aparece pela primeira vez, ela recebe ELO 1500.

### 4. Gravar o ELO pré-jogo antes da atualização

Para cada partida:

1. buscar o ELO atual do time da casa;
2. buscar o ELO atual do visitante;
3. gravar esses valores em `silver_elo_pre_jogo`;
4. calcular expectativa;
5. atualizar os ELOs depois do resultado.

O registro pré-jogo deve acontecer antes da atualização.

Errado:

```text
calcular resultado
atualizar ELO
gravar ELO
```

Certo:

```text
buscar ELO atual
gravar ELO pré-jogo
calcular resultado
atualizar ELO
```

### 5. Calcular vantagem de mando

A vantagem de mando deve ser aplicada somente quando o jogo não for neutro.

Regra:

```python
hfa = 0 if neutro else 100
```

Ou seja:

```text
neutro = True  → HFA = 0
neutro = False → HFA = 100
```

### 6. Fórmula de expectativa

Calcular a expectativa do time da casa:

```python
E_casa = 1 / (1 + 10 ** ((elo_visitante - elo_casa - hfa) / 400))
```

E a expectativa do visitante:

```python
E_visitante = 1 - E_casa
```

Atenção ao sinal do HFA.

O HFA deve entrar com sinal negativo dentro do expoente:

```python
elo_visitante - elo_casa - hfa
```

Não usar:

```python
elo_visitante - elo_casa + hfa
```

Com dois times de ELO 1500 e jogo não neutro, o mandante deve ter expectativa aproximada de 0,64.

Teste esperado:

```python
elo_casa = 1500
elo_visitante = 1500
hfa = 100

E_casa = 1 / (1 + 10 ** ((elo_visitante - elo_casa - hfa) / 400))
```

Resultado esperado:

```text
aproximadamente 0.64
```

Se o resultado ficar próximo de 0.36, o HFA está invertido.

### 7. Resultado real da partida

Definir `S_casa` assim:

```text
vitória do time da casa → 1.0
empate → 0.5
derrota do time da casa → 0.0
```

Exemplo:

```python
if gols_casa > gols_visitante:
    S_casa = 1.0
elif gols_casa == gols_visitante:
    S_casa = 0.5
else:
    S_casa = 0.0
```

O resultado do visitante é:

```python
S_visitante = 1 - S_casa
```

### 8. K-factor por importância do torneio

Usar o `peso_torneio` criado na Feature 03 para definir o K-factor.

Regra:

```python
K = K_POR_TORNEIO[peso_torneio]
```

Mapeamento:

```text
peso_torneio = 1 → K = 20
peso_torneio = 2 → K = 40
peso_torneio = 3 → K = 60
```

O `peso_recencia` não deve ser usado no cálculo do ELO.

Motivo:

```text
O ELO já é naturalmente sensível à recência porque é atualizado sequencialmente.
```

### 9. Atualização do ELO

Atualizar os dois times assim:

```python
novo_elo_casa = elo_casa + K * (S_casa - E_casa)
novo_elo_visitante = elo_visitante + K * (S_visitante - E_visitante)
```

Como:

```python
S_visitante = 1 - S_casa
E_visitante = 1 - E_casa
```

A soma das alterações dos dois times deve ser aproximadamente zero.

### 10. Não usar multiplicador de goleada

Não adicionar multiplicador por saldo de gols nesta feature.

Não fazer:

```text
K ajustado por goleada
bônus por saldo
bônus por gols marcados
```

O ELO deve considerar apenas:

```text
resultado
expectativa
mando/neutro
peso_torneio
```

### 11. Não usar jogos sem placar

A tabela `silver_ponderado` não deve conter jogos com placar nulo.

Mesmo assim, validar antes de processar:

```python
assert df["gols_casa"].notna().all()
assert df["gols_visitante"].notna().all()
```

Se houver nulos, a feature deve parar com erro.

### 12. Não usar a Copa 2026 futura

A Feature 04 não deve processar jogos da Copa 2026 futura.

Validar:

```sql
SELECT COUNT(*)
FROM silver_ponderado
WHERE torneio = 'FIFA World Cup'
  AND data >= '2026-06-11';
```

Resultado esperado:

```text
0
```

### 13. Gravação idempotente

As tabelas devem ser recriadas do zero a cada execução:

```sql
DROP TABLE IF EXISTS silver_elo_pre_jogo;
DROP TABLE IF EXISTS silver_elo_atual;
CREATE TABLE ...
COPY ...
```

Rodar a Feature 04 várias vezes deve gerar o mesmo resultado.

## Schema das tabelas

### `silver_elo_pre_jogo`

```sql
CREATE TABLE silver_elo_pre_jogo (
    id bigint generated always as identity primary key,
    ponderado_id bigint,
    jogo_id bigint,
    data date,
    time_casa text,
    time_visitante text,
    elo_casa double precision,
    elo_visitante double precision
);
```

### `silver_elo_atual`

```sql
CREATE TABLE silver_elo_atual (
    id bigint generated always as identity primary key,
    selecao text,
    elo double precision
);
```

## Critérios de aceite

A Feature 04 será considerada correta quando:

1. `silver_elo_pre_jogo` tiver uma linha para cada jogo de `silver_ponderado`.
2. `silver_elo_atual` tiver uma linha para cada seleção encontrada no histórico.
3. Os primeiros jogos começarem com ELO próximo de 1500.
4. O ELO pré-jogo for gravado antes da atualização.
5. O ranking final tiver potências no topo.
6. O HFA aumentar a expectativa do mandante em jogos não neutros.
7. Jogos neutros não aplicarem HFA.
8. O K-factor usar apenas `peso_torneio`.
9. `peso_recencia` não for usado no ELO.
10. Não houver jogos da Copa 2026 futura processados.
11. O join futuro puder ser feito por `silver_elo_pre_jogo.ponderado_id = silver_ponderado.id`.

## Verificação SQL

### Verificar quantidade de linhas

```sql
SELECT
    (SELECT COUNT(*) FROM silver_ponderado) AS silver_ponderado,
    (SELECT COUNT(*) FROM silver_elo_pre_jogo) AS silver_elo_pre_jogo;
```

Os dois valores devem ser iguais.

### Verificar os primeiros jogos

```sql
SELECT data,
       time_casa,
       time_visitante,
       ROUND(elo_casa::numeric, 1) AS elo_casa,
       ROUND(elo_visitante::numeric, 1) AS elo_visitante
FROM silver_elo_pre_jogo
ORDER BY data, ponderado_id
LIMIT 10;
```

Resultado esperado:

```text
os primeiros jogos devem ter ELOs próximos de 1500
```

### Verificar ranking final

```sql
SELECT selecao,
       ROUND(elo::numeric, 0) AS elo
FROM silver_elo_atual
ORDER BY elo DESC
LIMIT 20;
```

Resultado esperado:

```text
seleções fortes no topo, como Espanha, Argentina, França, Brasil, Inglaterra, Portugal, Alemanha, Holanda etc.
```

A ordem exata pode variar, mas o topo deve ser coerente.

### Verificar seleções específicas

```sql
SELECT selecao,
       ROUND(elo::numeric, 0) AS elo
FROM silver_elo_atual
WHERE selecao IN ('Spain', 'Argentina', 'France', 'Brazil', 'England', 'Portugal', 'Germany', 'Scotland')
ORDER BY elo DESC;
```

Essa query ajuda a detectar se uma seleção média ficou artificialmente forte.

### Verificar vínculo com `silver_ponderado`

```sql
SELECT COUNT(*)
FROM silver_elo_pre_jogo e
LEFT JOIN silver_ponderado p
  ON p.id = e.ponderado_id
WHERE p.id IS NULL;
```

Resultado esperado:

```text
0
```

### Verificar duplicidade por jogo ponderado

```sql
SELECT ponderado_id, COUNT(*)
FROM silver_elo_pre_jogo
GROUP BY ponderado_id
HAVING COUNT(*) > 1;
```

Resultado esperado:

```text
nenhuma linha
```

### Verificar cobertura de seleções

```sql
SELECT COUNT(*) AS selecoes
FROM silver_elo_atual;
```

Resultado esperado:

```text
aproximadamente 300+ seleções, dependendo do dataset filtrado
```

### Verificar ausência de Copa 2026 futura

```sql
SELECT COUNT(*)
FROM silver_elo_pre_jogo
WHERE data >= '2026-06-11';
```

Resultado esperado:

```text
0 para jogos da Copa 2026 futura
```

Se existirem jogos de outras competições após essa data por causa de atualização do dataset, conferir a Feature 02. O histórico ideal para simular a Copa deve estar congelado antes do início da competição.

## Plano de implementação

1. Ler `silver_ponderado`.

2. Validar que não existem placares nulos.

3. Validar que `peso_torneio` só possui valores `1`, `2` e `3`.

4. Ordenar por `data, id`.

5. Criar dicionário de ELO com valor padrão `1500.0`.

6. Iterar jogo a jogo.

7. Para cada jogo:

   * buscar ELO atual da casa;
   * buscar ELO atual do visitante;
   * gravar linha pré-jogo com `ponderado_id` e `jogo_id`;
   * definir HFA conforme `neutro`;
   * calcular expectativa;
   * calcular resultado real;
   * definir K pelo `peso_torneio`;
   * atualizar ELO das duas seleções.

8. Ao fim, transformar o dicionário de ELO em `silver_elo_atual`.

9. Validar quantidades.

10. Gravar `silver_elo_pre_jogo` e `silver_elo_atual` com `DROP + CREATE + COPY`.

## Para explicar enquanto desenvolve

* ELO não é machine learning; é uma engenharia de força atualizada jogo a jogo.
* Todas as seleções começam iguais em 1500.
* Ganhar de uma seleção forte aumenta mais o ELO do que ganhar de uma seleção fraca.
* Perder quando se era favorito derruba mais o ELO.
* A ordem cronológica é obrigatória.
* O ELO pré-jogo evita data leakage.
* `peso_torneio` muda o tamanho da atualização.
* `peso_recencia` não entra no ELO porque o próprio ELO já dá mais importância ao presente por ser sequencial.
