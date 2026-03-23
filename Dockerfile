FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    xvfb \
    libglib2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libfontconfig1 \
    libfreetype6 \
    libdbus-1-3 \
    libnss3 \
    libasound2 \
    xdg-utils \
    libxcb1 \
    libxcb-util1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libegl1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# ODA notes some Ubuntu systems need libxcb-util.so.0
RUN if [ ! -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 ] && [ -e /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 ]; then \
      ln -s /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0; \
    fi

# Copy the DEB you downloaded manually into the image
COPY ODA_PACKAGE.deb /tmp/ODA_PACKAGE.deb

RUN apt-get update && apt-get install -y /tmp/ODA_PACKAGE.deb \
    && rm /tmp/ODA_PACKAGE.deb

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=10000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}