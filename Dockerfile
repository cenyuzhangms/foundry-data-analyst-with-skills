FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /app

# System tools needed at runtime:
#   bash + coreutils for the run_shell tool
#   curl/git for fetching datasets
#   build-essential + python3-dev so pip install for native wheels works on the fly
RUN apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates curl git jq procps file unzip \
        build-essential python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Persistent workspace the agent uses for downloaded datasets and chart artifacts.
RUN mkdir -p /work
ENV WORKDIR=/work

COPY . .

# Bake skill executables into /opt/skills/<name>/bin/ and add each to PATH.
# main.py also discovers skill metadata (SKILL.md) from the Foundry project at
# startup and appends it to the system prompt (Pattern A).
RUN set -eux; \
    if [ -d /app/skills ]; then \
        mkdir -p /opt/skills; \
        for d in /app/skills/*/; do \
            name="$(basename "$d")"; \
            mkdir -p "/opt/skills/$name"; \
            cp -r "$d"/. "/opt/skills/$name/"; \
            if [ -d "/opt/skills/$name/bin" ]; then \
                chmod -R +x "/opt/skills/$name/bin"; \
            fi; \
        done; \
    fi
# Make skill bin/ dirs visible to bash -lc (used by the run_shell tool).
RUN printf 'export PATH="/opt/skills/eda-quick-look/bin:/opt/skills/ab-test/bin:/opt/skills/time-series-decompose/bin:$PATH"\n' > /etc/profile.d/skills-path.sh
ENV PATH="/opt/skills/eda-quick-look/bin:/opt/skills/ab-test/bin:/opt/skills/time-series-decompose/bin:${PATH}"

EXPOSE 8088

CMD ["python", "main.py"]
