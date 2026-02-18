# ベースイメージ
FROM nvidia/cuda:12.8.1-runtime-ubuntu22.04

USER root
ENV TZ=Asia/Tokyo

# 必要なパッケージをインストール
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    curl \
    build-essential \
    mecab \
    libmecab-dev \
    mecab-ipadic-utf8 \
    xz-utils \
    file \
    sudo \
    ffmpeg \
    git-lfs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ワークディレクトリを設定
WORKDIR /workspace

# 必要なPythonライブラリをインストール
COPY requirements.dev.txt /workspace/
RUN pip install -r requirements.dev.txt

ARG HF_USERNAME
ARG HF_TOKEN
ENV HF_USERNAME=${HF_USERNAME}
ENV HF_TOKEN=${HF_TOKEN}

RUN git clone https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/ku-nlp/deberta-v2-large-japanese-char-wwm \
    /usr/local/lib/python3.10/dist-packages/style_bert_vits2/bert/deberta-v2-large-japanese-char-wwm