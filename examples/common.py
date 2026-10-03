"""What the example agents share: their instructions and how they pick an LLM."""

import os

# LiteLLM model name per API key, in order of preference when several keys are exported.
DEFAULT_MODELS = {
    'GEMINI_API_KEY': 'gemini/gemini-3.8-flash',
    'OPENAI_API_KEY': 'openai/gpt-5-mini',
}

INSTRUCTIONS = """\
You answer questions about the Juju model `{model}` for an operator.
Use the Juju tools, always with model `{model}`; when the question is about a few
applications, units or machines, use the tools' filter arguments to narrow the result.
Base every statement on tool results, name the units or machines you mean, and say so
when the result does not answer the question. You cannot change anything in Juju.
"""


def llm_model() -> str:
    """LLM_MODEL if set, else the default model for the first API key exported."""
    if os.environ.get('LLM_MODEL'):
        return os.environ['LLM_MODEL']
    for key, model in DEFAULT_MODELS.items():
        if os.environ.get(key):
            return model
    raise SystemExit(f'export one of {", ".join(DEFAULT_MODELS)}, or set LLM_MODEL')
