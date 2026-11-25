from ..models import (
    MinimalAnswer,
    MinimalSearchResults
)
from typing import List, Tuple, Any


def load_model() -> Tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    return (
        AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen3-0.6B",
            dtype=torch.bfloat16,
            device_map="cpu"
        ),
        AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
    )


_SYSTEM_PROMPT = """
You are an assistant answering questions from retrieved documents.

Instructions:
- Answer using only the provided context.
- Do not invent information.
- If the context doesn't contain the answer, say "I don't know".
- If you find the answer, cite the sources using [1], [2], etc.
- Keep answers concise, ideally 2-4 sentences; one sentence if possible.
- Avoid unnecessary explanations and repetition.
"""


_USER_PROMPT = """
Context:

{context}

Question:

{question}

Answer:
"""


def generate_rag_answer(
    results: MinimalSearchResults,
    k: int,
    model: Any,
    tokenizer: Any
) -> MinimalAnswer:

    # get chunk contents
    contents: List[str] = []
    for source in results.retrieved_sources:
        e, s = source.last_character_index, source.first_character_index
        with open(source.file_path, encoding="utf-8") as f:
            content = f.read()
        contents.append(repr(content[s:e]))

    # build context
    context = ""
    for i, c in enumerate(contents):
        context += f"[{i + 1}]\n{c}\n\n"

    # create conversation
    messages = [
        {
            "role": "system",
            "content": _SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": _USER_PROMPT.format(
                context=context, question=results.question
            )
        }
    ]

    # Qwen3 chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )

    # tokenize
    model_inputs = tokenizer([text], return_tensors="pt")

    # generate
    """generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=100,
        do_sample=False,
        num_beams=1
    )"""
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=256,
        do_sample=True,
        temperature=0.7,
        top_p=0.8,
        top_k=k
    )

    # get answer
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    answer = tokenizer.decode(output_ids, skip_special_tokens=True)

    return MinimalAnswer(**results.model_dump(), answer=answer)
