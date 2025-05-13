"""
LLM Explainer – Qwen QwQ-32B-AWQ (4-bit, fp16)
───────────────────────────────────────────────
• Até 32 k tokens de contexto; até 10 k tokens de resposta.
• Preserva o bloco <think> completo – sem cortes.
• Parser lê o primeiro “Correto/Correta/Incorreto/Incorreta” encontrado
  e devolve o restante como justificativa.

Dependências:
  pip install -U autoawq transformers accelerate safetensors \
      "awq @ https://huggingface.github.io/autawq-wheels/cu121"
"""
from __future__ import annotations

import gc
import logging
import re
from typing import List, Optional, Tuple

import torch
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

# ─────────────────────────── logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - EXPLAINER - %(levelname)s - %(message)s",
)

# ───────────────────────── constants
MODEL_ID   = "Qwen/QwQ-32B-AWQ"
DTYPE      = torch.float16       # evita mismatch fp16 × bf16
MAX_CTX_TK = 32_000

_model: Optional[AutoAWQForCausalLM] = None
_tok:   Optional[AutoTokenizer]      = None


# ─────────────────────── model loader
def _load_model() -> Tuple[AutoAWQForCausalLM, AutoTokenizer]:
    global _model, _tok
    if _model is not None:
        return _model, _tok

    gc.collect()
    torch.cuda.empty_cache()
    logging.info(f"🔄 Carregando {MODEL_ID}…")

    _model = AutoAWQForCausalLM.from_quantized(
        MODEL_ID,
        device_map="auto",
        torch_dtype=DTYPE,
        fuse_layers=True,
    ).eval()

    _tok = AutoTokenizer.from_pretrained(MODEL_ID)
    if _tok.pad_token is None:
        _tok.pad_token = _tok.eos_token
        _tok.padding_side = "right"

    logging.info("✅ Modelo carregado.")
    return _model, _tok


# ─────────────────────── prompt builder
def _build_prompt(statement: str, paragraphs: List[str]) -> str:
    ctx = "\n\n".join(
        f"Parágrafo {i+1}:\n{p}" for i, p in enumerate(paragraphs) if p.strip()
    ) or "Nenhum parágrafo de contexto foi fornecido."

    system_msg = (
        "Você é um avaliador jurídico. Determine se a AFIRMAÇÃO está correta "
        "à luz dos PARÁGRAFOS.\n\n"
        "CRITÉRIOS:\n"
        "• 'Incorreto' → contradição factual OU falta/divergência de fato essencial.\n"
        "• 'Correto'   → todos os fatos essenciais presentes ou paráfrase fiel.\n\n"
        "FORMATO OBRIGATÓRIO:\n"
        "Correto.\nJustificativa: …\n\nou\n\n"
        "Incorreto.\nJustificativa: …\n\n"
        "Comece **exatamente** com 'Correto.' ou 'Incorreto.' (sem 'Resultado:', "
        "sem Markdown). Responda em português."
    )

    user_msg = f"AFIRMAÇÃO: {statement}\n\nPARÁGRAFOS:\n{ctx}"

    # Formato chat Qwen-2
    return (
        "<|im_start|>system\n" + system_msg + "\n<|im_end|>\n"
        "<|im_start|>user\n"   + user_msg   + "\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


# ───────────────────────── main API
def explain(
    query: str,
    list_of_texts: List[str],
    *,
    max_new_tokens: int = 10_000,
    temperature: float = 0.0,
) -> Tuple[str, str]:
    """
    Retorna (veredito, justificativa).
    • Nenhum critério de parada explícito ‒ só ‘max_new_tokens’.
    • Inteiro <think> preservado.
    """
    if not query or not list_of_texts:
        return "ERRO_DE_PARSING", "Dados de entrada ausentes para o LLM."

    try:
        model, tok = _load_model()
        device = next(model.parameters()).device

        prompt = _build_prompt(query, list_of_texts)
        inp = tok(prompt, return_tensors="pt", truncation=True, padding=False)
        if inp.input_ids.shape[1] >= MAX_CTX_TK:
            return "ERRO_DE_PARSING", "Prompt excede o limite de contexto."

        inp = {k: v.to(device) for k, v in inp.items()}

        gen_ids = model.generate(
            **inp,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=0.9,
            do_sample=temperature > 0,
            pad_token_id=tok.pad_token_id,  # ← único token especial mantido
            # **eos_token_id REMOVIDO**  (nenhum critério de parada)
        )

        reply = tok.decode(
            gen_ids[0, inp["input_ids"].shape[1]:],
            skip_special_tokens=True,
        ).strip()

        # remove cabeçalho “Parágrafo X:” caso escape
        reply = re.sub(r"^Parágrafo[s]?\s*\d+(?:-?\d+)?[:.]?\s*", "", reply, flags=re.I).strip()

        # ─────────── parser
        m = re.search(r"(?:Resultado\s*:\s*)?\s*(Corret[oa]|Incorret[oa])\b\.?", reply, re.I)
        if not m:
            return "ERRO_DE_PARSING", f"LLM não seguiu o formato esperado. Resposta bruta: {reply}"

        verdict = "Correto" if m.group(1).lower().startswith("corret") else "Incorreto"
        rationale_raw = reply[m.end():].lstrip()

        j = re.search(r"Justificativa\s*:\s*(.*)", rationale_raw, re.I | re.S)
        rationale = j.group(1).strip() if j else rationale_raw or "Justificativa ausente."

        return verdict, rationale

    except Exception as exc:  # noqa: BLE001
        logging.exception("Erro em explain()")
        return "ERRO_DE_PARSING", f"Falha na geração da explicação pelo LLM: {exc}"


# ───────────────────────── quick test
if __name__ == "__main__":
    v, r = explain(
        "Segundo o TCU, o banco não é dependente da União.",
        ["SUMÁRIO: REPRESENTAÇÃO … NÃO ENQUADRAMENTO DO BNDES …"],
    )
    print("VEREDITO:", v)
    print("JUSTIFICATIVA:\n", r)
