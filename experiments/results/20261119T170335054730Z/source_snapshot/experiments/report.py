"""Resumo Markdown gerado a partir dos CSVs/JSONs da execução corrente."""

from pathlib import Path


def _table(rows, fields):
    def cell(value):
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)
    return "\n".join(["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)] +
                     ["| " + " | ".join(cell(row.get(key)) for key in fields) + " |" for row in rows])


def write_report(output, metadata, tables, reproducibility):
    counts = metadata["counts"]
    stable = [r for r in reproducibility if r["kind"] == "policy" and r["comparable"]]
    text = f"""# Resultados medidos — execução {metadata['run_id']}

Gerado automaticamente. Configuração e fontes identificadas em `metadata.json`.
São medidas de software e simulação RTL; nenhuma latência física de FPGA foi medida.

Dataset: {counts['dataset_cases']} casos, {counts['evaluation_cases']} na avaliação final.
Observações: {counts['numeric_rows']} numéricas, {counts['timing_rows']} temporais,
{counts['policy_rows']} de políticas e {counts['fault_rows']} de falhas controladas.
Caracterização, desenvolvimento e avaliação possuem identificadores distintos (`splits.json`).
Os perfis usam somente o primeiro conjunto; `frozen_policy.json` foi salvo antes da avaliação.

## A — Validação numérica

`valid_no_overflow` significa equivalência inteira sem overflow, não qualidade geométrica.
Os erros de casos com overflow ficam visíveis, mas suas latências são excluídas da
população válida das tabelas de desempenho. Matriz essencial nula torna indefinida
a comparação geométrica normalizada. Consulte cada caso em `numeric.csv`.

{_table(tables['numeric'], ['category', 'samples', 'bit_exact', 'valid_no_overflow', 'overflow', 'max_absolute_error_all', 'max_absolute_error_valid'])}

## B — Tempos de parede

Segundos por tentativa incluindo validação. `paired_valid` compara exatamente os
mesmos pares/repetições válidos nos dois caminhos. Percentis usam interpolação
linear, sem inferência sobre caudas raras. Compilação fria está em `raw.jsonl`;
compilação, preparo, serialização, processo GHDL e parsing estão em `timing.csv`.
Inicialização/JIT e simulação não são separáveis nesta instrumentação e ficam
marcados como não medidos, sem subtração de estimativas.

{_table(tables['timing'], ['backend', 'population', 'samples', 'seconds_median', 'seconds_p90', 'seconds_p95'])}

## C — Políticas e restrições

Tempos abaixo incluem requisições sem opção viável e tentativas rejeitadas;
consulte conjuntamente a taxa de validade. O custo da decisão e o orçamento
incluem verificações de versões/assinaturas. As preferências/requisitos foram
declarados em `config.json` antes de observar os resultados finais.

{_table(tables['policies'], ['scenario', 'policy', 'requests', 'valid', 'no_feasible', 'fallbacks', 'error_violations', 'time_overruns', 'seconds_median', 'decision_seconds_median'])}

Comparação pareada posterior à decisão, sem alimentar o seletor:

{_table(tables['comparisons'], ['scenario', 'requests', 'initial_feasible_ex_post', 'missed_observed_feasible', 'overhead_seconds_median', 'oracle_excess_seconds_median'])}

`oracle` é apenas a melhor alternativa fixa observada no mesmo caso/cenário/
repetição. Não é garantia de melhor latência nem conhecimento disponível ao seletor.
Overhead é a diferença pareada de tempos totais, sujeita à carga e à ordem de execução.

## D — Robustez

{_table(tables['faults'], ['fault', 'fallback_policy', 'status', 'selected_backend', 'backend', 'fallback_count', 'initial_success', 'detection_ok'])}

Injeções são segregadas das falhas naturais. Indisponibilidade antes da seleção
deve podar o candidato, sem inventar um fallback. A falha numérica usa F=0,1I,
K=I e limite zero depois de perfis exatos de ±I, demonstrando que um envelope
empírico não prova erro uniforme. U/X é produzido em uma cópia descartável do RTL.

## E — Reprodutibilidade

Regeneração independente do dataset idêntica: {metadata['dataset_regeneration_identical']}.
Resultados numéricos estáveis entre repetições: {metadata['checks']['numeric_repeat_stable']}.
Decisões/status/saídas estáveis: {sum(r['stable'] for r in stable)}/{len(stable)} comparações.
As eventuais diferenças estão em `reproducibility.csv`; tempos de parede não
são exigidos idênticos. Seeds e perfis brutos permanecem disponíveis.

## Interpretação e limites

Este kernel 3×3 tem custo NumPy pequeno frente ao subprocesso GHDL e à seleção.
A escolha por menor tempo pode se reduzir sistematicamente ao software.
Prefira descrever validade, generalização dos perfis, verificação e overhead;
não atribua aceleração física à simulação ou vantagem científica a matrizes de stress.
As imagens pertencem a uma única cena, com K estimada e sem ground truth.
O estudo não demonstra originalidade nem prontidão editorial.

Figuras medidas/derivadas: `figures/numeric_errors.png`, `figures/latency_ecdf.png`
e `figures/policy_success.png`, também em PDF. Tabelas são reproduzidas dos CSVs.
"""
    (Path(output) / "RESULTS.md").write_text(text, encoding="utf-8")
