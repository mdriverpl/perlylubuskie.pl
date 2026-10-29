FROM alpine:3.22 AS segments
RUN apk add --no-cache curl
ARG MAP_DATA_VERSION=2026-10
RUN mkdir /segments4 && echo "$MAP_DATA_VERSION" > /segments4/snapshot.txt \
    && curl --fail --location --retry 3 --max-time 300 https://brouter.de/brouter/segments4/E10_N50.rd5 -o /segments4/E10_N50.rd5 \
    && curl --fail --location --retry 3 --max-time 300 https://brouter.de/brouter/segments4/E15_N50.rd5 -o /segments4/E15_N50.rd5

FROM ghcr.io/abrensch/brouter@sha256:3c6c8a616f054f9237c900760add5fec6b88fc17108348fb2733a1dd62444165
LABEL org.opencontainers.image.source="https://github.com/mdriverpl/perlylubuskie.pl"
LABEL org.opencontainers.image.description="BRouter with OpenStreetMap segments for western Poland, cycling and walking"
COPY --from=segments --chown=1000:1000 /segments4/ /segments4/
ENV JAVA_OPTS="-Xmx512M -Xms64M -DmaxRunningTime=30 -DmemoryClass=512" MAXTHREADS=2
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=10 CMD bash -c ': > /dev/tcp/127.0.0.1/17777'
