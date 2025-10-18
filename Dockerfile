# Dockerfile for IRS Fact Graph (美國稅務知識圖譜)
# 用於運行 Fact Graph Demo 和編譯專案

FROM eclipse-temurin:21-jdk

# 安裝必要工具
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 sbt (Scala Build Tool)
RUN echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | tee /etc/apt/sources.list.d/sbt.list && \
    echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | tee /etc/apt/sources.list.d/sbt_old.list && \
    curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add && \
    apt-get update && \
    apt-get install -y sbt && \
    rm -rf /var/lib/apt/lists/*

# 安裝 Node.js (用於運行 JS 測試和 demo)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /fact-graph

# 只複製 build.sbt 和 project 目錄來下載依賴
COPY build.sbt ./
COPY project ./project

# 預先下載 sbt 依賴(加速後續建置)
RUN sbt update || true

# 暴露 HTTP 伺服器端口 (用於 demo)
EXPOSE 8897

# 預設命令:啟動 demo 伺服器
CMD cd demo && python3 -m http.server 8897
