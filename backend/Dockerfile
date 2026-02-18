# ベースイメージ
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

USER root

# 環境変数の設定
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/usr/local/bin:$PATH"
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
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python3 -c "import pyopenjtalk; pyopenjtalk._lazy_init()"

# Hugging Faceのモデルダウンロード
ARG HF_USERNAME
ARG HF_TOKEN
ENV HF_USERNAME=${HF_USERNAME}
ENV HF_TOKEN=${HF_TOKEN}

# 認証を通してモデルをダウンロード
RUN git clone https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/ku-nlp/deberta-v2-large-japanese-char-wwm \
    /usr/local/lib/python3.10/dist-packages/style_bert_vits2/bert/deberta-v2-large-japanese-char-wwm || echo "Model clone failed or already exists"

# 実行ユーザーの作成
RUN useradd -m appuser
USER appuser

# 起動コマンド
# /workspace/app/main.py が存在するため、これで起動します
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8077"]