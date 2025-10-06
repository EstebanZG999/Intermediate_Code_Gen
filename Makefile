DOCKER_IMAGE := csp-image
PROJECT_ROOT := $(PWD)
PROGRAM_DIR  := $(PWD)/program

# Montamos todo el repo en /workspace
DOCKER_RUN   := docker run --rm -ti -u $(shell id -u):$(shell id -g) \
  -v "$(PROJECT_ROOT)":/workspace -w /workspace $(DOCKER_IMAGE)

.PHONY: docker-build gen run test clean ide

docker-build:
	docker build --rm . -t $(DOCKER_IMAGE)

# Genera lexer/parser/visitor con ANTLR dentro del contenedor
gen: docker-build
	$(DOCKER_RUN) bash -lc 'cd program && antlr -Dlanguage=Python3 -visitor Compiscript.g4 && ls -1 Compiscript*.py'

# Ejecuta el driver dentro del contenedor
run: docker-build gen
	$(DOCKER_RUN) bash -lc '\
		export PYTHONPATH=/workspace:/workspace/program && \
		python3 program/Driver.py program/program.cps \
	'

# Corre pytest dentro del contenedor
test: docker-build
	$(DOCKER_RUN) bash -lc '\
		python3 -m pip install -q --break-system-packages pytest && \
		export PYTHONPATH=/workspace:/workspace/program && \
		pytest -q \
	'

# Limpia artefactos generados por ANTLR en tu árbol local
clean:
	@find program -maxdepth 1 -type f \( \
		-name "Compiscript*.py" -o -name "Compiscript*.tokens" -o -name "Compiscript*.interp" \
	\) -print -delete


rebuild:
	docker buildx prune -af || true
	docker system prune -af --volumes || true
	docker rmi $(DOCKER_IMAGE) || true
	docker build --no-cache --pull -t $(DOCKER_IMAGE) .
# ---------- Tests específicos ----------

.PHONY: test-scopes test-scopes-stack cov-scopes shell lint-b type-b

# Ejecuta SOLO los tests de scopes
test-scopes: docker-build
	$(DOCKER_RUN) bash -lc '\
		python3 -m pip install -q --break-system-packages pytest && \
		export PYTHONPATH=/workspace:/workspace/program && \
		pytest -q tests/semantic/test_scopes.py \
	'

# Ejecuta SOLO los tests de stack (ScopeStack)
test-scopes-stack: docker-build
	$(DOCKER_RUN) bash -lc '\
		python3 -m pip install -q --break-system-packages pytest && \
		export PYTHONPATH=/workspace:/workspace/program && \
		pytest -q tests/semantic/test_scopes_stack.py \
	'

# Reporte de cobertura centrado en semantic/scopes.py
cov-scopes: docker-build
	$(DOCKER_RUN) bash -lc '\
		python3 -m pip install -q --break-system-packages pytest pytest-cov && \
		export PYTHONPATH=/workspace:/workspace/program && \
		pytest -q --cov=semantic/scopes.py --cov-report=term-missing tests/semantic/test_scopes.py \
	'


# Abre una shell interactiva en el contenedor
shell: docker-build
	$(DOCKER_RUN) bash

# Lint rápido del módulo de scopes
lint-b: docker-build
	$(DOCKER_RUN) bash -lc '\
		python3 -m pip install -q --break-system-packages ruff && \
		ruff check program/semantic/scopes.py \
	'

ide: docker-build gen
	docker run --rm -it -p 8501:8501 \
	  -v "$(PROJECT_ROOT)":/workspace -w /workspace/program/ide $(DOCKER_IMAGE) \
	  bash -lc '\
	    export PYTHONPATH=/workspace:/workspace/program && \
	    streamlit run app.py --server.port=8501 --server.address=0.0.0.0 \
	  '
driver:
	python -m program.Driver program/program_ok.cps

