FROM ubuntu:latest

# =============================
# (Opcional) Configuración de certificados
# =============================
# WORKDIR /opt/certs
# RUN apt-get update \
#     && apt-get -y upgrade \
#     && apt-get clean
# USER root
# RUN apt-get update && apt-get -y install --no-install-recommends \
#     ca-certificates \
#     wget \
#     less \
#     tar 
# COPY ../configs/certs/* /opt/certs
# RUN cp -a /opt/certs/* /usr/local/share/ca-certificates/ && update-ca-certificates

# =============================
# Dependencias del sistema
# =============================
RUN apt-get update && apt-get install -y \
    curl \
    bash-completion \
    openjdk-17-jdk \
    fontconfig \
    fonts-dejavu-core \
    software-properties-common \
    python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# =============================
# Graphviz
# =============================
RUN apt-get update && apt-get install -y \
    graphviz \
 && rm -rf /var/lib/apt/lists/*


# =============================
# ANTLR
# =============================
COPY antlr-4.13.1-complete.jar /usr/local/lib/antlr-4.13.1-complete.jar
COPY ./commands/antlr /usr/local/bin/antlr
COPY ./commands/antlr /usr/bin/antlr
RUN chmod +x /usr/local/bin/antlr /usr/bin/antlr
COPY ./commands/grun /usr/local/bin/grun
COPY ./commands/grun /usr/bin/grun
RUN chmod +x /usr/local/bin/grun /usr/bin/grun

# =============================
# Python virtual env
# =============================
COPY python-venv.sh .
RUN chmod +x ./python-venv.sh && ./python-venv.sh

# =============================
# Requerimientos Python
# =============================
COPY requirements.txt .
RUN pip install -r requirements.txt --break-system-packages

# =============================
# Copiar TODO el proyecto al contenedor
# =============================
COPY . .

# =============================
# Crear usuario no root
# =============================
ARG USER=appuser
ARG UID=1001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "$(pwd)" \
    --no-create-home \
    --uid "${UID}" \
    "${USER}"
USER ${UID}

# =============================
# Carpeta de trabajo
# =============================
WORKDIR /program

# =============================
# Ejecutar Streamlit (IDE)
# =============================
CMD ["streamlit", "run", "semantic/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
