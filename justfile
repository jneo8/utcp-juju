set ignore-comments

# Juju series the manual is generated for, and the juju git checkout its schemas come from
# (override: just juju_repo=~/src/juju vendor-schema).
series := '3.6'
juju_repo := '../juju'
schema_file := 'schemas/' + series + '/schema.json'
schema_source := 'schemas/' + series + '/source.yaml'
manual_file := 'utcp_juju/data/juju.utcp.json'
manual_args := '--schema ' + schema_file + ' --allowlist manualgen/allowlist.yaml --out ' + manual_file

# this is the first recipe in the file, so it will run if just is called without a recipe
[doc('Describe usage and list the available recipes.')]
help:
    @just --list --unsorted

##########
# Linting
##########

[doc('Run `ruff`, failing afterwards if any errors are found.')]
lint path='.':
    #!/usr/bin/env -S bash -xueo pipefail
    FAILURES=0
    uv run --only-group=lint ruff check '{{path}}' || ((FAILURES+=1))
    uv run --only-group=lint ruff check --diff '{{path}}' || : 'Printed diff of changes to fix `ruff check` issues.'
    uv run --only-group=lint ruff format --diff '{{path}}' || ((FAILURES+=1))
    : "$FAILURES command(s) failed."
    exit $FAILURES

[doc('Run `ruff check --fix` and `ruff format`, modifying files in place.')]
format path='.':
    uv run --only-group=lint ruff format '{{path}}'
    uv run --only-group=lint ruff check --fix '{{path}}'

##########
# Testing
##########

[doc('Run unit tests (no Juju controller needed).')]
unit-test *args='':
    uv run --exact --group test pytest tests/unit/ {{args}}

[doc('Run functional tests against the current Juju controller (LXD); deploys into a temporary model.')]
functional-test *args='':
    uv run --exact --group functional pytest tests/functional/ {{args}}

##########
# Manual
##########

[doc('Vendor schema.json of a juju release tag from a local juju checkout, recording its commit.')]
vendor-schema tag='v3.6.29':
    #!/usr/bin/env -S bash -ueo pipefail
    commit=$(git -C '{{juju_repo}}' rev-parse '{{tag}}^{commit}')
    git -C '{{juju_repo}}' show "$commit:apiserver/facades/schema.json" > '{{schema_file}}'
    printf '%s\n' \
        '# Where schema.json comes from. Written by `just vendor-schema`; do not edit.' \
        'repository: https://github.com/juju/juju' \
        'path: apiserver/facades/schema.json' \
        'tag: {{tag}}' \
        "commit: $commit" > '{{schema_source}}'
    echo "vendored {{tag}} ($commit)"

[doc('Generate utcp_juju/data/juju.utcp.json from the schema and the allowlist.')]
gen-manual:
    uv run --group gen python -m manualgen {{manual_args}}

[doc('Fail if the committed manual does not match the schema and the allowlist.')]
check-manual:
    uv run --group gen python -m manualgen {{manual_args}} --check

[doc('List the tools in the manual.')]
list-tools:
    @uv run python -c "from utcp_juju import load_manual; [print(s.name, '-', s.description) for s in load_manual()]"

##########
# Examples
##########

[positional-arguments]
[doc('Ask the example OpenAI Agents SDK agent about the example model; see examples/README.md.')]
run-openai-example prompt='Which units are not active and idle, and why?':
    just -f examples/justfile run-openai-example "$1"

[positional-arguments]
[doc('Ask the example Google ADK agent about the example model; see examples/README.md.')]
run-google-example prompt='Which units are not active and idle, and why?':
    just -f examples/justfile run-google-example "$1"

[positional-arguments]
[doc('Call a tool through the example UTCP client (no LLM); see examples/README.md.')]
run-utcp-example tool='' arguments='{}':
    just -f examples/justfile run-utcp-example "$@"

##########
# Build
##########

[doc('Build the wheel and sdist.')]
build:
    uv build
